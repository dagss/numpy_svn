#define FORTRANOBJECT_C
#include "fortranobject.h"

#ifdef __cplusplus
extern "C" {
#endif
/*
  This file implements: FortranObject, array_from_pyobj, copy_ND_array,
                       lazy_transpose, transpose_strides,
		       and array_has_column_major_storage.

  Author: Pearu Peterson <pearu@cens.ioc.ee>
  $Revision: 1.52 $
  $Date: 2005/07/11 07:44:20 $
*/

/************************* FortranObject *******************************/

typedef PyObject *(*fortranfunc)(PyObject *,PyObject *,PyObject *,void *);

PyObject *
PyFortranObject_New(FortranDataDef* defs, f2py_void_func init) {
  int i;
  PyFortranObject *fp = NULL;
  PyObject *v = NULL;
  if (init!=NULL)                           /* Initialize F90 module objects */
    (*(init))();
  if ((fp = PyObject_New(PyFortranObject, &PyFortran_Type))==NULL) return NULL;
  if ((fp->dict = PyDict_New())==NULL) return NULL;
  fp->len = 0;
  while (defs[fp->len].name != NULL) fp->len++;
  if (fp->len == 0) goto fail;
  fp->defs = defs;
  for (i=0;i<fp->len;i++)
    if (fp->defs[i].rank == -1) {                      /* Is Fortran routine */
      v = PyFortranObject_NewAsAttr(&(fp->defs[i]));
      if (v==NULL) return NULL;
      PyDict_SetItemString(fp->dict,fp->defs[i].name,v);
    } else
      if ((fp->defs[i].data)!=NULL) { /* Is Fortran variable or array (not allocatable) */
	v = PyArray_FromDimsAndData(fp->defs[i].rank,
				    fp->defs[i].dims.d,
				    fp->defs[i].type,
				    fp->defs[i].data);
	if (v==NULL) return NULL;
	if (fp->defs[i].rank>1) { /* Is multi-dimensional common block member */
	  transpose_strides((PyArrayObject*)v);
	  ((PyArrayObject*)v)->flags &= ~CONTIGUOUS;
	}
	PyDict_SetItemString(fp->dict,fp->defs[i].name,v);
      }
  Py_XDECREF(v);
  return (PyObject *)fp;
 fail:
  Py_XDECREF(v);
  return NULL;
}

PyObject *
PyFortranObject_NewAsAttr(FortranDataDef* defs) { /* used for calling F90 module routines */
  PyFortranObject *fp = NULL;
  fp = PyObject_New(PyFortranObject, &PyFortran_Type);
  if (fp == NULL) return NULL;
  if ((fp->dict = PyDict_New())==NULL) return NULL;
  fp->len = 1;
  fp->defs = defs;
  return (PyObject *)fp;
}

/* Fortran methods */

static void
fortran_dealloc(PyFortranObject *fp) {
  Py_XDECREF(fp->dict);
  PyMem_Del(fp);
}


static PyMethodDef fortran_methods[] = {
	{NULL,		NULL}		/* sentinel */
};


static PyObject *
fortran_doc (FortranDataDef def) {
  char *p;
  PyObject *s = NULL;
  int i;
  unsigned size=100;
  if (def.doc!=NULL)
    size += strlen(def.doc);
  p = (char*)malloc (size);
  if (sprintf(p,"%s - ",def.name)==0) goto fail;
  if (def.rank==-1) {
    if (def.doc==NULL) {
      if (sprintf(p,"%sno docs available",p)==0)
	goto fail;
    } else {
      if (sprintf(p,"%s%s",p,def.doc)==0)
	goto fail;
    }
  } else {
    PyArray_Descr *d = PyArray_DescrFromType(def.type);
    if (sprintf(p,"%s'%c'-",p,d->type)==0) goto fail;
    if (def.data==NULL) {
      if (sprintf(p,"%sarray(%d",p,def.dims.d[0])==0) goto fail;
      for(i=1;i<def.rank;++i)
	if (sprintf(p,"%s,%d",p,def.dims.d[i])==0) goto fail;
      if (sprintf(p,"%s), not allocated",p)==0) goto fail;
    } else {
      if (def.rank>0) {
	if (sprintf(p,"%sarray(%d",p,def.dims.d[0])==0) goto fail;
	for(i=1;i<def.rank;i++)
	  if (sprintf(p,"%s,%d",p,def.dims.d[i])==0) goto fail;
	if (sprintf(p,"%s)",p)==0) goto fail;
      } else {
	if (sprintf(p,"%sscalar",p)==0) goto fail;
      }
    }
  }
  if (sprintf(p,"%s\n",p)==0) goto fail;
  if (strlen(p)>size) {
    fprintf(stderr,"fortranobject.c:fortran_doc:len(p)=%d>%d(size): too long doc string required, increase size\n",strlen(p),size);
    goto fail;
  }
  s = PyString_FromString(p);
 fail:
  free(p);
  return s;
}

static FortranDataDef *save_def; /* save pointer of an allocatable array */
static void set_data(char *d,int *f) {  /* callback from Fortran */
  if (*f)                               /* In fortran f=allocated(d) */
    save_def->data = d;
  else
    save_def->data = NULL;
  /* printf("set_data: d=%p,f=%d\n",d,*f); */
}

static PyObject *
fortran_getattr(PyFortranObject *fp, char *name) {
  int i,j,k,flag;
  if (fp->dict != NULL) {
    PyObject *v = PyDict_GetItemString(fp->dict, name);
    if (v != NULL) {
      Py_INCREF(v);
      return v;
    }
  }
  for (i=0,j=1;i<fp->len && (j=strcmp(name,fp->defs[i].name));i++);
  if (j==0)
    if (fp->defs[i].rank!=-1) {                   /* F90 allocatable array */ 
      if (fp->defs[i].func==NULL) return NULL;
      for(k=0;k<fp->defs[i].rank;++k) 
	fp->defs[i].dims.d[k]=-1;
      save_def = &fp->defs[i];
      (*(fp->defs[i].func))(&fp->defs[i].rank,fp->defs[i].dims.d,set_data,&flag);
      if (flag==2)
	k = fp->defs[i].rank + 1;
      else
	k = fp->defs[i].rank;
      if (fp->defs[i].data !=NULL) {              /* array is allocated */
	PyObject *v = PyArray_FromDimsAndData(k,
					      fp->defs[i].dims.d,
					      fp->defs[i].type,
					      fp->defs[i].data
					      );
	if (v==NULL) return NULL;
	if (fp->defs[i].rank>1) {                 /* multi-dimensional array */
	  transpose_strides((PyArrayObject*)v);
	  ((PyArrayObject*)v)->flags &= ~CONTIGUOUS;
	}
	/* Py_INCREF(v); */
	return v;
      } else {                                    /* array is not allocated */
	Py_INCREF(Py_None);
	return Py_None;
      }
    }
  if (strcmp(name,"__dict__")==0) {
    Py_INCREF(fp->dict);
    return fp->dict;
  }
  if (strcmp(name,"__doc__")==0) {
    PyObject *s = PyString_FromString("");
    for (i=0;i<fp->len;i++)
      PyString_ConcatAndDel(&s,fortran_doc(fp->defs[i]));
    if (PyDict_SetItemString(fp->dict, name, s))
      return NULL;
    return s;
  }
  if ((strcmp(name,"_cpointer")==0) && (fp->len==1)) {
    PyObject *cobj = PyCObject_FromVoidPtr((void *)(fp->defs[0].data),NULL);
    if (PyDict_SetItemString(fp->dict, name, cobj))
      return NULL;
    return cobj;
  }
  return Py_FindMethod(fortran_methods, (PyObject *)fp, name);
}

static int
fortran_setattr(PyFortranObject *fp, char *name, PyObject *v) {
  int i,j,flag;
  PyArrayObject *arr = NULL;
  for (i=0,j=1;i<fp->len && (j=strcmp(name,fp->defs[i].name));i++);
  if (j==0) {
    if (fp->defs[i].rank==-1) {
      PyErr_SetString(PyExc_AttributeError,"over-writing fortran routine");
      return -1;
    }
    if (fp->defs[i].func!=NULL) { /* is allocatable array */
      int dims[F2PY_MAX_DIMS],k;
      save_def = &fp->defs[i];
      if (v!=Py_None) {     /* set new value (reallocate if needed --
			       see f2py generated code for more
			       details ) */
	for(k=0;k<fp->defs[i].rank;k++) dims[k]=-1;
	if ((arr = array_from_pyobj(fp->defs[i].type,dims,fp->defs[i].rank,F2PY_INTENT_IN,v))==NULL)
	  return -1;
	(*(fp->defs[i].func))(&fp->defs[i].rank,arr->dimensions,set_data,&flag);
      } else {             /* deallocate */
	for(k=0;k<fp->defs[i].rank;k++) dims[k]=0;
	(*(fp->defs[i].func))(&fp->defs[i].rank,dims,set_data,&flag);
	for(k=0;k<fp->defs[i].rank;k++) dims[k]=-1;
      }
      memcpy(fp->defs[i].dims.d,dims,fp->defs[i].rank*sizeof(int));
    } else {                     /* not allocatable array */
      if ((arr = array_from_pyobj(fp->defs[i].type,fp->defs[i].dims.d,fp->defs[i].rank,F2PY_INTENT_IN,v))==NULL)
	return -1;      
    }
    if (fp->defs[i].data!=NULL) { /* copy Python object to Fortran array */
      int s = _PyArray_multiply_list(fp->defs[i].dims.d,arr->nd);
      if (s==-1)
	s = _PyArray_multiply_list(arr->dimensions,arr->nd);
      if (s<0 ||
	  (memcpy(fp->defs[i].data,arr->data,s*arr->descr->elsize))==NULL) {
	if ((PyObject*)arr!=v) {
	  Py_DECREF(arr);
	}
	return -1;
      }
      if ((PyObject*)arr!=v) {
        Py_DECREF(arr);
      }
    } else return (fp->defs[i].func==NULL?-1:0);
    return 0; /* succesful */
  }
  if (fp->dict == NULL) {
    fp->dict = PyDict_New();
    if (fp->dict == NULL)
      return -1;
  }
  if (v == NULL) {
    int rv = PyDict_DelItemString(fp->dict, name);
    if (rv < 0)
      PyErr_SetString(PyExc_AttributeError,"delete non-existing fortran attribute");
    return rv;
  }
  else
    return PyDict_SetItemString(fp->dict, name, v);
}

static PyObject*
fortran_call(PyFortranObject *fp, PyObject *arg, PyObject *kw) {
  int i = 0;
  /*  printf("fortran call
      name=%s,func=%p,data=%p,%p\n",fp->defs[i].name,
      fp->defs[i].func,fp->defs[i].data,&fp->defs[i].data); */
  if (fp->defs[i].rank==-1) {/* is Fortran routine */
    if ((fp->defs[i].func==NULL)) {
      PyErr_Format(PyExc_RuntimeError, "no function to call");
      return NULL;
    }
    else if (fp->defs[i].data==NULL)
      /* dummy routine */
      return (*((fortranfunc)(fp->defs[i].func)))((PyObject *)fp,arg,kw,NULL);
    else
      return (*((fortranfunc)(fp->defs[i].func)))((PyObject *)fp,arg,kw,
						  (void *)fp->defs[i].data);
  }
  PyErr_Format(PyExc_TypeError, "this fortran object is not callable");
  return NULL;
}


PyTypeObject PyFortran_Type = {
  PyObject_HEAD_INIT(0)
  0,			/*ob_size*/
  "fortran",			/*tp_name*/
  sizeof(PyFortranObject),	/*tp_basicsize*/
  0,			/*tp_itemsize*/
  /* methods */
  (destructor)fortran_dealloc, /*tp_dealloc*/
  0,			/*tp_print*/
  (getattrfunc)fortran_getattr, /*tp_getattr*/
  (setattrfunc)fortran_setattr, /*tp_setattr*/
  0,			/*tp_compare*/
  0,			/*tp_repr*/
  0,			/*tp_as_number*/
  0,			/*tp_as_sequence*/
  0,			/*tp_as_mapping*/
  0,			/*tp_hash*/
  (ternaryfunc)fortran_call,                    /*tp_call*/
};

/************************* f2py_report_atexit *******************************/

#ifdef F2PY_REPORT_ATEXIT
static int passed_time = 0;
static int passed_counter = 0;
static int passed_call_time = 0;
static struct timeb start_time;
static struct timeb stop_time;
static struct timeb start_call_time;
static struct timeb stop_call_time;
static int cb_passed_time = 0;
static int cb_passed_counter = 0;
static int cb_passed_call_time = 0;
static struct timeb cb_start_time;
static struct timeb cb_stop_time;
static struct timeb cb_start_call_time;
static struct timeb cb_stop_call_time;

extern void f2py_start_clock(void) { ftime(&start_time); }
extern
void f2py_start_call_clock(void) {
  f2py_stop_clock();
  ftime(&start_call_time);
}
extern
void f2py_stop_clock(void) {
  ftime(&stop_time);
  passed_time += 1000*(stop_time.time - start_time.time);
  passed_time += stop_time.millitm - start_time.millitm;
}
extern
void f2py_stop_call_clock(void) {
  ftime(&stop_call_time);
  passed_call_time += 1000*(stop_call_time.time - start_call_time.time);
  passed_call_time += stop_call_time.millitm - start_call_time.millitm;
  passed_counter += 1;
  f2py_start_clock();
}

extern void f2py_cb_start_clock(void) { ftime(&cb_start_time); }
extern
void f2py_cb_start_call_clock(void) {
  f2py_cb_stop_clock();
  ftime(&cb_start_call_time);
}
extern
void f2py_cb_stop_clock(void) {
  ftime(&cb_stop_time);
  cb_passed_time += 1000*(cb_stop_time.time - cb_start_time.time);
  cb_passed_time += cb_stop_time.millitm - cb_start_time.millitm;
}
extern
void f2py_cb_stop_call_clock(void) {
  ftime(&cb_stop_call_time);
  cb_passed_call_time += 1000*(cb_stop_call_time.time - cb_start_call_time.time);
  cb_passed_call_time += cb_stop_call_time.millitm - cb_start_call_time.millitm;
  cb_passed_counter += 1;
  f2py_cb_start_clock();
}

static int f2py_report_on_exit_been_here = 0;
extern
void f2py_report_on_exit(int exit_flag,void *name) {
  if (f2py_report_on_exit_been_here) {
    fprintf(stderr,"             %s\n",(char*)name);
    return;
  }
  f2py_report_on_exit_been_here = 1;
  fprintf(stderr,"                      /-----------------------\\\n");
  fprintf(stderr,"                     < F2PY performance report >\n");
  fprintf(stderr,"                      \\-----------------------/\n");
  fprintf(stderr,"Overall time spent in ...\n");
  fprintf(stderr,"(a) wrapped (Fortran/C) functions           : %8d msec\n",
	  passed_call_time);
  fprintf(stderr,"(b) f2py interface,           %6d calls  : %8d msec\n",
	  passed_counter,passed_time);
  fprintf(stderr,"(c) call-back (Python) functions            : %8d msec\n",
	  cb_passed_call_time);
  fprintf(stderr,"(d) f2py call-back interface, %6d calls  : %8d msec\n",
	  cb_passed_counter,cb_passed_time);
  
  fprintf(stderr,"(e) wrapped (Fortran/C) functions (acctual) : %8d msec\n\n",
	  passed_call_time-cb_passed_call_time-cb_passed_time);
  fprintf(stderr,"Use -DF2PY_REPORT_ATEXIT_DISABLE to disable this message.\n");
  fprintf(stderr,"Exit status: %d\n",exit_flag);
  fprintf(stderr,"Modules    : %s\n",(char*)name);
}
#endif

/********************** report on array copy ****************************/

#ifdef F2PY_REPORT_ON_ARRAY_COPY
static void f2py_report_on_array_copy(PyArrayObject* arr, char* func_name) {
  const long arr_size = PyArray_Size((PyObject *)arr);
  if (arr_size>F2PY_REPORT_ON_ARRAY_COPY) {
    fprintf(stderr,"copied an array using %s: size=%ld, elsize=%d\n", 
	    func_name, arr_size, arr->descr->elsize);
  }
}
#endif

/************************* lazy_transpose *******************************/

extern
void lazy_transpose(PyArrayObject* arr) {
  /*
    Changes the order of array strides and dimensions.  This
    corresponds to the lazy transpose of a Numeric array in-situ.
    Note that this function is assumed to be used even times for a
    given array. Otherwise, the caller should set flags &= ~CONTIGUOUS.
   */
  int rank,i,s,j; 
  rank = arr->nd; 
  if (rank < 2) return;

  for(i=0,j=rank-1;i<rank/2;++i,--j) {
    s = arr->strides[i];
    arr->strides[i] = arr->strides[j];
    arr->strides[j] = s;
    s = arr->dimensions[i];
    arr->dimensions[i] = arr->dimensions[j];
    arr->dimensions[j] = s;
  }
}

extern
void transpose_strides(PyArrayObject* arr) {
  int rank,i,j;
  rank = arr->nd; 
  if (rank < 2) return;
  j = arr->strides[rank-1];
  for(i=0;i<rank;++i) {
    arr->strides[i] = j;
    j *= arr->dimensions[i];
  }
}

/************************* array_from_obj *******************************/

/* 
 * File: array_from_pyobj.c 
 *
 * Description:
 * ------------ 
 * Provides array_from_pyobj function that returns a contigious array
 * object with the given dimensions and required storage order, either
 * in row-major (C) or column-major (Fortran) order. The function
 * array_from_pyobj is very flexible about its Python object argument
 * that can be any number, list, tuple, or array.
 * 
 * array_from_pyobj is used in f2py generated Python extension
 * modules.
 *
 * Author: Pearu Peterson <pearu@cens.ioc.ee>
 * Created: 13-16 January 2002
 * $Id: fortranobject.c,v 1.52 2005/07/11 07:44:20 pearu Exp $
 */


#define ARR_IS_NULL(arr_is_NULL,mess) \
if (arr_is_NULL) { \
    fprintf(stderr,"array_from_pyobj:" mess); \
    return NULL; \
}

#define CHECK_DIMS_DEFINED(rank,dims,mess) \
if (count_nonpos(rank,dims)) { int i;\
  fprintf(stderr,"array_from_pyobj:" mess); \
  fprintf(stderr,"rank=%d dimensions=[ ",rank); \
  for(i=0;i<rank;++i) fprintf(stderr,"%d ",dims[i]); \
  fprintf(stderr,"]\n"); \
  return NULL; \
}

#define HAS_PROPER_ELSIZE(arr,type_num) \
  ((PyArray_DescrFromType(type_num)->elsize) == (arr)->descr->elsize)

static
int count_nonpos(const int rank,
		 const int *dims) {
  int i=0,r=0;
  while (i<rank) {
    if (dims[i] <= 0) ++r;
    ++i;
  }
  return r;
}

static int check_and_fix_dimensions(const PyArrayObject* arr,
				    const int rank,
				    int *dims);

#ifdef DEBUG_COPY_ND_ARRAY
void dump_attrs(const PyArrayObject* arr) {
  int rank = arr->nd;
  int size = PyArray_Size((PyObject *)arr);
  int i;
  printf("\trank = %d, flags = %d, size = %d\n",rank,arr->flags,size);
  printf("\tstrides = [");
  for(i=0;i<rank;++i) {
    printf("%3d",arr->strides[i]);
  }
  printf("]\n\t dimensions = [");
  for(i=0;i<rank;++i) {
    printf("%3d",arr->dimensions[i]);
  }
  printf("]\n");
}
#endif

#if defined(NUMARRAY)
/* Numarray's array wrapper routines NA_InputArray, NA_OutputArray, and
NA_IoArray constrain input sequences and arrays to meet a set of numarray
behavioral requirements.  The principle behind the routines is to create a
temporary array to use as a shadow or substitute of an array/sequence which
doesn't satisfy the requirements.  For Input, data is copied from the original
sequence to the temporary.  For Output, data is copied back from the temporary
to the original sequence.  For Io, data flow is bidirectional.  Key
requirements for numarray describe alignment, byteswapping, and contiguity.

Because Fortran mode in f2py appears to require a transposed array, and
because numarray's use of temporary copies "erases" the striding effects
of the transpose, numarray has to un-transpose and then re-transpose
following the wrapping.  By un-transposing, wrapping, and re-transposing,
the Fortran striding effects are preserved.  When un-transposing, both
the original and shadow arrays must be untransposed.
*/
static PyArrayObject *
numarray_wrap(PyObject *obj, int intent)
{
	PyArrayObject *arr;
	if (intent & F2PY_INTENT_INOUT) {
		if ((intent & F2PY_INTENT_C) || !NA_NumArrayCheck(obj)) {
			arr = NA_IoArray(obj, tAny, NUM_C_ARRAY);
		} else { /* FORTRAN and NumArray */
			if (NA_swapAxes((PyArrayObject *) obj, -1, -2) < 0)
				return NULL;
			arr = NA_IoArray(
				obj, tAny, NUM_ALIGNED|NUM_NOTSWAPPED);
			if (NA_swapAxes((PyArrayObject *) obj, -1, -2) < 0)
			 	return NULL;
			if (((PyObject *)arr) != obj) {
			 	if (NA_swapAxes(arr, -1, -2) < 0)
			 		return NULL;
			}
		}
	} else if (intent & F2PY_INTENT_IN) {
		arr = NA_InputArray(obj, tAny, NUM_C_ARRAY);
        } else if (intent & F2PY_INTENT_OUT) {
	        arr = NA_OutputArray(obj, tAny, NUM_C_ARRAY);
	} else {
	  arr = (PyArrayObject *) PyErr_Format(PyExc_RuntimeError,
					       "unknown intent: %08x", intent);
	}
	if (((PyObject *)arr) == obj) {
	  Py_XDECREF(obj);
        }
	return arr;
}
#endif

#define SWAPTYPE(a,b,t) {t c; c = (a); (a) = (b); (b) = c; }

static int swap_arrays(PyArrayObject* arr1, PyArrayObject* arr2) {
#ifdef NUMARRAY
  fprintf(stderr,"swap_arrays: intent(inplace) not implemented for Numarray.\n"); 
  return 1;
#else
  SWAPTYPE(arr1->data,arr2->data,char*);
  SWAPTYPE(arr1->nd,arr2->nd,int);
  SWAPTYPE(arr1->dimensions,arr2->dimensions,int*);
  SWAPTYPE(arr1->strides,arr2->strides,int*);
  SWAPTYPE(arr1->base,arr2->base,PyObject*);
  SWAPTYPE(arr1->descr,arr2->descr,PyArray_Descr*);
  SWAPTYPE(arr1->flags,arr2->flags,int);
  /* SWAPTYPE(arr1->weakreflist,arr2->weakreflist,PyObject*); */
  return 0;
#endif
}

extern
PyArrayObject* array_from_pyobj(const int type_num,
				int *dims,
				const int rank,
				const int intent,
				PyObject *obj) {
  /* Note about reference counting
     -----------------------------
     If the caller returns the array to Python, it must be done with
     Py_BuildValue("N",arr).
     Otherwise, if obj!=arr then the caller must call Py_DECREF(arr).
  */

  if (intent & F2PY_INTENT_CACHE) {
    /* Don't expect correct storage order or anything reasonable when
       returning intent(cache) array. */ 
    if ((intent & F2PY_INTENT_HIDE)
	|| (obj==Py_None)) {
      PyArrayObject *arr = NULL;
      CHECK_DIMS_DEFINED(rank,dims,"optional,intent(cache) must"
			 " have defined dimensions.\n");
      arr = (PyArrayObject *)PyArray_FromDims(rank,dims,type_num);
      ARR_IS_NULL(arr==NULL,"FromDims failed: optional,intent(cache)\n");
/*       if (intent & F2PY_INTENT_OUT) */
/* 	Py_INCREF(arr); */
      return arr;
    }

    if (PyArray_Check(obj) 
	&& ISCONTIGUOUS((PyArrayObject *)obj)
	&& HAS_PROPER_ELSIZE((PyArrayObject *)obj,type_num)
	) {
      if (check_and_fix_dimensions((PyArrayObject *)obj,rank,dims))
	return NULL; /*XXX: set exception */
      {
	PyArrayObject *obj2;
#if !defined(NUMARRAY)
	if (intent & F2PY_INTENT_OUT)
	  Py_INCREF(obj);
	obj2 = (PyArrayObject *) obj;
#else
	obj2 = numarray_wrap(obj, intent);
#endif
	return obj2;
      }
    }
    ARR_IS_NULL(1,"intent(cache) must be contiguous array with a proper elsize.\n");
  }

  if (intent & F2PY_INTENT_HIDE) {
    PyArrayObject *arr = NULL;
    CHECK_DIMS_DEFINED(rank,dims,"intent(hide) must have defined dimensions.\n");
    arr = (PyArrayObject *)PyArray_FromDims(rank,dims,type_num);
    ARR_IS_NULL(arr==NULL,"FromDims failed: intent(hide)\n");
    if (intent & F2PY_INTENT_OUT) {
      if ((!(intent & F2PY_INTENT_C)) && (rank>1)) {
	transpose_strides(arr);
	arr->flags &= ~CONTIGUOUS;
      }
/*       Py_INCREF(arr); */
    }
    return arr;
  }

  if (PyArray_Check(obj)) { /* here we have always intent(in) or
			       intent(inout) or intent(inplace) */
    PyArrayObject *arr;
    int is_cont;

#if !defined(NUMARRAY)
    arr = (PyArrayObject *)obj;
#else
    arr = numarray_wrap(obj, intent);
#endif
    is_cont = (intent & F2PY_INTENT_C) ? 
      (ISCONTIGUOUS(arr)) : (2*array_has_column_major_storage(arr));
    if (check_and_fix_dimensions(arr,rank,dims))
      return NULL; /*XXX: set exception */
    if ((intent & F2PY_INTENT_COPY)
	|| (! (is_cont
	       && HAS_PROPER_ELSIZE(arr,type_num)
	       && PyArray_CanCastSafely(arr->descr->type_num,type_num)
	       /* Make PyArray_CanCastSafely safer for 64-bit machines: */
	       && (arr->descr->type_num==PyArray_LONG?type_num!=PyArray_DOUBLE:1)
	       ))) {
      PyArrayObject *tmp_arr = NULL;
      if (intent & F2PY_INTENT_INOUT) {
	ARR_IS_NULL(1,"intent(inout) array must be contiguous and"
		    " with a proper type and size.\n")
	  }
      if ((rank>1) && (! (intent & F2PY_INTENT_C))) {
	lazy_transpose(arr);
      }
/*       if (PyArray_CanCastSafely(arr->descr->type_num,type_num)) { */
/* 	tmp_arr = (PyArrayObject *)PyArray_CopyFromObject(obj,type_num,0,0); */
/* 	ARR_IS_NULL(arr==NULL,"CopyFromObject failed: array.\n"); */
/*       } else */
      {
	tmp_arr = (PyArrayObject *)PyArray_FromDims(arr->nd,
						    arr->dimensions,
						    type_num);
	ARR_IS_NULL(tmp_arr==NULL,"FromDims failed: array with unsafe cast.\n");
	if (copy_ND_array(arr,tmp_arr))
	  ARR_IS_NULL(1,"copy_ND_array failed: array with unsafe cast.\n");
      }
      if ((rank>1) && (! (intent & F2PY_INTENT_C))) {
	lazy_transpose(arr);
	lazy_transpose(tmp_arr);	
	tmp_arr->flags &= ~CONTIGUOUS;
      }
      /* discard numarray temporary for creating well behaved array */
#if defined(NUMARRAY)
      if (((PyObject *)arr) != obj) {
	Py_XDECREF(arr);
      }
#endif
      if (intent & F2PY_INTENT_INPLACE) {
	if (swap_arrays(arr,tmp_arr))
	  return NULL;
	Py_XDECREF(tmp_arr);
	if (intent & F2PY_INTENT_OUT)
	  Py_INCREF(arr);
      } else {
	arr = tmp_arr;
      }
    } else {
      if ((intent & F2PY_INTENT_OUT)
#if defined(NUMARRAY)
	  /* numarray can't assume that arr == obj */
	  && (((PyObject *)arr) == obj)
#endif
	  ) {
	Py_INCREF(arr);
      }
    }
    return arr;
  }

  if ((obj==Py_None) && (intent & F2PY_OPTIONAL)) {
    PyArrayObject *arr = NULL;
    CHECK_DIMS_DEFINED(rank,dims,"optional must have defined dimensions.\n");    
    arr = (PyArrayObject *)PyArray_FromDims(rank,dims,type_num);
    ARR_IS_NULL(arr==NULL,"FromDims failed: optional.\n");
    if (intent & F2PY_INTENT_OUT) {
      if ((!(intent & F2PY_INTENT_C)) && (rank>1)) {
	transpose_strides(arr);
	arr->flags &= ~CONTIGUOUS;
      }
/*       Py_INCREF(arr); */
    }
    return arr;
  }

  if ((intent & F2PY_INTENT_INOUT) || (intent & F2PY_INTENT_INPLACE)) {
    ARR_IS_NULL(1,"intent(inout)|intent(inplace) argument must be an array.\n");
  }

  {
    PyArrayObject *arr = (PyArrayObject *) \
      PyArray_ContiguousFromObject(obj,type_num,0,0);
    ARR_IS_NULL(arr==NULL,"ContiguousFromObject failed: not a sequence.\n");
    if (check_and_fix_dimensions(arr,rank,dims))
      return NULL; /*XXX: set exception */

    if ((rank>1) && (! (intent & F2PY_INTENT_C))) {
      PyArrayObject *tmp_arr = NULL;
      lazy_transpose(arr);
      arr->flags &= ~CONTIGUOUS;
      tmp_arr = (PyArrayObject *) PyArray_CopyFromObject((PyObject *)arr,type_num,0,0);
#ifdef F2PY_REPORT_ON_ARRAY_COPY
      f2py_report_on_array_copy(tmp_arr,"PyArray_CopyFromObject");
#endif
      Py_DECREF(arr);
      arr = tmp_arr;
      ARR_IS_NULL(arr==NULL,"CopyFromObject(Array) failed: intent(fortran)\n");
      lazy_transpose(arr);
      arr->flags &= ~CONTIGUOUS;
    }
/*     if (intent & F2PY_INTENT_OUT) */
/*       Py_INCREF(arr); */
    return arr;
  }

}

           /*****************************************/
           /* Helper functions for array_from_pyobj */
           /*****************************************/

extern
int array_has_column_major_storage(const PyArrayObject *ap) {
  /* array_has_column_major_storage(a) is equivalent to
     transpose(a).iscontiguous() but more efficient.

     This function can be used in order to decide whether to use a
     Fortran or C version of a wrapped function. This is relevant, for
     example, in choosing a clapack or flapack function depending on
     the storage order of array arguments.
  */
  int sd;
  int i;
  sd = ap->descr->elsize;
  for (i=0;i<ap->nd;++i) {
    if (ap->dimensions[i] == 0) return 1;
    if (ap->strides[i] != sd) return 0;
    sd *= ap->dimensions[i];
  }
  return 1;
}

static
int check_and_fix_dimensions(const PyArrayObject* arr,const int rank,int *dims) {
  /*
    This function fills in blanks (that are -1\'s) in dims list using
    the dimensions from arr. It also checks that non-blank dims will
    match with the corresponding values in arr dimensions.
   */
  const int arr_size = (arr->nd)?PyArray_Size((PyObject *)arr):1;

  if (rank > arr->nd) { /* [1,2] -> [[1],[2]]; 1 -> [[1]]  */
    int new_size = 1;
    int free_axe = -1;
    int i;
    /* Fill dims where -1 or 0; check dimensions; calc new_size; */
    for(i=0;i<arr->nd;++i) { 
      if (dims[i] >= 0) {
	if (dims[i]!=arr->dimensions[i]) {
	  fprintf(stderr,"%d-th dimension must be fixed to %d but got %d\n",
		  i,dims[i],arr->dimensions[i]);
	  return 1;
	}
	if (!dims[i]) dims[i] = 1;
      } else {
	dims[i] = arr->dimensions[i] ? arr->dimensions[i] : 1;
      }
      new_size *= dims[i];
    }
    for(i=arr->nd;i<rank;++i)
      if (dims[i]>1) {
	fprintf(stderr,"%d-th dimension must be %d but got 0 (not defined).\n",
		i,dims[i]);
	return 1;
      } else if (free_axe<0)
	free_axe = i;
      else
	dims[i] = 1;
    if (free_axe>=0) {
      dims[free_axe] = arr_size/new_size;
      new_size *= dims[free_axe];
    }
    if (new_size != arr_size) {
      fprintf(stderr,"confused: new_size=%d, arr_size=%d (maybe too many free"
	      " indices)\n",new_size,arr_size);
      return 1;
    }
  } else { /* [[1,2]] -> [[1],[2]] */
    int i,j,d;
    int effrank;
    int size;
    for (i=0,effrank=0;i<arr->nd;++i)
      if (arr->dimensions[i]>1) ++effrank;
    if (dims[rank-1]>=0)
      if (effrank>rank) {
	fprintf(stderr,"too many axes: %d (effrank=%d), expected rank=%d\n",
		arr->nd,effrank,rank);
	return 1;
      }
    for (i=0,j=0;i<rank;++i) {
      while (j<arr->nd && arr->dimensions[j]<2) ++j;
      if (j>=arr->nd) d = 1;
      else d = arr->dimensions[j++];
      if (dims[i]>=0) {
	if (d>1 && d!=dims[i]) {
	  fprintf(stderr,"%d-th dimension must be fixed to %d but got %d (real index=%d)\n",
		  i,dims[i],d,j-1);
	  return 1;	  
	}
	if (!dims[i]) dims[i] = 1;
      } else
	dims[i] = d;
    }
    for (i=rank;i<arr->nd;++i) { /* [[1,2],[3,4]] -> [1,2,3,4] */
      while (j<arr->nd && arr->dimensions[j]<2) ++j;
      if (j>=arr->nd) d = 1;
      else d = arr->dimensions[j++];
      dims[rank-1] *= d;
    }
    for (i=0,size=1;i<rank;++i) size *= dims[i];
    if (size != arr_size) {
      fprintf(stderr,"confused: size=%d, arr_size=%d, rank=%d, effrank=%d, arr.nd=%d, dims=[",
	      size,arr_size,rank,effrank,arr->nd);
      for (i=0;i<rank;++i) fprintf(stderr," %d",dims[i]);
      fprintf(stderr," ], arr.dims=[");
      for (i=0;i<arr->nd;++i) fprintf(stderr," %d",arr->dimensions[i]);
      fprintf(stderr," ]\n");
      return 1;
    }
  }
  return 0;
}

/* End of file: array_from_pyobj.c */


/************************* copy_ND_array *******************************/

#if defined(NUMARRAY)

extern 
int copy_ND_array(const PyArrayObject *in, PyArrayObject *out)
{
#ifdef F2PY_REPORT_ON_ARRAY_COPY
  f2py_report_on_array_copy(out,"NA_copyArray");
#endif
  return NA_copyArray(out, in);
} 
#elif defined(NDARRAY_VERSION)
extern
int copy_ND_array(const PyArrayObject *in, PyArrayObject *out)
{
#ifdef F2PY_REPORT_ON_ARRAY_COPY
  f2py_report_on_array_copy(out, "CopyInto");
#endif
  return PyArray_CopyInto(out, in);
}
#else
/*     Here starts Travis Oliphant's contribution    */
#define INCREMENT(ret_ind, nd, max_ind) \
{ \
  int k; \
  k = (nd) - 1; \
  if (k<0) (ret_ind)[0] = (max_ind)[0]; else \
  if (++(ret_ind)[k] >= (max_ind)[k]) { \
    while (k >= 0 && ((ret_ind)[k] >= (max_ind)[k]-1)) \
      (ret_ind)[k--] = 0; \
    if (k >= 0) (ret_ind)[k]++; \
    else (ret_ind)[0] = (max_ind)[0]; \
  }  \
}
#define CALCINDEX(indx, nd_index, strides, ndim) \
{ \
  int i; \
  indx = 0; \
  for (i=0; i < (ndim); ++i)  \
    indx += nd_index[i]*strides[i]; \
} 

static void CDOUBLE_to_CDOUBLE(double *ip, int ipstep, double *op, int opstep, int n) {
  int i; 
  for(i=0;i<n;i++,ip+=ipstep*2,op+=opstep*2) {
    *op = (double)*ip;
    *(op+1) = (double)*(ip+1);
  }
}
static void CFLOAT_to_CFLOAT(float *ip, int ipstep, float *op, int opstep, int n) {
  int i;
  for(i=0;i<n;i++,ip+=ipstep*2,op+=opstep*2) {
    *op = (float)*ip;
    *(op+1) = (float)*(ip+1);
  }
}
static void CDOUBLE_to_CFLOAT(double *ip, int ipstep, float *op, int opstep, int n) {
  int i; 
  for(i=0;i<n;i++,ip+=ipstep*2,op+=opstep*2) {
    *op = (float)*ip;
    *(op+1) = (float)*(ip+1);
  }
}
static void CFLOAT_to_CDOUBLE(float *ip, int ipstep, double *op, int opstep, int n) {
  int i;
  for(i=0;i<n;i++,ip+=ipstep*2,op+=opstep*2) {
    *op = (double)*ip;
    *(op+1) = (double)*(ip+1);
  }
}

extern 
int copy_ND_array(const PyArrayObject *in, PyArrayObject *out)
{

  /* This routine copies an N-D array in to an N-D array out where both
     can be discontiguous.  An appropriate (raw) cast is made on the data.
  */

  /* It works by using an N-1 length vector to hold the N-1 first indices 
     into the array.  This counter is looped through copying (and casting) 
     the entire last dimension at a time.
  */

  int *nd_index, indx1;
  int indx2, last_dim;
  int instep, outstep;
  PyArray_VectorUnaryFunc *cast = in->descr->cast[out->descr->type_num];

#ifdef DEBUG_COPY_ND_ARRAY
   printf("\n");
   printf("IN:\n");
   dump_attrs(in);
#endif

  if (0 == in->nd) {
    cast(in->data,1,out->data,1,1);
    return 0;
  }

#ifdef F2PY_REPORT_ON_ARRAY_COPY
  f2py_report_on_array_copy(out,"copy_ND_array");
#endif

  if (in->descr->type_num==PyArray_CDOUBLE
      && out->descr->type_num==PyArray_CDOUBLE)
    cast = (PyArray_VectorUnaryFunc*)CDOUBLE_to_CDOUBLE;
  else if (in->descr->type_num==PyArray_CFLOAT 
	   && out->descr->type_num==PyArray_CFLOAT)
    cast = (PyArray_VectorUnaryFunc*)CFLOAT_to_CFLOAT;
  else if (in->descr->type_num==PyArray_CFLOAT 
	   && out->descr->type_num==PyArray_CDOUBLE)
    cast = (PyArray_VectorUnaryFunc*)CFLOAT_to_CDOUBLE;
  else if (in->descr->type_num==PyArray_CDOUBLE
	   && out->descr->type_num==PyArray_CFLOAT)
    cast = (PyArray_VectorUnaryFunc*)CDOUBLE_to_CFLOAT;

  if (1 == in->nd) {
    instep = in->strides[0] / in->descr->elsize;
    outstep = out->strides[0] / out->descr->elsize;
    cast(in->data,instep,out->data,outstep,in->dimensions[0]);
  } else {
    nd_index = (int *)calloc(in->nd-1,sizeof(int));
    if (NULL == nd_index ) {
      fprintf(stderr,
	      "copy_ND_array: could not allocate memory for index array.\n");
      return -1;
    }

    last_dim = in->nd - 1;
    instep = in->strides[last_dim] / in->descr->elsize;
    outstep = out->strides[last_dim] / out->descr->elsize;

    while(nd_index[0] != in->dimensions[0]) {
      CALCINDEX(indx1,nd_index,in->strides,in->nd-1);
      CALCINDEX(indx2,nd_index,out->strides,out->nd-1);
      /* Copy (with an appropriate cast) the last dimension of the array */
      cast(in->data+indx1, instep,
	   out->data+indx2, outstep,
	   in->dimensions[last_dim]);
      INCREMENT(nd_index,in->nd-1,in->dimensions);
    }
    free(nd_index);
  }

#ifdef DEBUG_COPY_ND_ARRAY
  {
    const int arr_size = PyArray_Size((PyObject *)in);
    int i;
    for(i=0;i<arr_size;++i) {
      printf("in[%d] = ",i);
      PyObject_Print((PyObject*)(in->descr->getitem(in->data+i*in->descr->elsize)),stdout,0);
      printf("\n");
    }
  }
  {
    const int arr_size = PyArray_Size((PyObject *)out);
    int i;
    for(i=0;i<arr_size;++i) {
      printf("out[%d] = ",i);
      PyObject_Print((PyObject*)(out->descr->getitem(out->data+i*out->descr->elsize)),stdout,0);
      printf("\n");
    }
  }
#endif

  return 0;
} 
/* EOF T.O.'s contib */
#endif

#ifdef __cplusplus
}
#endif
/************************* EOF fortranobject.c *******************************/
