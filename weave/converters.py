""" converters.py
"""

import common_info
import c_spec

#----------------------------------------------------------------------------
# The "standard" conversion classes
#----------------------------------------------------------------------------

default = [c_spec.int_converter(),
           c_spec.float_converter(),
           c_spec.complex_converter(),
           c_spec.unicode_converter(),
           c_spec.string_converter(),
           c_spec.list_converter(),
           c_spec.dict_converter(),
           c_spec.tuple_converter(),
           c_spec.file_converter(),
           c_spec.callable_converter(),
           c_spec.instance_converter(),]                          
          #common_spec.module_converter()]

#----------------------------------------------------------------------------
# If Numeric is installed, add numeric array converters to the default
# converter list.
#----------------------------------------------------------------------------
try: 
    import standard_array_spec
    default.append(standard_array_spec.array_converter())
except ImportError: 
    pass    

#----------------------------------------------------------------------------
# Add wxPython support
#----------------------------------------------------------------------------

try: 
    # this is currently safe because it doesn't import wxPython.
    import wx_spec
    default.insert(0,wx_spec.wx_converter())
except IndexError: 
    pass    

standard_info = [common_info.basic_module_info()]
standard_info += [x.generate_build_info() for x in default]

#----------------------------------------------------------------------------
# Blitz conversion classes
#
# same as default, but will convert Numeric arrays to blitz C++ classes 
#----------------------------------------------------------------------------
import blitz_spec
blitz = [blitz_spec.array_converter()] + default

