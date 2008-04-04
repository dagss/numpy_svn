"""
from numpy.lib.financial import *

>>> rate(10,0,-3500,10000)
0.11069085371426901

>>> irr([-150000, 15000, 25000, 35000, 45000, 60000])
0.052432888859414106

>>> pv(0.07,20,12000,0)
-127128.17094619398

>>> fv(0.075, 20, -2000,0,0)
86609.362673042924

>>> pmt(0.08/12,5*12,15000)
-304.14591432620773

>>> nper(0.075,-2000,0,100000.)
21.544944197323336

>>> npv(0.05,[-15000,1500,2500,3500,4500,6000])
117.04271900089589

"""

from numpy.testing import *
import numpy as np

class TestDocs(NumpyTestCase):
    def check_doctests(self): return self.rundocs()

if __name__ == "__main__":
    NumpyTest().run()
