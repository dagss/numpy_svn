
Scipy Core is a replacement of Numeric Python that adds the features
of numarray

python setup.py install

to install

The setup.py script will take advantage of fast BLAS on your system if it can find it.  You can help the process with a site.cfg file.

If fast BLAS and LAPACK cannot be found, then a slower default version is used. 

