# -----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2022 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin framework
# -----------------------------------------------------------------------------

import sys
import os.path

from .pktk import (PkTk, EInvalidType, EInvalidValue, EInvalidStatus)

pluginsPath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if pluginsPath not in sys.path:
    # now, pktk modules for plugin <plugin> can be imported as:
    # import <plugin>.pktk.modules.xxxxx
    # import <plugin>.pktk.widgets.xxxxx
    sys.path.append(pluginsPath)
