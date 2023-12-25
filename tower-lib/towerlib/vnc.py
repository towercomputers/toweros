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

def start_vnc_server(host, port, run_cmd):
    resolution = get_thinclient_resolution()
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

def wait_for_window_id(host, display, run_cmd, session_id, callback):
    logger.debug("Waiting for window id...")
    window_id = xdo_get_window_id(host, display, run_cmd)
    if window_id is None:
        GLib.timeout_add(interval=100, function=lambda: wait_for_window_id(host, display, run_cmd, session_id, callback))
    else:
        on_vnc_window_ready(host, display, run_cmd, session_id, callback)

def on_vnc_window_ready(host, display, run_cmd, session_id, callback):
     # save session tmp files
    save_session_tmp_file(host, session_id, display, run_cmd)
    # move to top left corner
    xdo_move_window_to_top_left(host, display, run_cmd)
    # if possible  get the original application size
    width, height = xdo_get_window_size(host, display, run_cmd)
    # call vnc viewer window callback
    callback(display, width, height)

def on_vnc_initialized(host, run_cmd, session_id, x11vnc_output, callback):
    logger.info("Connection initialized")
    display = x11vnc_output.getvalue().split(" Using X display")[1].split("\n")[0].strip()
    logger.debug("DISPLAY %s", display)
    # wait for window application to be ready
    wait_for_window_id(host, display, run_cmd, session_id, callback)

def initialize_vnc_display(host, port, run_cmd, session_id, parent_window):
    x11vnc_output = start_vnc_server(host, port, run_cmd)
    vnc = GtkVnc.Display()
    vnc.realize()
    vnc.set_pointer_grab(True)
    vnc.set_keyboard_grab(True)
    # Example to change grab key combination to Ctrl+Alt+g
    grab_keys = GtkVnc.GrabSequence.new([ Gdk.KEY_Control_L, Gdk.KEY_Alt_L, Gdk.KEY_g ])
    vnc.set_grab_keys(grab_keys)
    # connect
    vnc.open_host("localhost", port)
    # initialize events listeners
    vnc.connect("vnc-pointer-grab", lambda _: logger.debug("Grabbed pointer"))
    vnc.connect("vnc-pointer-ungrab", lambda _: logger.debug("Ungrabbed pointer"))
    vnc.connect("vnc-connected", lambda _: logger.info("Connected to server"))
    vnc.connect("vnc-initialized", lambda _: on_vnc_initialized(host, run_cmd, session_id, x11vnc_output, parent_window.vnc_display_initialized))
    vnc.connect("vnc-disconnected", on_vnc_disconnected)
    parent_window.connect('delete-event', lambda _, __: on_vnc_close(vnc))
    # add vnc to window
    vnc_layout = Gtk.Layout()
    parent_window.add(vnc_layout)
    vnc_layout.add(vnc)


def save_session_tmp_file(host, session_id, display, run_cmd):
    # save display
    with open(f'/{TMP_DIR}/{session_id}.display', 'w', encoding="UTF-8") as file_pointer:
        file_pointer.write(display)
    # save host application pid
    window_pid = xdo_get_window_pid(host, display, run_cmd)
    if window_pid:
        with open(f'/{TMP_DIR}/{session_id}.pid', 'w', encoding="UTF-8") as file_pointer:
            file_pointer.write(window_pid)
    else:
        logger.warning("Could not get window pid.")


def gen_window_name(run_cmd):
    return run_cmd.split(' ')[0].split('/')[-1]

def xdo_get_window_id_cmd(display, run_cmd):
    window_name = gen_window_name(run_cmd)
    return f'DISPLAY={display} xdotool search --onlyvisible --name "{window_name}"'

def xdo_get_window_id(host, display, run_cmd):
    try:
        cmd = xdo_get_window_id_cmd(display, run_cmd)
        return ssh(host, cmd).strip()
    except ErrorReturnCode:
        return None

def xdo_get_window_pid(host, display, run_cmd):
    cmd = f'DISPLAY={display} xdotool getwindowpid $({xdo_get_window_id_cmd(display, run_cmd)})'
    try:
        return ssh(host, cmd).strip()
    except ErrorReturnCode:
        return None

def xdo_get_window_size(host, display, run_cmd):
    cmd = f'DISPLAY={display} xdotool getwindowgeometry $({xdo_get_window_id_cmd(display, run_cmd)})'
    try:
        geom = ssh(host, cmd).strip()
        return [int(value) for value in geom.split(' ')[-1].split('x')]
    except ErrorReturnCode:
        return None, None

def xdo_set_window_size(host, display, run_cmd, width, height):
    cmd = f'DISPLAY={display} xdotool windowsize --sync $({xdo_get_window_id_cmd(display, run_cmd)}) {width} {height}'
    try:
        ssh(host, cmd)
    except ErrorReturnCode:
        pass

def xdo_move_window_to_top_left(host, display, run_cmd):
    cmd = f'DISPLAY={display} xdotool windowmove $({xdo_get_window_id_cmd(display, run_cmd)}) 0 0'
    try:
        ssh(host, cmd)
    except ErrorReturnCode:
        pass

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
        self.display = None
        self.thinclient_resolution = None
        # close event
        self.connect("destroy", Gtk.main_quit)
        # set resizable
        self.set_resizable(True)
        # headerbar
        if not self.uncolored:
            host_color_name = get_host_color_name(self.host)
            self.set_headerbar_color(host_color_name)
        self.set_title(f"[{self.host}] {gen_window_name(run_cmd)}")
        # initialize vnc display
        initialize_vnc_display(host, port, run_cmd, session_id, self)

    def vnc_display_initialized(self, display, width, height):
        self.display = display
        # set initial size
        logger.debug("Initializing size")
        if width and height:
            self.resize(width, height)
        else:
            logger.warning("Could not get window size.")
        # initialize resize listener
        self.connect_resize_event(self._on_resize)
        self.show_all()

    def _on_resize(self, _width, _height):
        width, height = _width, _height
        if not self.thinclient_resolution:
            self.thinclient_resolution = get_thinclient_resolution()
        if not self.uncolored and width < self.thinclient_resolution[0]:
            width, height = _width - 50, _height - 90
        # resize host application to the size of the vncviewer
        xdo_set_window_size(self.host, self.display, self.run_cmd, width, height)
    
    def run(self):
        Gtk.main()


def gen_grep_kill_cmd(grep_arg):
    return f"ps -ef | grep {grep_arg} | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"

def kill_host_application(host, session_id):
    if not os.path.exists(f'/{TMP_DIR}/{session_id}.pid'):
        return
    with open(f'/{TMP_DIR}/{session_id}.pid', 'r', encoding="UTF-8") as file_pointer:
        window_pid = file_pointer.read().strip()
        ssh(
            host,
            f'kill -9 {window_pid} || true',
            _bg=True, _bg_exc=False
        )
        os.remove(f'/{TMP_DIR}/{session_id}.pid')

def kill_x11vnc(host, port, session_id):
    # killing xvfb and x11vnc
    if not os.path.exists(f'/{TMP_DIR}/{session_id}.display'):
        return
    with open(f'/{TMP_DIR}/{session_id}.display', 'r', encoding="UTF-8") as file_pointer:
        display = file_pointer.read().strip()
        kill_cmd = gen_grep_kill_cmd(f"-e 'Xvfb {display}' -e '-rfbport {port}'")
        ssh(
            host,
            kill_cmd,
            _bg=True, _bg_exc=False
        )
        os.remove(f'/{TMP_DIR}/{session_id}.display')

def kill_ssh_tunnel(port):
    ssh_killcmd = gen_grep_kill_cmd(f"-e '-L {port}:localhost:{port}'")
    Command('sh')('-c',
        ssh_killcmd,
        _bg=True, _bg_exc=False
    )

# all this processes should already be killed when exiting the host application
# but let's ensure to not have zombie processes
def cleanup(host, port, session_id):
    kill_host_application(host, session_id)
    kill_x11vnc(host, port, session_id)
    kill_ssh_tunnel(port)


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
        vnc_viewer = VNCViewer(host, port, cmd, session_id, uncolored)
        vnc_viewer.run()
    finally:
        cleanup(host, port, session_id)
