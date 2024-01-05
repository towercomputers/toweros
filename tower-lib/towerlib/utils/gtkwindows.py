import logging

# pylint: disable=wrong-import-position,no-name-in-module
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkVnc', '2.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
# pylint: enable=wrong-import-position,no-name-in-module

from towerlib.config import VNC_VIEWER_CSS

logger = logging.getLogger('tower')

# pylint: disable=too-few-public-methods
class ResizableWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self._timer_id = None
        self._event_id_size_allocate = None
        self._remembered_size = None
        self.on_resize_callback = None

    def connect_resize_event(self, on_resize_callback):
        self.on_resize_callback = on_resize_callback
        self._timer_id = None
        eid = self.connect('size-allocate', self._on_size_allocated)
        self._event_id_size_allocate = eid

    def _on_size_allocated(self, _, alloc):
        # don't install a second timer
        if self._timer_id:
            return
        # remember new size
        self._remembered_size = alloc
        # disconnect the 'size-allocate' event
        self.disconnect(self._event_id_size_allocate)
        # create a 500ms timer
        tid = GLib.timeout_add(interval=500, function=self._on_size_timer)
        # ...and remember its id
        self._timer_id = tid

    def _on_size_timer(self):
        # current window size
        curr = self.get_allocated_size().allocation
        # was the size changed in the last 500ms?
        # NO changes anymore
        if self._remembered_size.equal(curr):  # == doesn't work here
            logger.debug("Window size changed to %sx%s", curr.width, curr.height)
            self.on_resize_callback(curr.width, curr.height)
            # reconnect the 'size-allocate' event
            self.connect_resize_event(self.on_resize_callback)
            # stop the timer
            self._timer_id = None
            return False
        # YES size was changed
        # remember the new size for the next check after 500ms
        self._remembered_size = curr
        # repeat timer
        return True


# pylint: disable=too-few-public-methods
class ColorableWindow(ResizableWindow):
    def __init__(self):
        ResizableWindow.__init__(self)

    def set_headerbar_color(self, color_name):
        bg_filename = f"/var/towercomputers/backgrounds/square-{color_name.replace(' ', '-').lower()}.png"
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        self.set_titlebar(headerbar)
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        css = VNC_VIEWER_CSS.replace('BACKGROUND_FILENAME', bg_filename)
        provider.load_from_data(css)
