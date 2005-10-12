#ifndef Py_FORTRANOBJECT_H
#define Py_FORTRANOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "Python.h"

#ifdef FORTRANOBJECT_C
#define NO_IMPORT_ARRAY
#endif

#if defined(NUMARRAY)

#define libnumarray_UNIQUE_SYMBOL libnumarray_API
#include "numarray/libnumarray.h"

#if !defined(__arrayobject_h)  /* not defined as of 1.0 */
#define libnumeric_UNIQUE_SYMBOL libnumeric_API
#include "numarray/arrayobject.h"

/* numarray-1.0 hack */
#if defined(_libnumeric) && !defined(NUMARRAY_VERSION_HEX) && !defined(NO_IMPORT_ARRAY)
void **libnumeric_API;
void **libnumarray_API;
#endif

#endif

#else

#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
#if defined(NUMERIC)
#include "Numeric/arrayobject.h"
#else
#include "scipy/arrayobject.h"
#endif

#endif

  /*
#ifdef F2PY_REPORT_ATEXIT_DISABLE
#undef F2PY_REPORT_ATEXIT
#else

#ifndef __FreeBSD__
#ifndef __WIN32__
#ifndef __APPLE__
#define F2PY_REPORT_ATEXIT
#endif
#endif
#endif

#endif
  */

#ifdef F2PY_REPORT_ATEXIT
#include <sys/timeb.h>
  extern void f2py_start_clock(void);
  extern void f2py_stop_clock(void);
  extern void f2py_start_call_clock(void);
  extern void f2py_stop_call_clock(void);
  extern void f2py_cb_start_clock(void);
  extern void f2py_cb_stop_clock(void);
  extern void f2py_cb_start_call_clock(void);
  extern void f2py_cb_stop_call_clock(void);
  extern void f2py_report_on_exit(int,void*);
#endif

#ifdef DMALLOC
#include "dmalloc.h"
#endif

/* Fortran object interface */

/*
123456789-123456789-123456789-123456789-123456789-123456789-123456789-12

PyFortranObject represents various Fortran objects:
Fortran (module) routines, COMMON blocks, module data. 

Author: Pearu Peterson <pearu@cens.ioc.ee>
*/

#define F2PY_MAX_DIMS 40

typedef void (*f2py_set_data_func)(char*,int*);
typedef void (*f2py_void_func)(void);
typedef void (*f2py_init_func)(int*,int*,f2py_set_data_func,int*);

  /*typedef void* (*f2py_c_func)(void*,...);*/

typedef void *(*f2pycfunc)(void);

typedef struct {
  char *name;                /* attribute (array||routine) name */
  int rank;                  /* array rank, 0 for scalar, max is F2PY_MAX_DIMS,
				|| rank=-1 for Fortran routine */
  struct {int d[F2PY_MAX_DIMS];} dims;  /* dimensions of the array, || not used */
  int type;                  /* PyArray_<type> || not used */
  char *data;                /* pointer to array || Fortran routine */
  f2py_init_func func;            /* initialization function for
				allocatable arrays:
				func(&rank,dims,set_ptr_func,name,len(name))
				|| C/API wrapper for Fortran routine */
  char *doc;                 /* documentation string; only recommended
				for routines. */
} FortranDataDef;

typedef struct {
  PyObject_HEAD
  int len;                   /* Number of attributes */
  FortranDataDef *defs;      /* An array of FortranDataDef's */ 
  PyObject       *dict;      /* Fortran object attribute dictionary */
} PyFortranObject;

#define PyFortran_Check(op) ((op)->ob_type == &PyFortran_Type)
#define PyFortran_Check1(op) (0==strcmp((op)->ob_type->tp_name,"fortran"))

  extern PyTypeObject PyFortran_Type;
  extern PyObject * PyFortranObject_New(FortranDataDef* defs, f2py_void_func init);
  extern PyObject * PyFortranObject_NewAsAttr(FortranDataDef* defs);

#define ISCONTIGUOUS(m) ((m)->flags & CONTIGUOUS)
#define F2PY_INTENT_IN 1
#define F2PY_INTENT_INOUT 2
#define F2PY_INTENT_OUT 4
#define F2PY_INTENT_HIDE 8
#define F2PY_INTENT_CACHE 16
#define F2PY_INTENT_COPY 32
#define F2PY_INTENT_C 64
#define F2PY_OPTIONAL 128
#define F2PY_INTENT_INPLACE 256

  extern void lazy_transpose(PyArrayObject* arr); /* Obsolete?? */
  extern void transpose_strides(PyArrayObject* arr);
  extern PyArrayObject* array_from_pyobj(const int type_num,
					 int *dims,
					 const int rank,
					 const int intent,
					 PyObject *obj);
  extern int array_has_column_major_storage(const PyArrayObject *ap);
  extern int copy_ND_array(const PyArrayObject *in, PyArrayObject *out);

#ifdef DEBUG_COPY_ND_ARRAY
  extern void dump_attrs(const PyArrayObject* arr);
#endif

#ifdef __cplusplus
}
#endif
#endif /* !Py_FORTRANOBJECT_H */
