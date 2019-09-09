__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/


"""
import abc
from framework.common import TestConstants as tc


class OperationBase():
    __metaclass__ = abc.ABCMeta

    def __init__(self,tc):
        self.tc = tc

    def runTest(self):
        """ Implement this Method To run test"""