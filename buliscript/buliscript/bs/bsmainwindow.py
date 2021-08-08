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




# -----------------------------------------------------------------------------
#from .pktk import PkTk

import krita
import os
import re
import sys
import time

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal
    )
from PyQt5.QtWidgets import (
        QMainWindow
    )

from .bslanguagedef import BSLanguageDef

from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.utils import loadXmlUi
from buliscript.pktk.modules.menuutils import buildQMenuTree
from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )



# -----------------------------------------------------------------------------
class BSMainWindow(QMainWindow):
    """Buli Script main window"""

    DARK_THEME = 'dark'
    LIGHT_THEME = 'light'

    dialogShown = pyqtSignal()

    # region: initialisation methods -------------------------------------------

    def __init__(self, uiController, parent=None):
        super(BSMainWindow, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'bsmainwindow.ui')
        loadXmlUi(uiFileName, self)

        self.__uiController = uiController
        self.__eventCallBack = {}

        self.__fontMono = QFont()
        self.__fontMono.setPointSize(9)
        self.__fontMono.setFamily('DejaVu Sans Mono')

    def initMainView(self):
        """Initialise main view content"""
        #@pyqtSlot('QString')
        #def splitterMainView_Moved(pos, index):
        #    pass

    def initMenu(self):
        """Initialise actions for menu defaukt menu"""
        # Menu SCRIPT
        self.actionScriptNew.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptOpen.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptSave.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptSaveAs.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptSaveAll.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptClose.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptExecute.triggered.connect(self.__actionNotYetImplemented)
        self.actionScriptQuit.triggered.connect(self.__uiController.commandQuit)

        # Menu EDIT
        self.actionEditUndo.triggered.connect(self.__actionNotYetImplemented)
        self.actionEditRedo.triggered.connect(self.__actionNotYetImplemented)
        self.actionEditCut.triggered.connect(self.__actionNotYetImplemented)
        self.actionEditCopy.triggered.connect(self.__actionNotYetImplemented)
        self.actionEditPaste.triggered.connect(self.__actionNotYetImplemented)
        self.actionEditSelectAll.triggered.connect(self.__actionNotYetImplemented)

        # Menu VIEW
        self.actionViewShowCanvas.triggered.connect(self.__uiController.commandViewShowCanvasVisible)
        self.actionViewShowCanvasOrigin.triggered.connect(self.__uiController.commandViewShowCanvasOrigin)
        self.actionViewShowCanvasGrid.triggered.connect(self.__uiController.commandViewShowCanvasGrid)
        self.actionViewShowCanvasPosition.triggered.connect(self.__uiController.commandViewShowCanvasPosition)
        self.actionViewShowConsole.triggered.connect(self.__uiController.commandViewShowConsoleVisible)

        # Menu SETTINGS
        self.actionSettingsPreferences.triggered.connect(self.__actionNotYetImplemented)

        # Menu HELP
        self.actionHelpBuliScriptHandbook.triggered.connect(self.__actionNotYetImplemented)
        self.actionHelpAboutBS.triggered.connect(self.__uiController.commandAboutBs)

    # endregion: initialisation methods ----------------------------------------


    # region: define actions method --------------------------------------------

    def __actionNotYetImplemented(self, v=None):
        """"Method called when an action not yet implemented is triggered"""
        QMessageBox.warning(
                QWidget(),
                self.__uiController.name(),
                i18n(f"Sorry! Action has not yet been implemented ({v})")
            )

    # endregion: define actions method -----------------------------------------


    # region: events- ----------------------------------------------------------

    def showEvent(self, event):
        """Event trigerred when dialog is shown

           At this time, all widgets are initialised and size/visiblity is known


           Example
           =======
                # define callback function
                def my_callback_function():
                    # BSMainWindow shown!
                    pass

                # initialise a dialog from an xml .ui file
                dlgMain = BSMainWindow.loadUi(uiFileName)

                # execute my_callback_function() when dialog became visible
                dlgMain.dialogShown.connect(my_callback_function)
        """
        super(BSMainWindow, self).showEvent(event)

        self.dialogShown.emit()

    def closeEvent(self, event):
        """Event executed when window is about to be closed"""
        #event.ignore()
        self.__uiController.close()
        event.accept()

    def eventFilter(self, object, event):
        """Manage event filters for window"""
        if object in self.__eventCallBack.keys():
            return self.__eventCallBack[object](event)

        return super(BSMainWindow, self).eventFilter(object, event)

    def setEventCallback(self, object, method):
        """Add an event callback method for given object

           Example
           =======
                # define callback function
                def my_callback_function(event):
                    if event.type() == QEvent.xxxx:
                        # Event!
                        return True
                    return False


                # initialise a dialog from an xml .ui file
                dlgMain = BSMainWindow.loadUi(uiFileName)

                # define callback for widget from ui
                dlgMain.setEventCallback(dlgMain.my_widget, my_callback_function)
        """
        if object is None:
            return False

        self.__eventCallBack[object] = method
        object.installEventFilter(self)

    # endregion: events --------------------------------------------------------

    # region: methods ----------------------------------------------------------

    def __menuScriptQuit(self):
        """Quit BuliScript"""
        self.__uiController.commandQuit()

    def getWidgets(self):
        """Return a list of ALL widgets"""
        def appendWithSubWidget(parent):
            list=[parent]
            if len(parent.children())>0:
                for w in parent.children():
                    list+=appendWithSubWidget(w)
            return list

        return appendWithSubWidget(self)

    # endregion: methods -------------------------------------------------------



