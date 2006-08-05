# This module is for compatibility only.  All functions are defined elsewhere.

__all__ = ['rand', 'tril', 'trapz', 'hanning', 'rot90', 'triu', 'diff', 'angle', 'roots', 'ptp', 'kaiser', 'randn', 'cumprod', 'diag', 'msort', 'LinearAlgebra', 'RandomArray', 'prod', 'std', 'hamming', 'flipud', 'max', 'blackman', 'corrcoef', 'bartlett', 'eye', 'squeeze', 'sinc', 'tri', 'cov', 'svd', 'min', 'median', 'fliplr', 'eig', 'mean']

import linear_algebra as LinearAlgebra
import random_array as RandomArray
from numpy import tril, trapz as _Ntrapz, hanning, rot90, triu, diff, \
     angle, roots, ptp as _Nptp, kaiser, cumprod as _Ncumprod, \
     diag, msort, prod as _Nprod, std as _Nstd, hamming, flipud, \
     amax as _Nmax, amin as _Nmin, blackman, bartlett, corrcoef as _Ncorrcoef,\
     cov as _Ncov, squeeze, sinc, median, fliplr, mean as _Nmean

from numpy.linalg import eig, svd
from numpy.random import rand, randn
     
from typeconv import convtypecode

def eye(N, M=None, k=0, typecode=None, dtype=None):
    """ eye returns a N-by-M 2-d array where the  k-th diagonal is all ones,
        and everything else is zeros.
    """
    dtype = convtypecode(typecode, dtype)
    if M is None: M = N
    m = nn.equal(nn.subtract.outer(nn.arange(N), nn.arange(M)),-k)
    if m.dtype != dtype:
        return m.astype(dtype)
    
def tri(N, M=None, k=0, typecode=None, dtype=None):
    """ returns a N-by-M array where all the diagonals starting from
        lower left corner up to the k-th are all ones.
    """
    dtype = convtypecode(typecode, dtype)
    if M is None: M = N
    m = nn.greater_equal(nn.subtract.outer(nn.arange(N), nn.arange(M)),-k)
    if m.dtype != dtype:
        return m.astype(dtype)
    
def trapz(y, x=None, axis=-1):
    return _Ntrapz(y, x, axis=axis)

def ptp(x, axis=0):
    return _Nptp(x, axis)

def cumprod(x, axis=0):
    return _Ncumprod(x, axis)

def max(x, axis=0):
    return _Nmax(x, axis)

def min(x, axis=0):
    return _Nmin(x, axis)

def prod(x, axis=0):
    return _Nprod(x, axis)

def std(x, axis=0):
    return _Nstd(x, axis)

def mean(x, axis=0):
    return _Nmean(x, axis)

def cov(m, y=None, rowvar=0, bias=0):
    return _Ncov(m, y, rowvar, bias)

def corrcoef(x, y=None):
    return _Ncorrcoef(x,y,0,0)

from compat import *
from functions import *
from precision import *
from ufuncs import *
from misc import *

import compat
import precision
import functions
import misc
import ufuncs

import numpy
__version__ = numpy.__version__
del numpy

__all__ += ['__version__']
__all__ += compat.__all__
__all__ += precision.__all__
__all__ += functions.__all__
__all__ += ufuncs.__all__
__all__ += misc.__all__
        
del compat
del functions
del precision
del ufuncs
del misc

