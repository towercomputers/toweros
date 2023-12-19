from __future__ import print_function
import time
import logging
from io import StringIO
import uuid
import os
import socket
from contextlib import closing

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkVnc', '2.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GtkVnc
from gi.repository import GLib

from sh import ssh, Command

logger = logging.getLogger('tower')

X11VNC_TIMEOUT = 5

def wait_for_output(_out, expected_output):
    start_time = time.time()
    elapsed_time = 0
    process_output = _out.getvalue()
    while expected_output not in process_output:
        process_output = _out.getvalue()
        elapsed_time = time.time() - start_time
        if elapsed_time > X11VNC_TIMEOUT:
            print(process_output)
            raise Exception(f"x11vnc not ready after {X11VNC_TIMEOUT}s")
    logger.debug(process_output)

class VNCViewer(Gtk.Window):
    def __init__(self, host, port, run_cmd, session_id):
        Gtk.Window.__init__(self)
        self.host = host
        self.port = port
        self.run_cmd = run_cmd
        self.session_id = session_id
        self.init_size_timer = None
        self.window_id = None
        self.window_pid = None
        self.ssh_process = None
        self.set_resizable(False)
        # close event
        self.connect('delete-event', self._vnc_close)
        self.connect("destroy", Gtk.main_quit)


        self.hb = Gtk.HeaderBar()
        self.hb.set_show_close_button(True)
        self.set_titlebar(self.hb)

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        css = """
        headerbar {
            padding: 0px;
            margin: 0px;
            min-height: 0px;
            padding-left: 2px; /* same as childrens vertical margins for nicer proportions */
            padding-right: 2px;
            /* background-image: url("/var/towercomputers/wallpapers/wallpaper1.jpg"); */
            background-size: cover;
        }

        headerbar entry,
        headerbar spinbutton,
        headerbar button,
        headerbar separator {
            margin-top: 0px; /* same as headerbar side padding for nicer proportions */
            margin-bottom: 0px;
            padding: 1px;
        }

        /* shrink ssd titlebars */
        .default-decoration {
            min-height: 0; /* let the entry and button drive the titlebar size */
            padding: 0px;
            background-color: #FF0000;
        }

        .default-decoration .titlebutton {
            min-height: 0px; /* tweak these two props to reduce button size */
            min-width: 0px;
        }

        window.ssd headerbar.titlebar {
            padding-top: 0;
            padding-bottom: 0;
            min-height: 0;
        }
        """
        provider.load_from_data(css)

        self.set_title(host)
        self.layout = Gtk.Layout()
        self.add(self.layout)
        self.loading_label = Gtk.Label(label="Connecting to %s:%s" % (host, port))
        self.layout.add(self.loading_label)
        self.show_all()
        self._start_x11vnc_server()
        # initialize vnc display
        self._initialize_vnc_display()
    
    def _start_x11vnc_server(self):
        self.x11vnc_output = StringIO()
        vnc_cmd = f"x11vnc -create -nowf -nowcr -cursor arrow -ncache 20 -ncache_cr -env FD_PROG='{self.run_cmd}' -nopw -listen 127.0.0.1 -rfbport {self.port}"
        self.ssh_process = ssh(
            self.host, 
            "-L", f"{self.port}:localhost:{self.port}", 
            vnc_cmd,
            _err_to_out=True, _out=self.x11vnc_output, _bg=True, _bg_exc=False
        )
        wait_for_output(self.x11vnc_output, "PORT=")

    def _refresh_window_id(self):
        new_window_id = self._search_window_id()
        if new_window_id != self.window_id:
            self.window_id = new_window_id
            return True
        return False
    
    def _set_app_size(self, width, height):
        try:
            ssh(self.host, f'DISPLAY={self.display} xdotool windowsize --sync {self.window_id} {width} {height}')
        except Exception as e:
            if self._refresh_window_id():
                self._set_app_size(width, height)

    def _get_app_size(self):
        try:
            width, height = ssh(self.host, f'DISPLAY={self.display} xdotool getwindowgeometry {self.window_id}').split(' ')[-1].split('x')
            return int(width), int(height)
        except Exception as e:
            if self._refresh_window_id():
                return self._get_app_size()
            return 200, 200
    
    def _update_window_pid(self):
        try:
            self.window_pid = ssh(self.host, f'DISPLAY={self.display} xdotool getwindowpid {self.window_id}').strip()
            with open(f'/tmp/{self.session_id}.pid', 'w') as f:
                f.write(self.window_pid)
        except Exception as e:
            if self._refresh_window_id():
                return self._update_window_pid()
            
    def _update_session_display(self):
        self.display = self.x11vnc_output.getvalue().split(" Using X display")[1].split("\n")[0].strip()
        print("DISPLAY=%s" % self.display)
        with open(f'/tmp/{self.session_id}.display', 'w') as f:
            f.write(self.display)
        
    def _window_name(self):
        name = self.run_cmd.split(' ')[0]
        return name.split('/')[-1]

    def _search_window_id(self):
        try:
            cmd = f'DISPLAY={self.display} xdotool search --onlyvisible --name "{self._window_name()}"'
            return ssh(self.host, cmd).strip()
        except Exception as e:
            return None

    def _initialize_vnc_display(self):
        self.vnc = GtkVnc.Display()
        self.layout.add(self.vnc)
        self.vnc.realize()
        self.vnc.set_pointer_grab(True)
        self.vnc.set_keyboard_grab(True)
        # Example to change grab key combination to Ctrl+Alt+g
        grab_keys = GtkVnc.GrabSequence.new([ Gdk.KEY_Control_L, Gdk.KEY_Alt_L, Gdk.KEY_g ])
        self.vnc.set_grab_keys(grab_keys)
        self.vnc.open_host("localhost", self.port)
        self.vnc.connect("vnc-pointer-grab", self._vnc_grab)
        self.vnc.connect("vnc-pointer-ungrab", self._vnc_ungrab)
        self.vnc.connect("vnc-connected", self._vnc_connected)
        self.vnc.connect("vnc-initialized", self._vnc_initialized)
        self.vnc.connect("vnc-disconnected", self._vnc_disconnected)

    def _init_size(self):
        self._refresh_window_id()
        if self.window_id is None:
            self.init_size_timer = GLib.timeout_add(interval=1000, function=self._init_size)
            return
        self.init_size_timer = None
        width, height = self._get_app_size()
        self.resize(width, height)
        self.set_resizable(True)
        self._update_window_pid()
        # "resize" event
        self._connect_resize_event()

    def _connect_resize_event(self):
        self._timer_id = None
        eid = self.connect('size-allocate', self._on_size_allocated)
        self._event_id_size_allocate = eid

    def _on_delete_event(self, a, b):
        Gtk.main_quit()

    def _on_size_allocated(self, widget, alloc):
        if self.init_size_timer:
            return
        # don't install a second timer
        if self._timer_id:
            return
        # remember new size
        self._remembered_size = alloc
        # disconnect the 'size-allocate' event
        self.disconnect(self._event_id_size_allocate)
        # create a 500ms timer
        tid = GLib.timeout_add(interval=100, function=self._on_size_timer)
        # ...and remember its id
        self._timer_id = tid

    def _on_size_timer(self):
        # current window size
        curr = self.get_allocated_size().allocation
        # was the size changed in the last 500ms?
        # NO changes anymore
        if self._remembered_size.equal(curr):  # == doesn't work here
            self._set_app_size(curr.width, curr.height)
            # reconnect the 'size-allocate' event
            self._connect_resize_event()
            # stop the timer
            self._timer_id = None
            return False
        # YES size was changed
        # remember the new size for the next check after 500ms
        self._remembered_size = curr
        # repeat timer
        return True

    def _set_title(self, grabbed):
        keys = self.vnc.get_grab_keys()
        keystr = None
        for i in range(keys.nkeysyms):
            k = keys.get_nth(i)
            if keystr is None:
                keystr = Gdk.keyval_name(k)
            else:
                keystr = keystr + "+" + Gdk.keyval_name(k)
        if grabbed:
            subtitle = "(Press %s to release pointer) " % keystr
        else:
            subtitle = ""
        self.set_title(f"[{self.host}] {self._window_name()} {subtitle}")
    
    def _vnc_close(self, src, data=None):
        print("Window closed by user")
        self.vnc.send_keys([Gdk.KEY_Control_L, Gdk.KEY_q])
        return True
        #Gtk.main_quit()

    def _vnc_grab(self, src):
        self._set_title(True)

    def _vnc_ungrab(self, src):
        self._set_title(False)

    def _vnc_connected(self, src):
        print("Connected to server")

    def _vnc_initialized(self, src):
        print("Connection initialized")
        print(self.x11vnc_output.getvalue())
        self.layout.remove(self.loading_label)
        self._set_title(False)
        self._update_session_display()
        self._init_size()
        
        self.show_all()

    def _vnc_disconnected(self, src):
        print("Disconnected from server")
        Gtk.main_quit()

def cleanup(host, port, session_id):
    # killing application
    if os.path.exists(f'/tmp/{session_id}.pid'):
        with open(f'/tmp/{session_id}.pid', 'r') as f:
            window_pid = f.read().strip()
            ssh(host, f'kill -9 {window_pid} || true', _bg=True, _bg_exc=False)
            os.remove(f'/tmp/{session_id}.pid')
    # killing xvfb and x11vnc
    if os.path.exists(f'/tmp/{session_id}.display'):
        with open(f'/tmp/{session_id}.display', 'r') as f:
            display = f.read().strip()
            kill_cmd = f"ps -ef | grep -e 'Xvfb {display}' -e '-rfbport {port}' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
            ssh(host, kill_cmd, _bg=True, _bg_exc=False)
            os.remove(f'/tmp/{session_id}.display')
    # killing ssh tunnel
    ssh_killcmd = f"ps -ef | grep '{port}:localhost:{port} x11vnc' | grep -v grep | awk '{{print $2}}' | xargs kill 2>/dev/null || true"
    Command('sh')('-c', ssh_killcmd, _bg=True, _bg_exc=False)

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    
def run(host, run_cmd):
    port = str(find_free_port())
    session_id = uuid.uuid1()
    try:
        VNCViewer(host, port, run_cmd, session_id)
        Gtk.main()
    finally:
        cleanup(host, port, session_id)

# for testing because py3-gobject doesn't work with hatch :(
if __name__ == "__main__":
    import sys
    run(sys.argv[1], ' '.join(sys.argv[2:]))