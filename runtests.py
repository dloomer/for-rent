#!/usr/bin/env python
import sys
import unittest

sys.path.insert(0, '.')

if len(sys.argv) > 1:
    module_names = [x.split(".")[0].replace('/', '.') for x in sys.argv[1:]]
    testsuite = unittest.TestLoader().loadTestsFromNames(module_names)
else:
    testsuite = unittest.TestLoader().discover('./tests')
unittest.TextTestRunner().run(testsuite)
