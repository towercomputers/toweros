import platform

if platform.system() == "Darwin":
    from tower.osutils.darwin import *
    from tower.osutils.keymaps import *
elif platform.system() == "Linux":
    from tower.osutils.linux import *
elif platform.system() == "Windows":
    from tower.osutils.windows import *

from tower.osutils.common import *
