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
import html

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QMainWindow,
        QStatusBar
    )

from .bslanguagedef import BSLanguageDef
from .bsrenderer import BSWRendererScene

from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.utils import loadXmlUi
from buliscript.pktk.modules.strutils import (
        stripHtml,
        stripTags
    )
from buliscript.pktk.modules.menuutils import buildQMenuTree
from buliscript.pktk.modules.parser import Parser
from buliscript.pktk.modules.tokenizer import TokenizerRule

from buliscript.pktk.widgets.wseparator import WVLine

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )


class WMenuForCommand(QWidgetAction):
    """Encapsulate a QLabel as a menu item, used to display completion command properly formatted in menu"""
    onEnter=Signal()

    def __init__(self, label, parent=None):
        super(WMenuForCommand, self).__init__(parent)
        self.__label = QLabel(self.__reformattedText(label))
        self.__label.setStyleSheet("QLabel:hover { background: palette(highlight); color: palette(highlighted-text);}")
        self.__label.setContentsMargins(4,4,4,4)
        self.__label.mousePressEvent=self.__pressEvent
        self.__label.enterEvent=self.__enterEvent

        self.__layout = QVBoxLayout()
        self.__layout.setSpacing(0)
        self.__layout.setContentsMargins(0,0,0,0)
        self.__layout.addWidget(self.__label)

        self.__widget = QWidget()
        self.__widget.setContentsMargins(0,0,0,0)
        self.__widget.setMouseTracking(True)
        self.__widget.setLayout(self.__layout)

        self.__hover=False

        self.setDefaultWidget(self.__widget)

    def __reformattedText(self, text):
        """Reformat given text, assuming it's a completion text command"""
        returned=[]
        texts=text.split('\x01')
        for index, textItem in enumerate(texts):
            if index%2==1:
                # odd text ("optionnal" information) are written smaller, with darker color
                returned.append(f"<i>{textItem}</i>")
            else:
                # normal font
                returned.append(textItem)

        return ''.join(returned)

    def __pressEvent(self, event):
        """When label clicked, trigger event for QWidgetAction and close parent menu"""
        self.trigger()
        menu=None
        parentWidget=self.parentWidget()
        while(isinstance(parentWidget, QMenu)):
            menu=parentWidget
            parentWidget=menu.parentWidget()

        if menu:
            menu.close()

    def __enterEvent(self, event):
        """When mouse goes over label, trigger signal onEnter"""
        self.onEnter.emit()



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

        self.setDockOptions(QMainWindow.AllowTabbedDocks|QMainWindow.AllowNestedDocks)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self.setDocumentMode(False)

        self.__initStatusBar()
        self.__initBSDocuments()
        self.__initCanvas()

        # tweak a little bit how tabs are rendered
        self.setStyleSheet("""
            QTabBar {
                background: palette(Base);
                padding: 0px;
                border: 0px none;
                margin: 0px;
                qproperty-drawBase: 0;
            }

            QTabBar::tab {
                height: 3ex;
                padding: 0px 1ex;
                border-left: 0px none;
                border-right: 0px none;
                border-bottom: 1px solid palette(Base);
                border-top: 3px solid palette(Base);
                background: palette(Base);
                color:palette(Text);
                margin: 0px;
            }
            QTabBar::tab:selected {
                border-top: 3px solid palette(Highlight);
                background: palette(Window);
                border-bottom: 1px solid palette(Window);
            }

            QTabBar::tab:hover {
                background: palette(Highlight);
                border-top: 3px solid palette(Highlight);
                color: palette(HighlightedText);
            }
            QTabBar::close-button {
                height: 8px;
                width: 8px;
            }
            QTabBar::scroller {
                width: 4ex;
            }

            BSDocuments>* {
                padding: 4px 0 0 0;
                margin: -2px;
                border: 0px none;
                background: palette(Window);

            }
            BSDocuments::pane{
                padding: 0px;
                margin: 0px;
                border: 0px none;
                background: palette(Window);
            }
        """)

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
        statusBar.addPermanentWidget(WVLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_RO])
        statusBar.addPermanentWidget(WVLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_ROWS])
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_POS])
        statusBar.addPermanentWidget(WVLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_SELECTION])
        statusBar.addPermanentWidget(WVLine())
        statusBar.addPermanentWidget(self.__statusBarWidgets[BSMainWindow.STATUSBAR_INSOVR_MODE])

    def __initBSDocuments(self):
        """Initialise documents manager"""
        self.twDocuments.initialise(self, self.__uiController)

    def __initCanvas(self):
        """Initialise canvas"""
        self.gvCanvas.setScene(self.__uiController.renderedScene())
        self.gvCanvas.zoomChanged.connect(self.__canvasZoomChanged)
        self.__uiController.renderedScene().setSize(20000,20000)
        self.__uiController.renderedScene().sceneUpdated.connect(self.__canvasSceneUpdated)

        self.lblZoomLevel.mousePressEvent=lambda x: self.gvCanvas.setZoom(1.0)
        self.__canvasSceneUpdated({})

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
            def onExecute(dummy=None):
                self.__uiController.commandLanguageInsert(self.sender().property('insert'))

            def onEnter(dummy=None):
                self.__uiController.commandDockLangageQuickHelpSet(self.sender().property('insert').split('\x01')[0])

            #print(autoCompletion[0])
            action=WMenuForCommand(html.escape(autoCompletion[0]), menuTree[-1])
            action.setProperty('insert', autoCompletion[0])
            if len(autoCompletion)>1 and isinstance(autoCompletion[1], str):
                tip=TokenizerRule.descriptionExtractSection(autoCompletion[1], 'title')
                if tip=='':
                    tip=autoCompletion[1]
                action.setStatusTip(stripHtml(tip))

            action.triggered.connect(onExecute)
            action.onEnter.connect(onEnter)
            menuTree[-1].addAction(action)

        # Menu SCRIPT
        # ----------------------------------------------------------------------
        self.actionFileNew.triggered.connect(self.__uiController.commandFileNew)
        self.actionFileOpen.triggered.connect(self.__uiController.commandFileOpen)
        self.actionFileReload.triggered.connect(self.__uiController.commandFileReload)
        self.actionFileSave.triggered.connect(self.__uiController.commandFileSave)
        self.actionFileSaveAs.triggered.connect(self.__uiController.commandFileSaveAs)
        self.actionFileSaveAll.triggered.connect(self.__uiController.commandFileSaveAll)
        self.actionFileClose.triggered.connect(self.__uiController.commandFileClose)
        self.actionFileCloseAll.triggered.connect(self.__uiController.commandFileCloseAll)
        self.actionFileQuit.triggered.connect(self.__uiController.commandQuit)

        self.menuFileRecent.aboutToShow.connect(self.__menuFileRecentShow)

        # Menu EDIT
        # ----------------------------------------------------------------------
        self.actionEditUndo.triggered.connect(self.__uiController.commandEditUndo)
        self.actionEditRedo.triggered.connect(self.__uiController.commandEditRedo)
        self.actionEditCut.triggered.connect(self.__uiController.commandEditCut)
        self.actionEditCopy.triggered.connect(self.__uiController.commandEditCopy)
        self.actionEditPaste.triggered.connect(self.__uiController.commandEditPaste)
        self.actionEditSelectAll.triggered.connect(self.__uiController.commandEditSelectAll)

        # menu LANGUAGE
        # ----------------------------------------------------------------------
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

        # Menu SCRIPT
        # ----------------------------------------------------------------------
        self.actionScriptExecute.triggered.connect(self.__uiController.commandScriptExecute)
        self.actionScriptBreakPause.triggered.connect(self.__uiController.commandScriptBreakPause)
        self.actionScriptStop.triggered.connect(self.__uiController.commandScriptStop)

        # Menu VIEW
        # ----------------------------------------------------------------------
        self.actionViewCanvasShowCanvas.triggered.connect(self.__uiController.commandViewShowCanvasVisible)
        self.actionViewCanvasShowCanvasOrigin.triggered.connect(self.__uiController.commandViewShowCanvasOrigin)
        self.actionViewCanvasShowCanvasGrid.triggered.connect(self.__uiController.commandViewShowCanvasGrid)
        self.actionViewCanvasShowCanvasPosition.triggered.connect(self.__uiController.commandViewShowCanvasPosition)

        # menu View > Language > ...
        # is built from uiController

        # Menu SETTINGS
        # ----------------------------------------------------------------------
        self.actionSettingsPreferences.triggered.connect(self.__uiController.commandSettingsOpen)

        # Menu HELP
        # ----------------------------------------------------------------------
        self.actionHelpBuliScriptHandbook.triggered.connect(self.__uiController.commandHelpBs)
        self.actionHelpAboutBS.triggered.connect(self.__uiController.commandAboutBs)

    # endregion: initialisation methods ----------------------------------------


    # region: define actions method --------------------------------------------

    def __menuFileRecentShow(self):
        """Menu for 'file recent' is about to be displayed

        Build menu content
        """
        self.__uiController.buildmenuFileRecent(self.menuFileRecent)

    def __actionNotYetImplemented(self, v=None):
        """"Method called when an action not yet implemented is triggered"""
        QMessageBox.warning(
                QWidget(),
                self.__uiController.name(),
                i18n(f"Sorry! Action has not yet been implemented ({v})")
            )

    def __canvasZoomChanged(self, zoomLevel):
        """Update zoom level for canvas"""
        self.lblZoomLevel.setText(f"{100*zoomLevel:.2f}%")

    def __canvasSceneUpdated(self, position):
        """Scene has been updated, refresh position&rotation info"""
        if 'r' in position:
            rotation=round(position['r'], 2)

            textR=''
            if rotation>0:
                textR=f'Left'
            elif rotation<0:
                textR=f'Right'

            self.lblNfoRotation.setText(f"Rotation: {abs(rotation)%360:.2f}° {textR}")
        else:
            self.lblNfoRotation.setText('')

        if 'x' in position and 'y' in position:
            self.lblNfoPosition.setText(f"Position: {position['x']:.2f} {position['y']:.2f}")
        else:
            self.lblNfoPosition.setText('')

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
