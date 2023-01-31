import platform

if platform.system() == "Darwin":
    from tower.osutils.darwin import *
elif platform.system() == "Linux":
    from tower.osutils.linux import *
elif platform.system() == "Darwin":
    from tower.osutils.windows import *

from tower.osutils.keymaps import *
