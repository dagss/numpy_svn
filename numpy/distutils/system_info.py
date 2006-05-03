#!/usr/bin/env python
"""
This file defines a set of system_info classes for getting
information about various resources (libraries, library directories,
include directories, etc.) in the system. Currently, the following
classes are available:

  atlas_info
  atlas_threads_info
  atlas_blas_info
  atlas_blas_threads_info
  lapack_atlas_info
  blas_info
  lapack_info
  blas_opt_info       # usage recommended
  lapack_opt_info     # usage recommended
  fftw_info,dfftw_info,sfftw_info
  fftw_threads_info,dfftw_threads_info,sfftw_threads_info
  djbfft_info
  x11_info
  lapack_src_info
  blas_src_info
  numpy_info
  numarray_info
  numpy_info
  boost_python_info
  agg2_info
  wx_info
  gdk_pixbuf_xlib_2_info
  gdk_pixbuf_2_info
  gdk_x11_2_info
  gtkp_x11_2_info
  gtkp_2_info
  xft_info
  freetype2_info
  umfpack_info

Usage:
    info_dict = get_info(<name>)
  where <name> is a string 'atlas','x11','fftw','lapack','blas',
  'lapack_src', 'blas_src', etc. For a complete list of allowed names,
  see the definition of get_info() function below.

  Returned info_dict is a dictionary which is compatible with
  distutils.setup keyword arguments. If info_dict == {}, then the
  asked resource is not available (system_info could not find it).

  Several *_info classes specify an environment variable to specify
  the locations of software. When setting the corresponding environment
  variable to 'None' then the software will be ignored, even when it
  is available in system.

Global parameters:
  system_info.search_static_first - search static libraries (.a)
             in precedence to shared ones (.so, .sl) if enabled.
  system_info.verbosity - output the results to stdout if enabled.

The file 'site.cfg' is looked for in

1) Directory of main setup.py file being run.
2) Home directory of user running the setup.py file (Not implemented yet)
3) System wide directory (location of this file...)

The first one found is used to get system configuration options The
format is that used by ConfigParser (i.e., Windows .INI style). The
section DEFAULT has options that are the default for each section. The
available sections are fftw, atlas, and x11. Appropiate defaults are
used if nothing is specified.

The order of finding the locations of resources is the following:
 1. environment variable
 2. section in site.cfg
 3. DEFAULT section in site.cfg
Only the first complete match is returned.

Example:
----------
[DEFAULT]
library_dirs = /usr/lib:/usr/local/lib:/opt/lib
include_dirs = /usr/include:/usr/local/include:/opt/include
src_dirs = /usr/local/src:/opt/src
# search static libraries (.a) in preference to shared ones (.so)
search_static_first = 0

[fftw]
fftw_libs = rfftw, fftw
fftw_opt_libs = rfftw_threaded, fftw_threaded
# if the above aren't found, look for {s,d}fftw_libs and {s,d}fftw_opt_libs

[atlas]
library_dirs = /usr/lib/3dnow:/usr/lib/3dnow/atlas
# for overriding the names of the atlas libraries
atlas_libs = lapack, f77blas, cblas, atlas

[x11]
library_dirs = /usr/X11R6/lib
include_dirs = /usr/X11R6/include
----------

Authors:
  Pearu Peterson <pearu@cens.ioc.ee>, February 2002
  David M. Cooke <cookedm@physics.mcmaster.ca>, April 2002

Copyright 2002 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@cens.ioc.ee>
Permission to use, modify, and distribute this software is given under the
terms of the SciPy (BSD style) license.  See LICENSE.txt that came with
this distribution for specifics.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""

import sys,os,re
import warnings
from distutils.errors import DistutilsError
from glob import glob
import ConfigParser
from exec_command import find_executable, exec_command, get_pythonexe
from numpy.distutils.misc_util import is_sequence, is_string
import distutils.sysconfig

from distutils.sysconfig import get_config_vars

if sys.platform == 'win32':
    default_lib_dirs = ['C:\\',
                        os.path.join(distutils.sysconfig.EXEC_PREFIX,
                                     'libs')]
    default_include_dirs = []
    default_src_dirs = ['.']
    default_x11_lib_dirs = []
    default_x11_include_dirs = []
else:
    default_lib_dirs = ['/usr/local/lib', '/opt/lib', '/usr/lib',
                        '/opt/local/lib', '/sw/lib']
    default_include_dirs = ['/usr/local/include',
                            '/opt/include', '/usr/include',
                            '/opt/local/include', '/sw/include']
    default_src_dirs = ['.','/usr/local/src', '/opt/src','/sw/src']
    default_x11_lib_dirs = ['/usr/X11R6/lib','/usr/X11/lib','/usr/lib']
    default_x11_include_dirs = ['/usr/X11R6/include','/usr/X11/include',
                                '/usr/include']

if os.path.join(sys.prefix, 'lib') not in default_lib_dirs:
    default_lib_dirs.insert(0,os.path.join(sys.prefix, 'lib'))
    default_include_dirs.append(os.path.join(sys.prefix, 'include'))
    default_src_dirs.append(os.path.join(sys.prefix, 'src'))

default_lib_dirs = filter(os.path.isdir, default_lib_dirs)
default_include_dirs = filter(os.path.isdir, default_include_dirs)
default_src_dirs = filter(os.path.isdir, default_src_dirs)

so_ext = get_config_vars('SO')[0] or ''

def get_standard_file(fname):
    """Returns a list of files named 'fname' from
    1) System-wide directory (directory-location of this module)
    2) Users HOME directory (os.environ['HOME'])
    3) Local directory
    """
    # System-wide file
    filenames = []
    try:
        f = __file__
    except NameError:
        f = sys.argv[0]
    else:
        sysfile = os.path.join(os.path.split(os.path.abspath(f))[0],
                               fname)
        if os.path.isfile(sysfile):
            filenames.append(sysfile)

    # Home directory
    # And look for the user config file
    try:
        f = os.environ['HOME']
    except KeyError:
        pass
    else:
        user_file = os.path.join(f, fname)
        if os.path.isfile(user_file):
            filenames.append(user_file)

    # Local file
    if os.path.isfile(fname):
        filenames.append(os.path.abspath(fname))

    return filenames

def get_info(name,notfound_action=0):
    """
    notfound_action:
      0 - do nothing
      1 - display warning message
      2 - raise error
    """
    cl = {'atlas':atlas_info,  # use lapack_opt or blas_opt instead
          'atlas_threads':atlas_threads_info,                # ditto
          'atlas_blas':atlas_blas_info,
          'atlas_blas_threads':atlas_blas_threads_info,
          'lapack_atlas':lapack_atlas_info,  # use lapack_opt instead
          'lapack_atlas_threads':lapack_atlas_threads_info,  # ditto
          'mkl':mkl_info,
          'lapack_mkl':lapack_mkl_info,      # use lapack_opt instead
          'blas_mkl':blas_mkl_info,          # use blas_opt instead
          'x11':x11_info,
          'fft_opt':fft_opt_info,
          'fftw':fftw_info,
          'fftw2':fftw2_info,
          'fftw3':fftw3_info,
          'dfftw':dfftw_info,
          'sfftw':sfftw_info,
          'fftw_threads':fftw_threads_info,
          'dfftw_threads':dfftw_threads_info,
          'sfftw_threads':sfftw_threads_info,
          'djbfft':djbfft_info,
          'blas':blas_info,                  # use blas_opt instead
          'lapack':lapack_info,              # use lapack_opt instead
          'lapack_src':lapack_src_info,
          'blas_src':blas_src_info,
          'numpy':numpy_info,
          'f2py':f2py_info,
          'Numeric':Numeric_info,
          'numeric':Numeric_info,
          'numarray':numarray_info,
          'numerix':numerix_info,
          'lapack_opt':lapack_opt_info,
          'blas_opt':blas_opt_info,
          'boost_python':boost_python_info,
          'agg2':agg2_info,
          'wx':wx_info,
          'gdk_pixbuf_xlib_2':gdk_pixbuf_xlib_2_info,
          'gdk-pixbuf-xlib-2.0':gdk_pixbuf_xlib_2_info,
          'gdk_pixbuf_2':gdk_pixbuf_2_info,
          'gdk-pixbuf-2.0':gdk_pixbuf_2_info,
          'gdk':gdk_info,
          'gdk_2':gdk_2_info,
          'gdk-2.0':gdk_2_info,
          'gdk_x11_2':gdk_x11_2_info,
          'gdk-x11-2.0':gdk_x11_2_info,
          'gtkp_x11_2':gtkp_x11_2_info,
          'gtk+-x11-2.0':gtkp_x11_2_info,
          'gtkp_2':gtkp_2_info,
          'gtk+-2.0':gtkp_2_info,
          'xft':xft_info,
          'freetype2':freetype2_info,
          'umfpack':umfpack_info,
          'amd':amd_info,
          }.get(name.lower(),system_info)
    return cl().get_info(notfound_action)

class NotFoundError(DistutilsError):
    """Some third-party program or library is not found."""

class AtlasNotFoundError(NotFoundError):
    """
    Atlas (http://math-atlas.sourceforge.net/) libraries not found.
    Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [atlas]) or by setting
    the ATLAS environment variable."""

class LapackNotFoundError(NotFoundError):
    """
    Lapack (http://www.netlib.org/lapack/) libraries not found.
    Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [lapack]) or by setting
    the LAPACK environment variable."""

class LapackSrcNotFoundError(LapackNotFoundError):
    """
    Lapack (http://www.netlib.org/lapack/) sources not found.
    Directories to search for the sources can be specified in the
    numpy/distutils/site.cfg file (section [lapack_src]) or by setting
    the LAPACK_SRC environment variable."""

class BlasNotFoundError(NotFoundError):
    """
    Blas (http://www.netlib.org/blas/) libraries not found.
    Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [blas]) or by setting
    the BLAS environment variable."""

class BlasSrcNotFoundError(BlasNotFoundError):
    """
    Blas (http://www.netlib.org/blas/) sources not found.
    Directories to search for the sources can be specified in the
    numpy/distutils/site.cfg file (section [blas_src]) or by setting
    the BLAS_SRC environment variable."""

class FFTWNotFoundError(NotFoundError):
    """
    FFTW (http://www.fftw.org/) libraries not found.
    Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [fftw]) or by setting
    the FFTW environment variable."""

class DJBFFTNotFoundError(NotFoundError):
    """
    DJBFFT (http://cr.yp.to/djbfft.html) libraries not found.
    Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [djbfft]) or by setting
    the DJBFFT environment variable."""

class NumericNotFoundError(NotFoundError):
    """
    Numeric (http://www.numpy.org/) module not found.
    Get it from above location, install it, and retry setup.py."""

class X11NotFoundError(NotFoundError):
    """X11 libraries not found."""

class UmfpackNotFoundError(NotFoundError):
    """
    UMFPACK sparse solver (http://www.cise.ufl.edu/research/sparse/umfpack/)
    not found. Directories to search for the libraries can be specified in the
    numpy/distutils/site.cfg file (section [umfpack]) or by setting
    the UMFPACK environment variable."""

class system_info:

    """ get_info() is the only public method. Don't use others.
    """
    section = 'DEFAULT'
    dir_env_var = None
    search_static_first = 0 # XXX: disabled by default, may disappear in
                            # future unless it is proved to be useful.
    verbosity = 1
    saved_results = {}

    notfounderror = NotFoundError

    def __init__ (self,
                  default_lib_dirs=default_lib_dirs,
                  default_include_dirs=default_include_dirs,
                  verbosity = 1,
                  ):
        self.__class__.info = {}
        self.local_prefixes = []
        defaults = {}
        defaults['libraries'] = ''
        defaults['library_dirs'] = os.pathsep.join(default_lib_dirs)
        defaults['include_dirs'] = os.pathsep.join(default_include_dirs)
        defaults['src_dirs'] = os.pathsep.join(default_src_dirs)
        defaults['search_static_first'] = str(self.search_static_first)
        self.cp = ConfigParser.ConfigParser(defaults)
        self.files = get_standard_file('site.cfg')
        self.parse_config_files()
        self.search_static_first = self.cp.getboolean(self.section,
                                                      'search_static_first')
        assert isinstance(self.search_static_first, int)

    def parse_config_files(self):
        self.cp.read(self.files)
        if not self.cp.has_section(self.section):
            self.cp.add_section(self.section)

    def calc_libraries_info(self):
        libs = self.get_libraries()
        dirs = self.get_lib_dirs()
        info = {}
        for lib in libs:
            i = None
            for d in dirs:
                i = self.check_libs(d,[lib])
                if i is not None:
                    break
            if i is not None:
                dict_append(info,**i)
            else:
                print 'Library %s was not found. Ignoring' % (lib)
        return info

    def set_info(self,**info):
        if info:
            lib_info = self.calc_libraries_info()
            dict_append(info,**lib_info)
        self.saved_results[self.__class__.__name__] = info

    def has_info(self):
        return self.saved_results.has_key(self.__class__.__name__)

    def get_info(self,notfound_action=0):
        """ Return a dictonary with items that are compatible
            with numpy.distutils.setup keyword arguments.
        """
        flag = 0
        if not self.has_info():
            flag = 1
            if self.verbosity>0:
                print self.__class__.__name__ + ':'
            if hasattr(self, 'calc_info'):
                self.calc_info()
            if notfound_action:
                if not self.has_info():
                    if notfound_action==1:
                        warnings.warn(self.notfounderror.__doc__)
                    elif notfound_action==2:
                        raise self.notfounderror,self.notfounderror.__doc__
                    else:
                        raise ValueError(repr(notfound_action))

            if self.verbosity>0:
                if not self.has_info():
                    print '  NOT AVAILABLE'
                    self.set_info()
                else:
                    print '  FOUND:'

        res = self.saved_results.get(self.__class__.__name__)
        if self.verbosity>0 and flag:
            for k,v in res.items():
                v = str(v)
                if k=='sources' and len(v)>200: v = v[:60]+' ...\n... '+v[-60:]
                print '    %s = %s'%(k,v)
            print

        return res

    def get_paths(self, section, key):
        dirs = self.cp.get(section, key).split(os.pathsep)
        env_var = self.dir_env_var
        if env_var:
            if is_sequence(env_var):
                e0 = env_var[-1]
                for e in env_var:
                    if os.environ.has_key(e):
                        e0 = e
                        break
                if not env_var[0]==e0:
                    print 'Setting %s=%s' % (env_var[0],e0)
                env_var = e0
        if env_var and os.environ.has_key(env_var):
            d = os.environ[env_var]
            if d=='None':
                print 'Disabled',self.__class__.__name__,'(%s is None)' \
                      % (self.dir_env_var)
                return []
            if os.path.isfile(d):
                dirs = [os.path.dirname(d)] + dirs
                l = getattr(self,'_lib_names',[])
                if len(l)==1:
                    b = os.path.basename(d)
                    b = os.path.splitext(b)[0]
                    if b[:3]=='lib':
                        print 'Replacing _lib_names[0]==%r with %r' \
                              % (self._lib_names[0], b[3:])
                        self._lib_names[0] = b[3:]
            else:
                ds = d.split(os.pathsep)
                ds2 = []
                for d in ds:
                    if os.path.isdir(d):
                        ds2.append(d)
                        for dd in ['include','lib']:
                            d1 = os.path.join(d,dd)
                            if os.path.isdir(d1):
                                ds2.append(d1)
                dirs = ds2 + dirs
        default_dirs = self.cp.get('DEFAULT', key).split(os.pathsep)
        dirs.extend(default_dirs)
        ret = []
        [ret.append(d) for d in dirs if os.path.isdir(d) and d not in ret]
        if self.verbosity>1:
            print '(',key,'=',':'.join(ret),')'
        return ret

    def get_lib_dirs(self, key='library_dirs'):
        return self.get_paths(self.section, key)

    def get_include_dirs(self, key='include_dirs'):
        return self.get_paths(self.section, key)

    def get_src_dirs(self, key='src_dirs'):
        return self.get_paths(self.section, key)

    def get_libs(self, key, default):
        try:
            libs = self.cp.get(self.section, key)
        except ConfigParser.NoOptionError:
            if not default:
                return []
            if is_string(default):
                return [default]
            return default
        return [b for b in [a.strip() for a in libs.split(',')] if b]

    def get_libraries(self, key='libraries'):
        return self.get_libs(key,'')

    def check_libs(self,lib_dir,libs,opt_libs =[]):
        """ If static or shared libraries are available then return
            their info dictionary. """
        if self.search_static_first:
            exts = ['.a',so_ext]
        else:
            exts = [so_ext,'.a']
        if sys.platform=='cygwin':
            exts.append('.dll.a')
        for ext in exts:
            info = self._check_libs(lib_dir,libs,opt_libs,[ext])
            if info is not None: return info
        return

    def check_libs2(self,lib_dir,libs,opt_libs =[]):
        """ If static or shared libraries are available then return
            their info dictionary. """
        if self.search_static_first:
            exts = ['.a',so_ext]
        else:
            exts = [so_ext,'.a']
        if sys.platform=='cygwin':
            exts.append('.dll.a')
        info = self._check_libs(lib_dir,libs,opt_libs,exts)
        if info is not None: return info
        return

    def _lib_list(self, lib_dir, libs, exts):
        assert is_string(lib_dir)
        liblist = []
        for l in libs:
            for ext in exts:
                p = self.combine_paths(lib_dir, 'lib'+l+ext)
                if p:
                    assert len(p)==1
                    liblist.append(p[0])
                    break
        return liblist

    def _extract_lib_names(self,libs):
        return [os.path.splitext(os.path.basename(p))[0][3:] \
                for p in libs]

    def _check_libs(self,lib_dir,libs, opt_libs, exts):
        found_libs = self._lib_list(lib_dir, libs, exts)
        if len(found_libs) == len(libs):
            found_libs = self._extract_lib_names(found_libs)
            info = {'libraries' : found_libs, 'library_dirs' : [lib_dir]}
            opt_found_libs = self._lib_list(lib_dir, opt_libs, exts)
            if len(opt_found_libs) == len(opt_libs):
                opt_found_libs = self._extract_lib_names(opt_found_libs)
                info['libraries'].extend(opt_found_libs)
            return info
        else:
            print '  looking libraries %s in %s but found %s' % \
                  (','.join(libs), lib_dir, ','.join(found_libs) or None)

    def combine_paths(self,*args):
        return combine_paths(*args,**{'verbosity':self.verbosity})


class fft_opt_info(system_info):

    def calc_info(self):
        info = {}
        fftw_info = get_info('fftw3') or get_info('fftw2') or get_info('dfftw')
        djbfft_info = get_info('djbfft')
        if fftw_info:
            dict_append(info,**fftw_info)
            if djbfft_info:
                dict_append(info,**djbfft_info)
            self.set_info(**info)
            return


class fftw_info(system_info):
    #variables to override
    section = 'fftw'
    dir_env_var = 'FFTW'
    notfounderror = FFTWNotFoundError
    ver_info  = [ { 'name':'fftw3',
                    'libs':['fftw3'],
                    'includes':['fftw3.h'],
                    'macros':[('SCIPY_FFTW3_H',None)]},
                  { 'name':'fftw2',
                    'libs':['rfftw', 'fftw'],
                    'includes':['fftw.h','rfftw.h'],
                    'macros':[('SCIPY_FFTW_H',None)]}]

    def __init__(self):
        system_info.__init__(self)

    def calc_ver_info(self,ver_param):
        """Returns True on successful version detection, else False"""
        lib_dirs = self.get_lib_dirs()
        incl_dirs = self.get_include_dirs()
        incl_dir = None
        libs = self.get_libs(self.section+'_libs', ver_param['libs'])
        info = None
        for d in lib_dirs:
            r = self.check_libs(d,libs)
            if r is not None:
                info = r
                break
        if info is not None:
            flag = 0
            for d in incl_dirs:
                if len(self.combine_paths(d,ver_param['includes']))==len(ver_param['includes']):
                    dict_append(info,include_dirs=[d])
                    flag = 1
                    incl_dirs = [d]
                    incl_dir = d
                    break
            if flag:
                dict_append(info,define_macros=ver_param['macros'])
            else:
                info = None
        if info is not None:
            self.set_info(**info)
            return True
        else:
            if self.verbosity>0:
                print '  %s not found' % (ver_param['name'])
            return False

    def calc_info(self):
        for i in self.ver_info:
            if self.calc_ver_info(i):
                break

class fftw2_info(fftw_info):
    #variables to override
    section = 'fftw'
    dir_env_var = 'FFTW'
    notfounderror = FFTWNotFoundError
    ver_info  = [ { 'name':'fftw2',
                    'libs':['rfftw', 'fftw'],
                    'includes':['fftw.h','rfftw.h'],
                    'macros':[('SCIPY_FFTW_H',None)]}
                  ]

class fftw3_info(fftw_info):
    #variables to override
    section = 'fftw3'
    dir_env_var = 'FFTW3'
    notfounderror = FFTWNotFoundError
    ver_info  = [ { 'name':'fftw3',
                    'libs':['fftw3'],
                    'includes':['fftw3.h'],
                    'macros':[('SCIPY_FFTW3_H',None)]},
                  ]

class dfftw_info(fftw_info):
    section = 'fftw'
    dir_env_var = 'FFTW'
    ver_info  = [ { 'name':'dfftw',
                    'libs':['drfftw','dfftw'],
                    'includes':['dfftw.h','drfftw.h'],
                    'macros':[('SCIPY_DFFTW_H',None)]} ]

class sfftw_info(fftw_info):
    section = 'fftw'
    dir_env_var = 'FFTW'
    ver_info  = [ { 'name':'sfftw',
                    'libs':['srfftw','sfftw'],
                    'includes':['sfftw.h','srfftw.h'],
                    'macros':[('SCIPY_SFFTW_H',None)]} ]

class fftw_threads_info(fftw_info):
    section = 'fftw'
    dir_env_var = 'FFTW'
    ver_info  = [ { 'name':'fftw threads',
                    'libs':['rfftw_threads','fftw_threads'],
                    'includes':['fftw_threads.h','rfftw_threads.h'],
                    'macros':[('SCIPY_FFTW_THREADS_H',None)]} ]

class dfftw_threads_info(fftw_info):
    section = 'fftw'
    dir_env_var = 'FFTW'
    ver_info  = [ { 'name':'dfftw threads',
                    'libs':['drfftw_threads','dfftw_threads'],
                    'includes':['dfftw_threads.h','drfftw_threads.h'],
                    'macros':[('SCIPY_DFFTW_THREADS_H',None)]} ]

class sfftw_threads_info(fftw_info):
    section = 'fftw'
    dir_env_var = 'FFTW'
    ver_info  = [ { 'name':'sfftw threads',
                    'libs':['srfftw_threads','sfftw_threads'],
                    'includes':['sfftw_threads.h','srfftw_threads.h'],
                    'macros':[('SCIPY_SFFTW_THREADS_H',None)]} ]

class djbfft_info(system_info):
    section = 'djbfft'
    dir_env_var = 'DJBFFT'
    notfounderror = DJBFFTNotFoundError

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend(self.combine_paths(d,['djbfft'])+[d])
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()
        incl_dirs = self.get_include_dirs()
        info = None
        for d in lib_dirs:
            p = self.combine_paths (d,['djbfft.a'])
            if p:
                info = {'extra_objects':p}
                break
            p = self.combine_paths (d,['libdjbfft.a','libdjbfft'+so_ext])
            if p:
                info = {'libraries':['djbfft'],'library_dirs':[d]}
                break
        if info is None:
            return
        for d in incl_dirs:
            if len(self.combine_paths(d,['fftc8.h','fftfreq.h']))==2:
                dict_append(info,include_dirs=[d],
                            define_macros=[('SCIPY_DJBFFT_H',None)])
                self.set_info(**info)
                return
        return

class mkl_info(system_info):
    section = 'mkl'
    dir_env_var = 'MKL'
    _lib_mkl = ['mkl','vml','guide']

    def get_mkl_rootdir(self):
        mklroot = os.environ.get('MKLROOT',None)
        if mklroot is not None:
            return mklroot
        paths = os.environ.get('LD_LIBRARY_PATH','').split(os.pathsep)
        ld_so_conf = '/etc/ld.so.conf'
        if os.path.isfile(ld_so_conf):
            for d in open(ld_so_conf,'r').readlines():
                d = d.strip()
                if d: paths.append(d)
        intel_mkl_dirs = []
        for path in paths:
            path_atoms = path.split(os.sep)
            for m in path_atoms:
                if m.startswith('mkl'):
                    d = os.sep.join(path_atoms[:path_atoms.index(m)+2])
                    intel_mkl_dirs.append(d)
                    break
        for d in paths:
            dirs = glob(os.path.join(d,'mkl','*')) + glob(os.path.join(d,'mkl*'))
            for d in dirs:
                if os.path.isdir(os.path.join(d,'lib')):
                    return d
        return None

    def __init__(self):
        mklroot = self.get_mkl_rootdir()
        if mklroot is None:
            system_info.__init__(self)
        else:
            from cpuinfo import cpu
            l = 'mkl' # use shared library
            if cpu.is_Itanium():
                plt = '64'
                #l = 'mkl_ipf'
            elif cpu.is_Xeon():
                plt = 'em64t'
                #l = 'mkl_em64t'
            else:
                plt = '32'
                #l = 'mkl_ia32'
            if l not in self._lib_mkl:
                self._lib_mkl.insert(0,l)
            system_info.__init__(self,
                                 default_lib_dirs=[os.path.join(mklroot,'lib',plt)],
                                 default_include_dirs=[os.path.join(mklroot,'include')])

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()
        incl_dirs = self.get_include_dirs()
        mkl_libs = self.get_libs('mkl_libs',self._lib_mkl)
        mkl = None
        for d in lib_dirs:
            mkl = self.check_libs2(d,mkl_libs)
            if mkl is not None:
                break
        if mkl is None:
            return
        info = {}
        dict_append(info,**mkl)
        dict_append(info,libraries = ['pthread'], include_dirs = incl_dirs)
        self.set_info(**info)

class lapack_mkl_info(mkl_info):

    def calc_info(self):
        mkl = get_info('mkl')
        if not mkl:
            return
        lapack_libs = self.get_libs('lapack_libs',['mkl_lapack32','mkl_lapack64'])
        info = {'libraries': lapack_libs}
        dict_append(info,**mkl)
        self.set_info(**info)

class blas_mkl_info(mkl_info):
    pass

class atlas_info(system_info):
    section = 'atlas'
    dir_env_var = 'ATLAS'
    _lib_names = ['f77blas','cblas']
    if sys.platform[:7]=='freebsd':
        _lib_atlas = ['atlas_r']
        _lib_lapack = ['alapack_r']
    else:
        _lib_atlas = ['atlas']
        _lib_lapack = ['lapack']

    notfounderror = AtlasNotFoundError

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend(self.combine_paths(d,['atlas*','ATLAS*',
                                         'sse','3dnow','sse2'])+[d])
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()
        info = {}
        atlas_libs = self.get_libs('atlas_libs',
                                   self._lib_names + self._lib_atlas)
        lapack_libs = self.get_libs('lapack_libs',self._lib_lapack)
        atlas = None
        lapack = None
        atlas_1 = None
        for d in lib_dirs:
            atlas = self.check_libs(d,atlas_libs,[])
            lapack_atlas = self.check_libs(d,['lapack_atlas'],[])
            if atlas is not None:
                lib_dirs2 = self.combine_paths(d,['atlas*','ATLAS*'])+[d]
                for d2 in lib_dirs2:
                    lapack = self.check_libs(d2,lapack_libs,[])
                    if lapack is not None:
                        break
                else:
                    lapack = None
                if lapack is not None:
                    break
            if atlas:
                atlas_1 = atlas
        print self.__class__
        if atlas is None:
            atlas = atlas_1
        if atlas is None:
            return
        include_dirs = self.get_include_dirs()
        h = (self.combine_paths(lib_dirs+include_dirs,'cblas.h') or [None])[0]
        if h:
            h = os.path.dirname(h)
            dict_append(info,include_dirs=[h])
        info['language'] = 'c'
        if lapack is not None:
            dict_append(info,**lapack)
            dict_append(info,**atlas)
        elif 'lapack_atlas' in atlas['libraries']:
            dict_append(info,**atlas)
            dict_append(info,define_macros=[('ATLAS_WITH_LAPACK_ATLAS',None)])
            self.set_info(**info)
            return
        else:
            dict_append(info,**atlas)
            dict_append(info,define_macros=[('ATLAS_WITHOUT_LAPACK',None)])
            message = """
*********************************************************************
    Could not find lapack library within the ATLAS installation.
*********************************************************************
"""
            warnings.warn(message)
            self.set_info(**info)
            return

        # Check if lapack library is complete, only warn if it is not.
        lapack_dir = lapack['library_dirs'][0]
        lapack_name = lapack['libraries'][0]
        lapack_lib = None
        for e in ['.a',so_ext]:
            fn = os.path.join(lapack_dir,'lib'+lapack_name+e)
            if os.path.exists(fn):
                lapack_lib = fn
                break
        if lapack_lib is not None:
            sz = os.stat(lapack_lib)[6]
            if sz <= 4000*1024:
                message = """
*********************************************************************
    Lapack library (from ATLAS) is probably incomplete:
      size of %s is %sk (expected >4000k)

    Follow the instructions in the KNOWN PROBLEMS section of the file
    numpy/INSTALL.txt.
*********************************************************************
""" % (lapack_lib,sz/1024)
                warnings.warn(message)
            else:
                info['language'] = 'f77'

        self.set_info(**info)

class atlas_blas_info(atlas_info):
    _lib_names = ['f77blas','cblas']

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()
        info = {}
        atlas_libs = self.get_libs('atlas_libs',
                                   self._lib_names + self._lib_atlas)
        atlas = None
        for d in lib_dirs:
            atlas = self.check_libs(d,atlas_libs,[])
            if atlas is not None:
                break
        if atlas is None:
            return
        include_dirs = self.get_include_dirs()
        h = (self.combine_paths(lib_dirs+include_dirs,'cblas.h') or [None])[0]
        if h:
            h = os.path.dirname(h)
            dict_append(info,include_dirs=[h])
        info['language'] = 'c'

        dict_append(info,**atlas)

        self.set_info(**info)
        return


class atlas_threads_info(atlas_info):
    dir_env_var = ['PTATLAS','ATLAS']
    _lib_names = ['ptf77blas','ptcblas']

class atlas_blas_threads_info(atlas_blas_info):
    dir_env_var = ['PTATLAS','ATLAS']
    _lib_names = ['ptf77blas','ptcblas']

class lapack_atlas_info(atlas_info):
    _lib_names = ['lapack_atlas'] + atlas_info._lib_names

class lapack_atlas_threads_info(atlas_threads_info):
    _lib_names = ['lapack_atlas'] + atlas_threads_info._lib_names

class lapack_info(system_info):
    section = 'lapack'
    dir_env_var = 'LAPACK'
    _lib_names = ['lapack']
    notfounderror = LapackNotFoundError

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()

        lapack_libs = self.get_libs('lapack_libs', self._lib_names)
        for d in lib_dirs:
            lapack = self.check_libs(d,lapack_libs,[])
            if lapack is not None:
                info = lapack
                break
        else:
            return
        info['language'] = 'f77'
        self.set_info(**info)

class lapack_src_info(system_info):
    section = 'lapack_src'
    dir_env_var = 'LAPACK_SRC'
    notfounderror = LapackSrcNotFoundError

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend([d] + self.combine_paths(d,['LAPACK*/SRC','SRC']))
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        src_dirs = self.get_src_dirs()
        src_dir = ''
        for d in src_dirs:
            if os.path.isfile(os.path.join(d,'dgesv.f')):
                src_dir = d
                break
        if not src_dir:
            #XXX: Get sources from netlib. May be ask first.
            return
        # The following is extracted from LAPACK-3.0/SRC/Makefile
        allaux='''
        ilaenv ieeeck lsame lsamen xerbla
        ''' # *.f
        laux = '''
        bdsdc bdsqr disna labad lacpy ladiv lae2 laebz laed0 laed1
        laed2 laed3 laed4 laed5 laed6 laed7 laed8 laed9 laeda laev2
        lagtf lagts lamch lamrg lanst lapy2 lapy3 larnv larrb larre
        larrf lartg laruv las2 lascl lasd0 lasd1 lasd2 lasd3 lasd4
        lasd5 lasd6 lasd7 lasd8 lasd9 lasda lasdq lasdt laset lasq1
        lasq2 lasq3 lasq4 lasq5 lasq6 lasr lasrt lassq lasv2 pttrf
        stebz stedc steqr sterf
        ''' # [s|d]*.f
        lasrc = '''
        gbbrd gbcon gbequ gbrfs gbsv gbsvx gbtf2 gbtrf gbtrs gebak
        gebal gebd2 gebrd gecon geequ gees geesx geev geevx gegs gegv
        gehd2 gehrd gelq2 gelqf gels gelsd gelss gelsx gelsy geql2
        geqlf geqp3 geqpf geqr2 geqrf gerfs gerq2 gerqf gesc2 gesdd
        gesv gesvd gesvx getc2 getf2 getrf getri getrs ggbak ggbal
        gges ggesx ggev ggevx ggglm gghrd gglse ggqrf ggrqf ggsvd
        ggsvp gtcon gtrfs gtsv gtsvx gttrf gttrs gtts2 hgeqz hsein
        hseqr labrd lacon laein lags2 lagtm lahqr lahrd laic1 lals0
        lalsa lalsd langb lange langt lanhs lansb lansp lansy lantb
        lantp lantr lapll lapmt laqgb laqge laqp2 laqps laqsb laqsp
        laqsy lar1v lar2v larf larfb larfg larft larfx largv larrv
        lartv larz larzb larzt laswp lasyf latbs latdf latps latrd
        latrs latrz latzm lauu2 lauum pbcon pbequ pbrfs pbstf pbsv
        pbsvx pbtf2 pbtrf pbtrs pocon poequ porfs posv posvx potf2
        potrf potri potrs ppcon ppequ pprfs ppsv ppsvx pptrf pptri
        pptrs ptcon pteqr ptrfs ptsv ptsvx pttrs ptts2 spcon sprfs
        spsv spsvx sptrf sptri sptrs stegr stein sycon syrfs sysv
        sysvx sytf2 sytrf sytri sytrs tbcon tbrfs tbtrs tgevc tgex2
        tgexc tgsen tgsja tgsna tgsy2 tgsyl tpcon tprfs tptri tptrs
        trcon trevc trexc trrfs trsen trsna trsyl trti2 trtri trtrs
        tzrqf tzrzf
        ''' # [s|c|d|z]*.f
        sd_lasrc = '''
        laexc lag2 lagv2 laln2 lanv2 laqtr lasy2 opgtr opmtr org2l
        org2r orgbr orghr orgl2 orglq orgql orgqr orgr2 orgrq orgtr
        orm2l orm2r ormbr ormhr orml2 ormlq ormql ormqr ormr2 ormr3
        ormrq ormrz ormtr rscl sbev sbevd sbevx sbgst sbgv sbgvd sbgvx
        sbtrd spev spevd spevx spgst spgv spgvd spgvx sptrd stev stevd
        stevr stevx syev syevd syevr syevx sygs2 sygst sygv sygvd
        sygvx sytd2 sytrd
        ''' # [s|d]*.f
        cz_lasrc = '''
        bdsqr hbev hbevd hbevx hbgst hbgv hbgvd hbgvx hbtrd hecon heev
        heevd heevr heevx hegs2 hegst hegv hegvd hegvx herfs hesv
        hesvx hetd2 hetf2 hetrd hetrf hetri hetrs hpcon hpev hpevd
        hpevx hpgst hpgv hpgvd hpgvx hprfs hpsv hpsvx hptrd hptrf
        hptri hptrs lacgv lacp2 lacpy lacrm lacrt ladiv laed0 laed7
        laed8 laesy laev2 lahef lanhb lanhe lanhp lanht laqhb laqhe
        laqhp larcm larnv lartg lascl laset lasr lassq pttrf rot spmv
        spr stedc steqr symv syr ung2l ung2r ungbr unghr ungl2 unglq
        ungql ungqr ungr2 ungrq ungtr unm2l unm2r unmbr unmhr unml2
        unmlq unmql unmqr unmr2 unmr3 unmrq unmrz unmtr upgtr upmtr
        ''' # [c|z]*.f
        #######
        sclaux = laux + ' econd '                  # s*.f
        dzlaux = laux + ' secnd '                  # d*.f
        slasrc = lasrc + sd_lasrc                  # s*.f
        dlasrc = lasrc + sd_lasrc                  # d*.f
        clasrc = lasrc + cz_lasrc + ' srot srscl ' # c*.f
        zlasrc = lasrc + cz_lasrc + ' drot drscl ' # z*.f
        oclasrc = ' icmax1 scsum1 '                # *.f
        ozlasrc = ' izmax1 dzsum1 '                # *.f
        sources = ['s%s.f'%f for f in (sclaux+slasrc).split()] \
                  + ['d%s.f'%f for f in (dzlaux+dlasrc).split()] \
                  + ['c%s.f'%f for f in (clasrc).split()] \
                  + ['z%s.f'%f for f in (zlasrc).split()] \
                  + ['%s.f'%f for f in (allaux+oclasrc+ozlasrc).split()]
        sources = [os.path.join(src_dir,f) for f in sources]
        #XXX: should we check here actual existence of source files?
        info = {'sources':sources,'language':'f77'}
        self.set_info(**info)

atlas_version_c_text = r'''
/* This file is generated from numpy_distutils/system_info.py */
#ifdef __CPLUSPLUS__
extern "C" {
#endif
#include "Python.h"
static PyMethodDef module_methods[] = { {NULL,NULL} };
PyMODINIT_FUNC initatlas_version(void) {
  void ATL_buildinfo(void);
  ATL_buildinfo();
  Py_InitModule("atlas_version", module_methods);
}
#ifdef __CPLUSCPLUS__
}
#endif
'''

def _get_build_temp():
    from distutils.util import get_platform
    plat_specifier = ".%s-%s" % (get_platform(), sys.version[0:3])
    return os.path.join('build','temp'+plat_specifier)

def get_atlas_version(**config):
    os.environ['NO_SCIPY_IMPORT']='get_atlas_version'
    from core import Extension, setup
    from misc_util import get_cmd
    import log
    magic = hex(hash(repr(config)))
    def atlas_version_c(extension, build_dir,magic=magic):
        source = os.path.join(build_dir,'atlas_version_%s.c' % (magic))
        if os.path.isfile(source):
            from distutils.dep_util import newer
            if newer(source,__file__):
                return source
        f = open(source,'w')
        f.write(atlas_version_c_text)
        f.close()
        return source
    ext = Extension('atlas_version',
                    sources=[atlas_version_c],
                    **config)
    build_dir = _get_build_temp()
    extra_args = ['--build-lib',build_dir]
    for a in sys.argv:
        if re.match('[-][-]compiler[=]',a):
            extra_args.append(a)
    import distutils.core
    old_dist = distutils.core._setup_distribution
    distutils.core._setup_distribution = None
    return_flag = True
    try:
        dist = setup(ext_modules=[ext],
                     script_name = 'get_atlas_version',
                     script_args = ['build_src','build_ext']+extra_args)
        return_flag = False
    except Exception,msg:
        print "##### msg: %s" % msg
        if not msg:
            msg = "Unknown Exception"
        log.warn(msg)
    distutils.core._setup_distribution = old_dist

    if return_flag:
        return

    from distutils.sysconfig import get_config_var
    so_ext = get_config_var('SO')
    target = os.path.join(build_dir,'atlas_version'+so_ext)
    cmd = [get_pythonexe(),'-c',
           '"import imp,os;os.environ[\\"NO_SCIPY_IMPORT\\"]='\
           '\\"system_info.get_atlas_version:load atlas_version\\";'\
           'imp.load_dynamic(\\"atlas_version\\",\\"%s\\")"'\
           % (os.path.basename(target))]
    s,o = exec_command(cmd,execute_in=os.path.dirname(target),use_tee=0)
    atlas_version = None
    if not s:
        m = re.search(r'ATLAS version (?P<version>\d+[.]\d+[.]\d+)',o)
        if m:
            atlas_version = m.group('version')
    if atlas_version is None:
        if re.search(r'undefined symbol: ATL_buildinfo',o,re.M):
            atlas_version = '3.2.1_pre3.3.6'
        else:
            print 'Command:',' '.join(cmd)
            print 'Status:',s
            print 'Output:',o
    return atlas_version


class lapack_opt_info(system_info):

    def calc_info(self):

        if sys.platform=='darwin' and not os.environ.get('ATLAS',None):
            args = []
            link_args = []
            if os.path.exists('/System/Library/Frameworks/Accelerate.framework/'):
                args.extend(['-faltivec'])
                link_args.extend(['-Wl,-framework','-Wl,Accelerate'])
            elif os.path.exists('/System/Library/Frameworks/vecLib.framework/'):
                args.extend(['-faltivec'])
                link_args.extend(['-Wl,-framework','-Wl,vecLib'])
            if args:
                self.set_info(extra_compile_args=args,
                              extra_link_args=link_args,
                              define_macros=[('NO_ATLAS_INFO',3)])
                return

        lapack_mkl_info = get_info('lapack_mkl')
        if lapack_mkl_info:
            self.set_info(**lapack_mkl_info)
            return

        atlas_info = get_info('atlas_threads')
        if not atlas_info:
            atlas_info = get_info('atlas')
        #atlas_info = {} ## uncomment for testing
        atlas_version = None
        need_lapack = 0
        need_blas = 0
        info = {}
        if atlas_info:
            version_info = atlas_info.copy()
            atlas_version = get_atlas_version(**version_info)
            if not atlas_info.has_key('define_macros'):
                atlas_info['define_macros'] = []
            if atlas_version is None:
                atlas_info['define_macros'].append(('NO_ATLAS_INFO',2))
            else:
                atlas_info['define_macros'].append(('ATLAS_INFO',
                                                    '"\\"%s\\""' % atlas_version))
            if atlas_version=='3.2.1_pre3.3.6':
                atlas_info['define_macros'].append(('NO_ATLAS_INFO',4))
            l = atlas_info.get('define_macros',[])
            if ('ATLAS_WITH_LAPACK_ATLAS',None) in l \
                   or ('ATLAS_WITHOUT_LAPACK',None) in l:
                need_lapack = 1
            info = atlas_info
        else:
            warnings.warn(AtlasNotFoundError.__doc__)
            need_blas = 1
            need_lapack = 1
            dict_append(info,define_macros=[('NO_ATLAS_INFO',1)])

        if need_lapack:
            lapack_info = get_info('lapack')
            #lapack_info = {} ## uncomment for testing
            if lapack_info:
                dict_append(info,**lapack_info)
            else:
                warnings.warn(LapackNotFoundError.__doc__)
                lapack_src_info = get_info('lapack_src')
                if not lapack_src_info:
                    warnings.warn(LapackSrcNotFoundError.__doc__)
                    return
                dict_append(info,libraries=[('flapack_src',lapack_src_info)])

        if need_blas:
            blas_info = get_info('blas')
            #blas_info = {} ## uncomment for testing
            if blas_info:
                dict_append(info,**blas_info)
            else:
                warnings.warn(BlasNotFoundError.__doc__)
                blas_src_info = get_info('blas_src')
                if not blas_src_info:
                    warnings.warn(BlasSrcNotFoundError.__doc__)
                    return
                dict_append(info,libraries=[('fblas_src',blas_src_info)])

        self.set_info(**info)
        return


class blas_opt_info(system_info):

    def calc_info(self):

        if sys.platform=='darwin' and not os.environ.get('ATLAS',None):
            args = []
            link_args = []
            if os.path.exists('/System/Library/Frameworks/Accelerate.framework/'):
                args.extend(['-faltivec',
                    '-I/System/Library/Frameworks/vecLib.framework/Headers',
                    ])
                link_args.extend(['-Wl,-framework','-Wl,Accelerate'])
            elif os.path.exists('/System/Library/Frameworks/vecLib.framework/'):
                args.extend(['-faltivec',
                    '-I/System/Library/Frameworks/vecLib.framework/Headers',
                    ])
                link_args.extend(['-Wl,-framework','-Wl,vecLib'])
            if args:
                self.set_info(extra_compile_args=args,
                              extra_link_args=link_args,
                              define_macros=[('NO_ATLAS_INFO',3)])
                return

        blas_mkl_info = get_info('blas_mkl')
        if blas_mkl_info:
            self.set_info(**blas_mkl_info)
            return

        atlas_info = get_info('atlas_blas_threads')
        if not atlas_info:
            atlas_info = get_info('atlas_blas')
        atlas_version = None
        need_blas = 0
        info = {}
        if atlas_info:
            version_info = atlas_info.copy()
            atlas_version = get_atlas_version(**version_info)
            if not atlas_info.has_key('define_macros'):
                atlas_info['define_macros'] = []
            if atlas_version is None:
                atlas_info['define_macros'].append(('NO_ATLAS_INFO',2))
            else:
                atlas_info['define_macros'].append(('ATLAS_INFO',
                                                    '"\\"%s\\""' % atlas_version))
            info = atlas_info
        else:
            warnings.warn(AtlasNotFoundError.__doc__)
            need_blas = 1
            dict_append(info,define_macros=[('NO_ATLAS_INFO',1)])

        if need_blas:
            blas_info = get_info('blas')
            if blas_info:
                dict_append(info,**blas_info)
            else:
                warnings.warn(BlasNotFoundError.__doc__)
                blas_src_info = get_info('blas_src')
                if not blas_src_info:
                    warnings.warn(BlasSrcNotFoundError.__doc__)
                    return
                dict_append(info,libraries=[('fblas_src',blas_src_info)])

        self.set_info(**info)
        return


class blas_info(system_info):
    section = 'blas'
    dir_env_var = 'BLAS'
    _lib_names = ['blas']
    notfounderror = BlasNotFoundError

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()

        blas_libs = self.get_libs('blas_libs', self._lib_names)
        for d in lib_dirs:
            blas = self.check_libs(d,blas_libs,[])
            if blas is not None:
                info = blas
                break
        else:
            return
        info['language'] = 'f77'  # XXX: is it generally true?
        self.set_info(**info)


class blas_src_info(system_info):
    section = 'blas_src'
    dir_env_var = 'BLAS_SRC'
    notfounderror = BlasSrcNotFoundError

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend([d] + self.combine_paths(d,['blas']))
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        src_dirs = self.get_src_dirs()
        src_dir = ''
        for d in src_dirs:
            if os.path.isfile(os.path.join(d,'daxpy.f')):
                src_dir = d
                break
        if not src_dir:
            #XXX: Get sources from netlib. May be ask first.
            return
        blas1 = '''
        caxpy csscal dnrm2 dzasum saxpy srotg zdotc ccopy cswap drot
        dznrm2 scasum srotm zdotu cdotc dasum drotg icamax scnrm2
        srotmg zdrot cdotu daxpy drotm idamax scopy sscal zdscal crotg
        dcabs1 drotmg isamax sdot sswap zrotg cscal dcopy dscal izamax
        snrm2 zaxpy zscal csrot ddot dswap sasum srot zcopy zswap
        '''
        blas2 = '''
        cgbmv chpmv ctrsv dsymv dtrsv sspr2 strmv zhemv ztpmv cgemv
        chpr dgbmv dsyr lsame ssymv strsv zher ztpsv cgerc chpr2 dgemv
        dsyr2 sgbmv ssyr xerbla zher2 ztrmv cgeru ctbmv dger dtbmv
        sgemv ssyr2 zgbmv zhpmv ztrsv chbmv ctbsv dsbmv dtbsv sger
        stbmv zgemv zhpr chemv ctpmv dspmv dtpmv ssbmv stbsv zgerc
        zhpr2 cher ctpsv dspr dtpsv sspmv stpmv zgeru ztbmv cher2
        ctrmv dspr2 dtrmv sspr stpsv zhbmv ztbsv
        '''
        blas3 = '''
        cgemm csymm ctrsm dsyrk sgemm strmm zhemm zsyr2k chemm csyr2k
        dgemm dtrmm ssymm strsm zher2k zsyrk cher2k csyrk dsymm dtrsm
        ssyr2k zherk ztrmm cherk ctrmm dsyr2k ssyrk zgemm zsymm ztrsm
        '''
        sources = [os.path.join(src_dir,f+'.f') \
                   for f in (blas1+blas2+blas3).split()]
        #XXX: should we check here actual existence of source files?
        info = {'sources':sources,'language':'f77'}
        self.set_info(**info)

class x11_info(system_info):
    section = 'x11'
    notfounderror = X11NotFoundError

    def __init__(self):
        system_info.__init__(self,
                             default_lib_dirs=default_x11_lib_dirs,
                             default_include_dirs=default_x11_include_dirs)

    def calc_info(self):
        if sys.platform  in ['win32']:
            return
        lib_dirs = self.get_lib_dirs()
        include_dirs = self.get_include_dirs()
        x11_libs = self.get_libs('x11_libs', ['X11'])
        for lib_dir in lib_dirs:
            info = self.check_libs(lib_dir, x11_libs, [])
            if info is not None:
                break
        else:
            return
        inc_dir = None
        for d in include_dirs:
            if self.combine_paths(d, 'X11/X.h'):
                inc_dir = d
                break
        if inc_dir is not None:
            dict_append(info, include_dirs=[inc_dir])
        self.set_info(**info)

class _numpy_info(system_info):
    section = 'Numeric'
    modulename = 'Numeric'
    notfounderror = NumericNotFoundError

    def __init__(self):
        from distutils.sysconfig import get_python_inc
        include_dirs = []
        try:
            module = __import__(self.modulename)
            prefix = []
            for name in module.__file__.split(os.sep):
                if name=='lib':
                    break
                prefix.append(name)
            include_dirs.append(get_python_inc(prefix=os.sep.join(prefix)))
        except ImportError:
            pass
        py_incl_dir = get_python_inc()
        include_dirs.append(py_incl_dir)
        for d in default_include_dirs:
            d = os.path.join(d, os.path.basename(py_incl_dir))
            if d not in include_dirs:
                include_dirs.append(d)
        system_info.__init__(self,
                             default_lib_dirs=[],
                             default_include_dirs=include_dirs)

    def calc_info(self):
        try:
            module = __import__(self.modulename)
        except ImportError:
            return
        info = {}
        macros = []
        for v in ['__version__','version']:
            vrs = getattr(module,v,None)
            if vrs is None:
                continue
            macros = [(self.modulename.upper()+'_VERSION',
                      '"\\"%s\\""' % (vrs)),
                      (self.modulename.upper(),None)]
            break
##         try:
##             macros.append(
##                 (self.modulename.upper()+'_VERSION_HEX',
##                  hex(vstr2hex(module.__version__))),
##                 )
##         except Exception,msg:
##             print msg
        dict_append(info, define_macros = macros)
        include_dirs = self.get_include_dirs()
        inc_dir = None
        for d in include_dirs:
            if self.combine_paths(d,
                                  os.path.join(self.modulename,
                                               'arrayobject.h')):
                inc_dir = d
                break
        if inc_dir is not None:
            dict_append(info, include_dirs=[inc_dir])
        if info:
            self.set_info(**info)
        return

class numarray_info(_numpy_info):
    section = 'numarray'
    modulename = 'numarray'

class Numeric_info(_numpy_info):
    section = 'Numeric'
    modulename = 'Numeric'

class numpy_info(_numpy_info):
    section = 'numpy'
    modulename = 'numpy'

class numerix_info(system_info):
    section = 'numerix'
    def calc_info(self):
        import sys, os
        which = None, None
        if os.getenv("NUMERIX"):
            which = os.getenv("NUMERIX"), "environment var"
        # If all the above fail, default to numpy.
        if which[0] is None:
            which = "numpy", "defaulted"
            try:
                import numpy
                which = "numpy", "defaulted"
            except ImportError,msg1:
                try:
                    import Numeric
                    which = "numeric", "defaulted"
                except ImportError,msg2:
                    try:
                        import numarray
                        which = "numarray", "defaulted"
                    except ImportError,msg3:
                        print msg1
                        print msg2
                        print msg3
        which = which[0].strip().lower(), which[1]
        if which[0] not in ["numeric", "numarray", "numpy"]:
            raise ValueError("numerix selector must be either 'Numeric' "
                             "or 'numarray' or 'numpy' but the value obtained"
                             " from the %s was '%s'." % (which[1], which[0]))
        self.set_info(**get_info(which[0]))

class f2py_info(system_info):
    def calc_info(self):
        try:
            import numpy.f2py as f2py
        except ImportError:
            return
        f2py_dir = os.path.join(os.path.dirname(f2py.__file__),'src')
        self.set_info(sources = [os.path.join(f2py_dir,'fortranobject.c')],
                      include_dirs = [f2py_dir])
        return

class boost_python_info(system_info):
    section = 'boost_python'
    dir_env_var = 'BOOST'

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend([d] + self.combine_paths(d,['boost*']))
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        from distutils.sysconfig import get_python_inc
        src_dirs = self.get_src_dirs()
        src_dir = ''
        for d in src_dirs:
            if os.path.isfile(os.path.join(d,'libs','python','src','module.cpp')):
                src_dir = d
                break
        if not src_dir:
            return
        py_incl_dir = get_python_inc()
        srcs_dir = os.path.join(src_dir,'libs','python','src')
        bpl_srcs = glob(os.path.join(srcs_dir,'*.cpp'))
        bpl_srcs += glob(os.path.join(srcs_dir,'*','*.cpp'))
        info = {'libraries':[('boost_python_src',{'include_dirs':[src_dir,py_incl_dir],
                                                  'sources':bpl_srcs})],
                'include_dirs':[src_dir],
                }
        if info:
            self.set_info(**info)
        return

class agg2_info(system_info):
    section = 'agg2'
    dir_env_var = 'AGG2'

    def get_paths(self, section, key):
        pre_dirs = system_info.get_paths(self, section, key)
        dirs = []
        for d in pre_dirs:
            dirs.extend([d] + self.combine_paths(d,['agg2*']))
        return [ d for d in dirs if os.path.isdir(d) ]

    def calc_info(self):
        src_dirs = self.get_src_dirs()
        src_dir = ''
        for d in src_dirs:
            if os.path.isfile(os.path.join(d,'src','agg_affine_matrix.cpp')):
                src_dir = d
                break
        if not src_dir:
            return
        if sys.platform=='win32':
            agg2_srcs = glob(os.path.join(src_dir,'src','platform','win32','agg_win32_bmp.cpp'))
        else:
            agg2_srcs = glob(os.path.join(src_dir,'src','*.cpp'))
            agg2_srcs += [os.path.join(src_dir,'src','platform','X11','agg_platform_support.cpp')]

        info = {'libraries':[('agg2_src',{'sources':agg2_srcs,
                                          'include_dirs':[os.path.join(src_dir,'include')],
                                          })],
                'include_dirs':[os.path.join(src_dir,'include')],
                }
        if info:
            self.set_info(**info)
        return

class _pkg_config_info(system_info):
    section = None
    config_env_var = 'PKG_CONFIG'
    default_config_exe = 'pkg-config'
    append_config_exe = ''
    version_macro_name = None
    release_macro_name = None
    version_flag = '--modversion'
    cflags_flag = '--cflags'

    def get_config_exe(self):
        if os.environ.has_key(self.config_env_var):
            return os.environ[self.config_env_var]
        return self.default_config_exe
    def get_config_output(self, config_exe, option):
        s,o = exec_command(config_exe+' '+self.append_config_exe+' '+option,use_tee=0)
        if not s:
            return o

    def calc_info(self):
        config_exe = find_executable(self.get_config_exe())
        if not os.path.isfile(config_exe):
            print 'File not found: %s. Cannot determine %s info.' \
                  % (config_exe, self.section)
            return
        info = {}
        macros = []
        libraries = []
        library_dirs = []
        include_dirs = []
        extra_link_args = []
        extra_compile_args = []
        version = self.get_config_output(config_exe,self.version_flag)
        if version:
            macros.append((self.__class__.__name__.split('.')[-1].upper(),
                           '"\\"%s\\""' % (version)))
            if self.version_macro_name:
                macros.append((self.version_macro_name+'_%s' % (version.replace('.','_')),None))
        if self.release_macro_name:
            release = self.get_config_output(config_exe,'--release')
            if release:
                macros.append((self.release_macro_name+'_%s' % (release.replace('.','_')),None))
        opts = self.get_config_output(config_exe,'--libs')
        if opts:
            for opt in opts.split():
                if opt[:2]=='-l':
                    libraries.append(opt[2:])
                elif opt[:2]=='-L':
                    library_dirs.append(opt[2:])
                else:
                    extra_link_args.append(opt)
        opts = self.get_config_output(config_exe,self.cflags_flag)
        if opts:
            for opt in opts.split():
                if opt[:2]=='-I':
                    include_dirs.append(opt[2:])
                elif opt[:2]=='-D':
                    if '=' in opt:
                        n,v = opt[2:].split('=')
                        macros.append((n,v))
                    else:
                        macros.append((opt[2:],None))
                else:
                    extra_compile_args.append(opt)
        if macros: dict_append(info, define_macros = macros)
        if libraries: dict_append(info, libraries = libraries)
        if library_dirs: dict_append(info, library_dirs = library_dirs)
        if include_dirs: dict_append(info, include_dirs = include_dirs)
        if extra_link_args: dict_append(info, extra_link_args = extra_link_args)
        if extra_compile_args: dict_append(info, extra_compile_args = extra_compile_args)
        if info:
            self.set_info(**info)
        return

class wx_info(_pkg_config_info):
    section = 'wx'
    config_env_var = 'WX_CONFIG'
    default_config_exe = 'wx-config'
    append_config_exe = ''
    version_macro_name = 'WX_VERSION'
    release_macro_name = 'WX_RELEASE'
    version_flag = '--version'
    cflags_flag = '--cxxflags'

class gdk_pixbuf_xlib_2_info(_pkg_config_info):
    section = 'gdk_pixbuf_xlib_2'
    append_config_exe = 'gdk-pixbuf-xlib-2.0'
    version_macro_name = 'GDK_PIXBUF_XLIB_VERSION'

class gdk_pixbuf_2_info(_pkg_config_info):
    section = 'gdk_pixbuf_2'
    append_config_exe = 'gdk-pixbuf-2.0'
    version_macro_name = 'GDK_PIXBUF_VERSION'

class gdk_x11_2_info(_pkg_config_info):
    section = 'gdk_x11_2'
    append_config_exe = 'gdk-x11-2.0'
    version_macro_name = 'GDK_X11_VERSION'

class gdk_2_info(_pkg_config_info):
    section = 'gdk_2'
    append_config_exe = 'gdk-2.0'
    version_macro_name = 'GDK_VERSION'

class gdk_info(_pkg_config_info):
    section = 'gdk'
    append_config_exe = 'gdk'
    version_macro_name = 'GDK_VERSION'

class gtkp_x11_2_info(_pkg_config_info):
    section = 'gtkp_x11_2'
    append_config_exe = 'gtk+-x11-2.0'
    version_macro_name = 'GTK_X11_VERSION'


class gtkp_2_info(_pkg_config_info):
    section = 'gtkp_2'
    append_config_exe = 'gtk+-2.0'
    version_macro_name = 'GTK_VERSION'

class xft_info(_pkg_config_info):
    section = 'xft'
    append_config_exe = 'xft'
    version_macro_name = 'XFT_VERSION'

class freetype2_info(_pkg_config_info):
    section = 'freetype2'
    append_config_exe = 'freetype2'
    version_macro_name = 'FREETYPE2_VERSION'

class amd_info(system_info):
    section = 'amd'
    dir_env_var = 'AMD'
    _lib_names = ['amd']

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()

        amd_libs = self.get_libs('amd_libs', self._lib_names)
        for d in lib_dirs:
            amd = self.check_libs(d,amd_libs,[])
            if amd is not None:
                info = amd
                break
        else:
            return

        include_dirs = self.get_include_dirs()

        inc_dir = None
        for d in include_dirs:
            p = self.combine_paths(d,'amd.h')
            if p:
                inc_dir = os.path.dirname(p[0])
                break
        if inc_dir is not None:
            dict_append(info, include_dirs=[inc_dir],
                        define_macros=[('SCIPY_AMD_H',None)],
                        swig_opts = ['-I' + inc_dir])

        self.set_info(**info)
        return

class umfpack_info(system_info):
    section = 'umfpack'
    dir_env_var = 'UMFPACK'
    notfounderror = UmfpackNotFoundError
    _lib_names = ['umfpack']

    def calc_info(self):
        lib_dirs = self.get_lib_dirs()

        umfpack_libs = self.get_libs('umfpack_libs', self._lib_names)
        for d in lib_dirs:
            umf = self.check_libs(d,umfpack_libs,[])
            if umf is not None:
                info = umf
                break
        else:
            return

        include_dirs = self.get_include_dirs()

        inc_dir = None
        for d in include_dirs:
            p = self.combine_paths(d,['','umfpack'],'umfpack.h')
            if p:
                inc_dir = os.path.dirname(p[0])
                break
        if inc_dir is not None:
            dict_append(info, include_dirs=[inc_dir],
                        define_macros=[('SCIPY_UMFPACK_H',None)],
                        swig_opts = ['-I' + inc_dir])

        amd = get_info('amd')
        dict_append(info, **get_info('amd'))

        self.set_info(**info)
        return

## def vstr2hex(version):
##     bits = []
##     n = [24,16,8,4,0]
##     r = 0
##     for s in version.split('.'):
##         r |= int(s) << n[0]
##         del n[0]
##     return r

#--------------------------------------------------------------------

def combine_paths(*args,**kws):
    """ Return a list of existing paths composed by all combinations of
        items from arguments.
    """
    r = []
    for a in args:
        if not a: continue
        if is_string(a):
            a = [a]
        r.append(a)
    args = r
    if not args: return []
    if len(args)==1:
        result = reduce(lambda a,b:a+b,map(glob,args[0]),[])
    elif len (args)==2:
        result = []
        for a0 in args[0]:
            for a1 in args[1]:
                result.extend(glob(os.path.join(a0,a1)))
    else:
        result = combine_paths(*(combine_paths(args[0],args[1])+args[2:]))
    verbosity = kws.get('verbosity',1)
    if verbosity>1 and result:
        print '(','paths:',','.join(result),')'
    return result

language_map = {'c':0,'c++':1,'f77':2,'f90':3}
inv_language_map = {0:'c',1:'c++',2:'f77',3:'f90'}
def dict_append(d,**kws):
    languages = []
    for k,v in kws.items():
        if k=='language':
            languages.append(v)
            continue
        if d.has_key(k):
            if k in ['library_dirs','include_dirs','define_macros']:
                [d[k].append(vv) for vv in v if vv not in d[k]]
            else:
                d[k].extend(v)
        else:
            d[k] = v
    if languages:
        l = inv_language_map[max([language_map.get(l,0) for l in languages])]
        d['language'] = l
    return

def show_all():
    import system_info
    import pprint
    match_info = re.compile(r'.*?_info').match
    show_only = []
    for n in sys.argv[1:]:
        if n[-5:] != '_info':
            n = n + '_info'
        show_only.append(n)
    show_all = not show_only
    for n in filter(match_info,dir(system_info)):
        if n in ['system_info','get_info']: continue
        if not show_all:
            if n not in show_only: continue
            del show_only[show_only.index(n)]
        c = getattr(system_info,n)()
        c.verbosity = 2
        r = c.get_info()
    if show_only:
        print 'Info classes not defined:',','.join(show_only)
if __name__ == "__main__":
    show_all()
