
from __version__ import version as __version__
# Must import local ccompiler ASAP in order to get
# customized CCompiler.spawn effective.
import ccompiler
import unixccompiler

try:
    import __config__
    _INSTALLED = True
except ImportError:
    _INSTALLED = False

if _INSTALLED:
    from scipy.test.testing import ScipyTest 
    test = ScipyTest('scipy.distutils').test
