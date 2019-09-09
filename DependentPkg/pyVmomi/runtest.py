# Copyright (c) 2018 VMware, Inc.  All rights reserved.
# -- VMware Confidential

""" Python VMOMI tests

This module provides a place to add tests for pyVmomi.
Also, it can be used as a playground to experiment with new utilities.
"""

import os
import sys
import unittest

thisFile = os.path.realpath(__file__)

# The pyVmomi package root.
pyVmomiPath = os.path.dirname(os.path.dirname(thisFile))

# The pyVmomi modules depend on six.py.
sixPath = os.path.join(os.environ.get("TCROOT", "/build/toolchain"),
                       "noarch", "six-1.9.0", "lib", "python2.7",
                       "site-packages")

# Both of those enable the importing of pyVmomi.
sys.path.insert(0, pyVmomiPath)
sys.path.insert(0, sixPath)

import pyVmomi


class VersionTest(unittest.TestCase):
    """Test the version support for pyVmomi

    This class contains tests for various VMODL version uitilites.
    """

    def test_GetVersionProps(self):
        """GetVersionProps() doesn't crash"""

        for vmodlNamespace in ["vim", "vpx"]:
            ver = pyVmomi.VmomiSupport.stableVersions.Get(vmodlNamespace)

            self.assertTrue(
                pyVmomi.VmomiSupport.GetVersionProps(ver) is not None)


if "__main__" == __name__:
    sys.exit(unittest.main())
