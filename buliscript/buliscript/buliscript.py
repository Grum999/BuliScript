#-----------------------------------------------------------------------------
# Buli Script
# Copyright (C) 2020 - Grum999
# -----------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see https://www.gnu.org/licenses/
# -----------------------------------------------------------------------------
# A Krita plugin designed to draw programmatically
# -----------------------------------------------------------------------------

import os
import re
import sys
import time

import PyQt5.uic

from krita import (
        Extension,
        Krita
    )

from PyQt5.Qt import *
from PyQt5 import QtCore
from PyQt5.QtCore import (
        pyqtSlot
    )

if __name__ != '__main__':
     # script is executed from Krita, loaded as a module
    __PLUGIN_EXEC_FROM__ = 'KRITA'

    from .pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )

    from .bs.bsuicontroller import BSUIController
    from buliscript.pktk.modules.utils import checkKritaVersion
else:
    # Execution from 'Scripter' plugin?
    __PLUGIN_EXEC_FROM__ = 'SCRIPTER_PLUGIN'

    from importlib import reload

    print("======================================")
    print(f'Execution from {__PLUGIN_EXEC_FROM__}')

    for module in list(sys.modules.keys()):
        if not re.search(r'^buliscript\.', module) is None:
            print('Reload module {0}: {1}', module, sys.modules[module])
            reload(sys.modules[module])

    from buliscript.pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )

    from buliscript.bs.bsuicontroller import BSUIController
    from buliscript.pktk.modules.utils import checkKritaVersion

    print("======================================")


EXTENSION_ID = 'pykrita_buliscript'
PLUGIN_VERSION = '0.1.0a'
PLUGIN_MENU_ENTRY = 'Buli Script'

REQUIRED_KRITA_VERSION = (4, 4, 0)


class BuliScript(Extension):

    def __init__(self, parent):
        # Default options

        # Always initialise the superclass.
        # This is necessary to create the underlying C++ object
        super().__init__(parent)
        self.parent = parent
        self.__uiController = None
        self.__isKritaVersionOk = checkKritaVersion(*REQUIRED_KRITA_VERSION)


    def __initUiController(self, kritaIsStarting=False):
        """Initialise UI controller

        `kritaIsStarting` set to True if UiConbtroller is intialised during Krita's startup,
        otherwise set to False (initialised on first manual execution)
        """
        try:
            Krita.instance().notifier().applicationClosing.disconnect()
        except Exception as e:
            pass

        if self.__uiController is None:
            # no controller, create it
            # (otherwise, with Krita 5.0.0, can be triggered more than once time - on each new window)
            self.__uiController = BSUIController(PLUGIN_MENU_ENTRY, PLUGIN_VERSION, kritaIsStarting)


    def setup(self):
        """Is executed at Krita's startup"""
        @pyqtSlot()
        def windowCreated():
            # the best place to initialise controller (just after main window is created)
            self.__initUiController(True)

        if not self.__isKritaVersionOk:
            return

        if checkKritaVersion(5,0,0):
            # windowCreated signal has been implemented with krita 5.0.0
            Krita.instance().notifier().setActive(True)
            Krita.instance().notifier().windowCreated.connect(windowCreated)


    def createActions(self, window):
        action = window.createAction(EXTENSION_ID, PLUGIN_MENU_ENTRY, "tools/scripts")
        action.triggered.connect(self.start)


    def start(self):
        """Execute Buli Script"""
        # ----------------------------------------------------------------------
        # Create dialog box
        if not self.__isKritaVersionOk:
            QMessageBox.information(QWidget(),
                                      PLUGIN_MENU_ENTRY,
                                      "At least, Krita version {0} is required to use plugin...".format('.'.join([str(v) for v in REQUIRED_KRITA_VERSION]))
                                    )
            return

        if self.__uiController is None:
            # with krita 5.0.0, might be created at krita startup
            self.__initUiController(False)
        self.__uiController.start()

if __PLUGIN_EXEC_FROM__ == 'SCRIPTER_PLUGIN':
    sys.stdout = sys.__stdout__

    # Disconnect signals if any before assigning new signals

    ch=BuliScript(Krita.instance())
    ch.setup()
    ch.start()
