#!/usr/bin/env python3

import sys
import os
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

tests_dir = os.path.join(project_root, "tests", "unit")
suite = unittest.TestLoader().discover(start_dir=tests_dir, pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
