from __future__ import print_function
import time
import logging
from io import StringIO
import uuid
import os
import socket
from contextlib import closing
import tempfile

# pylint: disable=wrong-import-position,no-name-in-module
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkVnc', '2.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GtkVnc
from gi.repository import GLib
# pylint: enable=wrong-import-position,no-name-in-module

from towerlib.utils.shell import ssh, Command, ErrorReturnCode_1, ErrorReturnCode
from towerlib.sshconf import get_host_color_name
from towerlib.utils.exceptions import ServerTimeoutException, CommandNotFound
from towerlib.utils.gtkwindows import ColorableWindow

logger = logging.getLogger('tower')

X11VNC_TIMEOUT = 5
TMP_DIR = tempfile.gettempdir()

def wait_for_output(_out, expected_output):
    start_time = time.time()
    elapsed_time = 0
    process_output = _out.getvalue()
    while expected_output not in process_output:
        process_output = _out.getvalue()
        elapsed_time = time.time() - start_time
        if elapsed_time > X11VNC_TIMEOUT:
            logger.info(process_output)
            raise ServerTimeoutException(f"x11vnc not ready after {X11VNC_TIMEOUT}s")
    logger.debug(process_output)


def start_vnc_server(host, port, run_cmd, resolution):
    x11vnc_output = StringIO()
    vnc_params = ' '.join([
        '-create',
        '-nopw', '-listen 127.0.0.1',
        '-cursor arrow', 
        '-ncache 20', '-ncache_cr',
        f'-env FD_GEOM={resolution[0]}x{resolution[1]}x16',
        f"-env FD_PROG='{run_cmd}'",
        "-env PULSE_SERVER=tcp:localhost:4713",
        f"-rfbport {port}",
    ])
    vnc_cmd = f"x11vnc {vnc_params}"
    ssh(
        host,
        "-L", f"{port}:localhost:{port}", 
        "-R", "4713:localhost:4713", # tunnel for pulseaudio
        vnc_cmd,
        _out=x11vnc_output, _err_to_out=True, _bg=True, _bg_exc=False
    )
    wait_for_output(x11vnc_output, "PORT=")
    return x11vnc_output


def get_thinclient_resolution():
    resolution = Command('sh')('-c', "xrandr | grep '*' | awk '{print $1}'").strip()
    return [int(v) for v in resolution.split('x')]


def on_vnc_disconnected(_):
    logger.info("Disconnected from server")
    Gtk.main_quit()

def on_vnc_close(vnc):
    logger.debug("Window closed by user")
    vnc.send_keys([Gdk.KEY_Control_L, Gdk.KEY_q])
    return True

def initialize_vnc_display(parent_window, port):
    vnc = GtkVnc.Display()
    vnc.realize()
    vnc.set_pointer_grab(True)
    vnc.set_keyboard_grab(True)
    # Example to change grab key combination to Ctrl+Alt+g
    grab_keys = GtkVnc.GrabSequence.new([ Gdk.KEY_Control_L, Gdk.KEY_Alt_L, Gdk.KEY_g ])
    vnc.set_grab_keys(grab_keys)
    vnc.open_host("localhost", port)
    vnc.connect("vnc-pointer-grab", lambda _: logger.debug("Grabbed pointer"))
    vnc.connect("vnc-pointer-ungrab", lambda _: logger.debug("Ungrabbed pointer"))
    vnc.connect("vnc-connected", lambda _: logger.info("Connected to server"))
    vnc.connect("vnc-initialized", parent_window._vnc_initialized)
    vnc.connect("vnc-disconnected", on_vnc_disconnected)
    parent_window.connect('delete-event', lambda _, __: on_vnc_close(vnc))
    return vnc


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class VNCViewer(ColorableWindow):
    # pylint: disable=too-many-arguments
    def __init__(self, host, port, run_cmd, session_id, uncolored=False):
        Gtk.Window.__init__(self)
        self.host = host
        self.port = port
        self.run_cmd = run_cmd
        self.session_id = session_id
        self.uncolored = uncolored
        self.init_size_timer = None
        self.window_id = None
        self.window_pid = None
        self.display = None
        self.set_resizable(False)
        self.thinclient_resolution = get_thinclient_resolution()
        # close event
        self.connect("destroy", Gtk.main_quit)
        # headerbar
        if not self.uncolored:
            host_color_name = get_host_color_name(self.host)
            self.set_headerbar_color(host_color_name)
        self.set_title(f"[{self.host}] {self._window_name()}")
        self.layout = Gtk.Layout()
        self.add(self.layout)
        self.x11vnc_output = start_vnc_server(host, port, run_cmd, self.thinclient_resolution)
        # initialize vnc display
        self.vnc = initialize_vnc_display(self, port)
        self.layout.add(self.vnc)

    def _window_name(self):
        name = self.run_cmd.split(' ')[0]
        return name.split('/')[-1]

    def _vnc_initialized(self, _):
        logger.info("Connection initialized")
        logger.debug(self.x11vnc_output.getvalue())
        self._update_session_display()
        self._init_size()
        self.show_all()

    def _init_size(self):
        self._refresh_window_id()
        if self.window_id is None:
            self.init_size_timer = GLib.timeout_add(interval=1000, function=self._init_size)
            return
        self.init_size_timer = None
        width, height = self._get_app_size()
        ssh(self.host, f'DISPLAY={self.display} xdotool windowmove {self.window_id} 0 0')
        self.resize(width, height)
        self.set_resizable(True)
        self._update_window_pid()
        # "resize" event
        self.connect_resize_event(self._on_resize)

    def _search_window_id(self):
        try:
            cmd = f'DISPLAY={self.display} xdotool search --onlyvisible --name "{self._window_name()}"'
            return ssh(self.host, cmd).strip()
        except ErrorReturnCode:
            return None

    def _refresh_window_id(self):
        new_window_id = self._search_window_id()
        if new_window_id != self.window_id:
            self.window_id = new_window_id
            return True
        return False

    def _set_app_size(self, width, height):
        try:
            ssh(self.host, f'DISPLAY={self.display} xdotool windowsize --sync {self.window_id} {width} {height}')
        except ErrorReturnCode:
            if self._refresh_window_id():
                self._set_app_size(width, height)

    def _get_app_size(self):
        try:
            width, height = ssh(self.host, f'DISPLAY={self.display} xdotool getwindowgeometry {self.window_id}').split(' ')[-1].split('x')
            return int(width), int(height)
        except ErrorReturnCode:
            if self._refresh_window_id():
                return self._get_app_size()
            return 200, 200

    def _update_window_pid(self):
        try:
            self.window_pid = ssh(self.host, f'DISPLAY={self.display} xdotool getwindowpid {self.window_id}').strip()
            with open(f'/{TMP_DIR}/{self.session_id}.pid', 'w', encoding="UTF-8") as file_pointer:
                file_pointer.write(self.window_pid)
        except ErrorReturnCode:
            if self._refresh_window_id():
                self._update_window_pid()

    def _update_session_display(self):
        self.display = self.x11vnc_output.getvalue().split(" Using X display")[1].split("\n")[0].strip()
        logger.debug("DISPLAY %s", self.display)
        with open(f'/{TMP_DIR}/{self.session_id}.display', 'w', encoding="UTF-8") as file_pointer:
            file_pointer.write(self.display)

    def _on_resize(self, width, height):
        if self.uncolored or width == self.thinclient_resolution[0]:
            self._set_app_size(width, height)
        else:
            self._set_app_size(width - 50, height - 90)


def cleanup(host, port, session_id):
    # killing application
    if os.path.exists(f'/{TMP_DIR}/{session_id}.pid'):
        with open(f'/{TMP_DIR}/{session_id}.pid', 'r', encoding="UTF-8") as file_pointer:
            window_pid = file_pointer.read().strip()
            ssh(
                host,
                f'kill -9 {window_pid} || true',
                _bg=True, _bg_exc=False
            )
            os.remove(f'/{TMP_DIR}/{session_id}.pid')
    # killing xvfb and x11vnc
    if os.path.exists(f'/{TMP_DIR}/{session_id}.display'):
        with open(f'/{TMP_DIR}/{session_id}.display', 'r', encoding="UTF-8") as file_pointer:
            display = file_pointer.read().strip()
            kill_cmd = f"ps -ef | grep -e 'Xvfb {display}' -e '-rfbport {port}' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
            ssh(
                host,
                kill_cmd,
                _bg=True, _bg_exc=False
            )
            os.remove(f'/{TMP_DIR}/{session_id}.display')
    # killing ssh tunnel
    ssh_killcmd = f"ps -ef | grep '{port}:localhost:{port} x11vnc' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
    Command('sh')('-c',
        ssh_killcmd,
        _bg=True, _bg_exc=False
    )


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('', 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


def find_cmd_path(host, run_cmd):
    try:
        return ssh(host, f'which {run_cmd}').strip()
    except ErrorReturnCode_1 as exc:
        raise CommandNotFound(f'Command {run_cmd} not found on host {host}') from exc


def run(host, run_cmd, uncolored=False):
    port = str(find_free_port())
    session_id = uuid.uuid1()
    cmd = find_cmd_path(host, run_cmd)
    try:
        VNCViewer(host, port, cmd, session_id, uncolored)
        Gtk.main()
    finally:
        cleanup(host, port, session_id)
