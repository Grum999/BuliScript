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
        QMainWindow,
        QStatusBar
    )

from .bslanguagedef import BSLanguageDef

from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.utils import loadXmlUi
from buliscript.pktk.modules.menuutils import buildQMenuTree
from buliscript.pktk.modules.parser import Parser

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )


class VLine(QFrame):
    """A vertical line widget that can be used as a separator"""

    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine|self.Sunken)


# -----------------------------------------------------------------------------
class BSMainWindow(QMainWindow):
    """Buli Script main window"""

    DARK_THEME = 'dark'
    LIGHT_THEME = 'light'

    STATUSBAR_FILENAME = 0
    STATUSBAR_RO = 1
    STATUSBAR_ROWS = 2
    STATUSBAR_POS = 3
    STATUSBAR_SELECTION = 4
    STATUSBAR_INSOVR_MODE = 5
    STATUSBAR_LASTSECTION = 6

    dialogShown = pyqtSignal()

    # region: initialisation methods -------------------------------------------

    def __init__(self, uiController, parent=None):
        super(BSMainWindow, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'bsmainwindow.ui')
        loadXmlUi(uiFileName, self)

        self.__uiController = uiController
        self.__eventCallBack = {}

        self.__initStatusBar()
        self.__initBSDocuments()


    def __initStatusBar(self):
        """Initialise status bar

        [ Path/File name    | Column: 999 . Row: 999/999 | Selection: 999 | INSOVR ]
        """
        self.__statusBarWidgets=[
                QLabel(),                                   # File name
                QLabel(),                                   # file is in read-only mode
                QLabel("Rows: 0000"),                       # total number of rows
                QLabel("0000:0000"),                        # Current column/row
                QLabel("000:0000 - 000:0000 [00000]"),      # Selection start (col/row) - Selection end (col/row) [selection length]
                QLabel("WWW"),                              # INSert/OVeRwrite
            ]


        fontMetrics=self.__statusBarWidgets[BSMainWindow.STATUSBAR_FILENAME].fontMetrics()

        self.__statusBarWidgets[BSMainWindow.STATUSBAR_RO].setMinimumWidth(fontMetrics.boundingRect("RO").width())
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_ROWS].setMinimumWidth(fontMetrics.boundingRect("Rows: 0000").width())
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_POS].setMinimumWidth(fontMetrics.boundingRect("0000:0000").width())
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_SELECTION].setMinimumWidth(fontMetrics.boundingRect("000:0000 - 000:0000 [00000]").width())
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_INSOVR_MODE].setMinimumWidth(fontMetrics.boundingRect("INS_").width())

        self.__statusBarWidgets[BSMainWindow.STATUSBAR_FILENAME].setToolTip(i18n('Document file name'))
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_RO].setToolTip(i18n('Document in Read-Only mode'))
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_ROWS].setToolTip(i18n('Total number of rows'))
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_POS].setToolTip(i18n('Current position (column:row)'))
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_SELECTION].setToolTip(i18n('Current selection: Selection start (column:row) - Selection end (column:row) [selection length]'))
        self.__statusBarWidgets[BSMainWindow.STATUSBAR_INSOVR_MODE].setToolTip(i18n('INS: insert mode\nOVR: overwrite mode'))



        statusBar=self.statusBar()
        statusBar.addWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_FILENAME])
        statusBar.addPermanentWidget(VLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_RO])
        statusBar.addPermanentWidget(VLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_ROWS])
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_POS])
        statusBar.addPermanentWidget(VLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_SELECTION])
        statusBar.addPermanentWidget(VLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_INSOVR_MODE])

    def __initBSDocuments(self):
        """Initialise documents manager"""
        self.twDocuments.initialise(self, self.__uiController)


    def initMainView(self):
        """Initialise main view content"""
        pass


    def initMenu(self):
        """Initialise actions for menu defaukt menu"""
        def __insertLanguageAction(menuTree, autoCompletion):
            """Create action for Language menu

            Title=autoCompletion
            Action=insert autoCompletion
            """
            def execute(dummy=None):
                self.__uiController.commandLanguageInsert(autoCompletion[0])

            action=QAction(autoCompletion[0].replace('\x01', ''), menuTree[-1])
            action.setProperty('insert', autoCompletion[0])
            if len(autoCompletion)>1 and isinstance(autoCompletion[1], str):
                action.setToolTip(autoCompletion[1])

            action.triggered.connect(execute)
            menuTree[-1].addAction(action)

        # Menu SCRIPT
        self.actionFileNew.triggered.connect(self.__uiController.commandFileNew)
        self.actionFileOpen.triggered.connect(self.__uiController.commandFileOpen)
        self.actionFileReload.triggered.connect(self.__uiController.commandFileReload)
        self.actionFileSave.triggered.connect(self.__uiController.commandFileSave)
        self.actionFileSaveAs.triggered.connect(self.__uiController.commandFileSaveAs)
        self.actionFileSaveAll.triggered.connect(self.__uiController.commandFileSaveAll)
        self.actionFileClose.triggered.connect(self.__uiController.commandFileClose)
        self.actionFileCloseAll.triggered.connect(self.__uiController.commandFileCloseAll)
        self.actionFileQuit.triggered.connect(self.__uiController.commandQuit)

        # Menu EDIT
        self.actionEditUndo.triggered.connect(self.__uiController.commandEditUndo)
        self.actionEditRedo.triggered.connect(self.__uiController.commandEditRedo)
        self.actionEditCut.triggered.connect(self.__uiController.commandEditCut)
        self.actionEditCopy.triggered.connect(self.__uiController.commandEditCopy)
        self.actionEditPaste.triggered.connect(self.__uiController.commandEditPaste)
        self.actionEditSelectAll.triggered.connect(self.__uiController.commandEditSelectAll)

        # Menu SCRIPT
        self.actionScriptExecute.triggered.connect(self.__uiController.commandScriptExecute)

        # menu LANGUAGE
        # dynamically built from tokenizer autoCompletion rules
        for rule in self.__uiController.languageDef().tokenizer().rules():
            for autoCompletion in rule.autoCompletion():
                description=rule.description()
                if not description is None:
                    for menuPath in description.split('|'):
                        menuTree=buildQMenuTree(menuPath, None, self.menuLanguage)
                        if len(menuTree)>0:
                            #print(re.sub('\x01.*', '', autoCompletion[0]))
                            __insertLanguageAction(menuTree, autoCompletion)

        # Menu VIEW
        self.actionViewShowCanvas.triggered.connect(self.__uiController.commandViewShowCanvasVisible)
        self.actionViewShowCanvasOrigin.triggered.connect(self.__uiController.commandViewShowCanvasOrigin)
        self.actionViewShowCanvasGrid.triggered.connect(self.__uiController.commandViewShowCanvasGrid)
        self.actionViewShowCanvasPosition.triggered.connect(self.__uiController.commandViewShowCanvasPosition)
        self.actionViewShowConsole.triggered.connect(self.__uiController.commandViewShowConsoleVisible)

        # Menu SETTINGS
        self.actionSettingsPreferences.triggered.connect(self.__uiController.commandSettingsOpen)

        # Menu HELP
        self.actionHelpBuliScriptHandbook.triggered.connect(self.__uiController.commandHelpBs)
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

    def getWidgets(self):
        """Return a list of ALL widgets"""
        def appendWithSubWidget(parent):
            list=[parent]
            if len(parent.children())>0:
                for w in parent.children():
                    list+=appendWithSubWidget(w)
            return list

        return appendWithSubWidget(self)

    def documents(self):
        """Return BSDocuments instance"""
        return self.twDocuments

    def statusBarText(self, index):
        """Return text in status bar section designed by `index`"""
        if not isinstance(index, int):
            raise EInvalidStatus("Given `index` must be <int>")
        elif index < 0 or index > BSMainWindow.STATUSBAR_LASTSECTION:
            raise EInvalidValue(f"Given `index` must be between 0 and {BSMainWindow.STATUSBAR_LASTSECTION}")
        return self.__statusBarWidgets[index].text()

    def setStatusBarText(self, index, text):
        """Set given `text` in status bar section designed by `index`"""
        if not isinstance(index, int):
            raise EInvalidStatus("Given `index` must be <int>")
        elif index < 0 or index > BSMainWindow.STATUSBAR_LASTSECTION:
            raise EInvalidValue(f"Given `index` must be between 0 and {BSMainWindow.STATUSBAR_LASTSECTION}")

        if index==BSMainWindow.STATUSBAR_ROWS:
            text=f"Rows: {text}"

        self.__statusBarWidgets[index].setText(text)

        if len(text)==0:
            self.__statusBarWidgets[index].setToolTipDuration(1)
        else:
            self.__statusBarWidgets[index].setToolTipDuration(-1)

    def openedDocumentTabs(self):
        """Return number of documents tabs"""
        return self.twDocuments.count()


    # endregion: methods -------------------------------------------------------
