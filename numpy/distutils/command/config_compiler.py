import sys
from distutils.core import Command
from numpy.distutils import log

#XXX: Implement confic_cc for enhancing C/C++ compiler options.
#XXX: Linker flags

def show_fortran_compilers(_cache=[]):
    # Using cache to prevent infinite recursion
    if _cache: return
    _cache.append(1)
    log.set_verbosity(-2)
    from numpy.distutils.fcompiler import show_fcompilers
    import distutils.core
    dist = distutils.core._setup_distribution
    show_fcompilers(dist)
    return

class config_fc(Command):
    """ Distutils command to hold user specified options
    to Fortran compilers.

    config_fc command is used by the FCompiler.customize() method.
    """

    user_options = [
        ('fcompiler=',None,"specify Fortran compiler type"),
        ('f77exec=', None, "specify F77 compiler command"),
        ('f90exec=', None, "specify F90 compiler command"),
        ('f77flags=',None,"specify F77 compiler flags"),
        ('f90flags=',None,"specify F90 compiler flags"),
        ('opt=',None,"specify optimization flags"),
        ('arch=',None,"specify architecture specific optimization flags"),
        ('debug','g',"compile with debugging information"),
        ('noopt',None,"compile without optimization"),
        ('noarch',None,"compile without arch-dependent optimization"),
        ]

    help_options = [
        ('help-fcompiler',None, "list available Fortran compilers",
         show_fortran_compilers),
        ]

    boolean_options = ['debug','noopt','noarch']

    def initialize_options(self):
        self.fcompiler = None
        self.f77exec = None
        self.f90exec = None
        self.f77flags = None
        self.f90flags = None
        self.opt = None
        self.arch = None
        self.debug = None
        self.noopt = None
        self.noarch = None
        return

    def finalize_options(self):
        log.info('unifing config_fc, config, build_clib, build_ext commands --fcompiler options')
        build_clib = self.get_finalized_command('build_clib')
        build_ext = self.get_finalized_command('build_ext')
        config = self.get_finalized_command('config')
        cmd_list = [self, config, build_clib, build_ext]
        for a in ['fcompiler']:
            l = []
            for c in cmd_list:
                v = getattr(c,a)
                if v is not None and v not in l: l.append(v)
            if not l: v1 = None
            else: v1 = l[0]
            if len(l)>1:
                log.warn('  commands have different --%s options: %s'\
                         ', using first in list as default' % (a, l))
            if v1:
                for c in cmd_list:
                    if getattr(c,a) is None: setattr(c, a, v1)
        return

    def run(self):
        # Do nothing.
        return

class config_cc(Command):
    """ Distutils command to hold user specified options
    to C/C++ compilers.
    """

    user_options = [
        ('compiler=',None,"specify C/C++ compiler type"),
        ]

    def initialize_options(self):
        self.compiler = None
        return

    def finalize_options(self):
        log.info('unifing config_cc, config, build_clib, build_ext commands --compiler options')
        build_clib = self.get_finalized_command('build_clib')
        build_ext = self.get_finalized_command('build_ext')
        config = self.get_finalized_command('config')
        cmd_list = [self, config, build_clib, build_ext]
        for a in ['compiler']:
            l = []
            for c in cmd_list:
                v = getattr(c,a)
                if v is not None and v not in l: l.append(v)
            if not l: v1 = None
            else: v1 = l[0]
            if len(l)>1:
                log.warn('  commands have different --%s options: %s'\
                         ', using first in list as default' % (a, l))
            if v1:
                for c in cmd_list:
                    if getattr(c,a) is None: setattr(c, a, v1)
        return

    def run(self):
        # Do nothing.
        return
