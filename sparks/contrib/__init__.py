import sys

if sys.version_info[0] > 2:
    from ..contrib import lsb_release3 as lsb_release
else:
    from ..contrib import lsb_release2 as lsb_release # NOQA
