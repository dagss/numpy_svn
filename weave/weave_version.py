major = 0
minor = 3
micro = 2
#release_level = 'alpha'
release_level = ''
try:
    from __cvs_version__ import cvs_version
    cvs_minor = cvs_version[-3]
    cvs_serial = cvs_version[-1]
except ImportError,msg:
    print msg
    cvs_minor = 0
    cvs_serial = 0

if release_level:
    weave_version = '%(major)d.%(minor)d.%(micro)d_%(release_level)s'\
                    '_%(cvs_minor)d.%(cvs_serial)d' % (locals ())
else:
    weave_version = '%(major)d.%(minor)d.%(micro)d'\
                    '_%(cvs_minor)d.%(cvs_serial)d' % (locals ())
