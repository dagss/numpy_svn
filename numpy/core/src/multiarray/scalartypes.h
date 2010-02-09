#ifndef _NPY_SCALARTYPES_H_
#define _NPY_SCALARTYPES_H_

NPY_NO_EXPORT void
initialize_numeric_types(void);

NPY_NO_EXPORT void
format_longdouble(char *buf, size_t buflen, longdouble val, unsigned int prec);

NPY_NO_EXPORT void
gentype_struct_free(void *ptr, void *arg);

NPY_NO_EXPORT int
_typenum_fromtypeobj(PyObject *type, int user);

NPY_NO_EXPORT void *
scalar_value(PyObject *scalar, PyArray_Descr *descr);

#endif
