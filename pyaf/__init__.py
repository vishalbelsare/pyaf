# Copyright (C) 2016 Antoine Carme <Antoine.Carme@outlook.com>
# All rights reserved.

# This file is part of the Python Automatic Forecasting (PyAF) library and is made available under
# the terms of the 3 Clause BSD license

def check_python_version_for_pyaf():
    import six
    if six.PY2:
        raise Exception("PYAF_ERROR_PYTHON_2_NOT_SUPPORTED")


check_python_version_for_pyaf()

from . import ForecastEngine, HierarchicalForecastEngine

__version__ = '5.0'

def activate_timer_logging():
    import pyaf.TS.Utils as tsutil
    tsutil.activate_timer_logging()

