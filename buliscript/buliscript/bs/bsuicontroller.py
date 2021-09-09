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

import os.path
from pathlib import Path

import sys
import re
import base64

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal,
        QDir,
        QRect
    )

from PyQt5.QtWidgets import (
        QMessageBox,
        QWidget
    )


from .bsdwlanguage import (
        BSDockWidgetLangageQuickHelp,
        BSDockWidgetLangageReference
    )
from .bshistory import BSHistory
from .bsinterpreter import BSInterpreter
from .bslanguagedef import BSLanguageDef
from .bsmainwindow import BSMainWindow
from .bssystray import BSSysTray
from .bssettings import (
        BSSettings,
        BSSettingsKey
    )

from buliscript.pktk.modules.tokenizer import TokenizerRule
from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.utils import (
        checkKritaVersion,
        Debug
    )
from buliscript.pktk.modules.imgutils import buildIcon
from buliscript.pktk.modules.about import AboutWindow

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )

from buliscript.pktk.modules.ekrita import (
        EKritaNode
    )


# ------------------------------------------------------------------------------
class BSUIController(QObject):
    """The controller provide an access to all BuliScript functions
    """
    bsWindowShown = Signal()
    bsWindowClosed = Signal()

    def __init__(self, bsName="Buli Script", bsVersion="testing", kritaIsStarting=False):
        super(BSUIController, self).__init__(None)

        self.__bsStarted = False
        self.__bsStarting = False


        self.__window = None
        self.__bsName = bsName
        self.__bsVersion = bsVersion
        self.__bsTitle = "{0} - {1}".format(bsName, bsVersion)

        self.__languageDef=BSLanguageDef()

        BSSettings.load()

        UITheme.load()
        # BC theme must be loaded before systray is initialized
        # #----- uncomment if local resources # UITheme.load(os.path.join(os.path.dirname(__file__), 'resources'))

        self.__systray=BSSysTray(self)
        self.commandSettingsSysTrayMode(BSSettings.get(BSSettingsKey.CONFIG_SYSTRAY_MODE))

        # store a global reference to activeWindow to be able to work with
        # activeWindow signals
        # https://krita-artists.org/t/krita-4-4-new-api/12247?u=grum999
        self.__kraActiveWindow = None

        # keep in memory last directory from open/save dialog box
        self.__lastDocumentDirectoryOpen=""
        self.__lastDocumentDirectorySave=""

        # keep document history list
        self.__historyFiles=BSHistory()

        # clipboard
        self.__clipboard = QGuiApplication.clipboard()
        self.__clipboard.changed.connect(self.__updateMenuEditPaste)

        # cache directory
        self.__bsCachePath = os.path.join(QStandardPaths.writableLocation(QStandardPaths.CacheLocation), "buliscript")
        try:
            os.makedirs(self.__bsCachePath, exist_ok=True)
            for subDirectory in ['documents']:
                os.makedirs(self.cachePath(subDirectory), exist_ok=True)
        except Exception as e:
            Debug.print('[BSUIController.__init__] Unable to create directory {0}: {1}', self.cachePath(subDirectory), str(e))

        # current active document
        self.__currentDocument=None

        self.__initialised = False

        self.__dwLangageReference=None
        self.__dwLangageQuickHelp=None

        self.__dwLangageQuickHelpAction=None
        self.__dwLangageReferenceAction=None

        self.__interpreter=BSInterpreter(self.__languageDef)

        if kritaIsStarting and BSSettings.get(BSSettingsKey.CONFIG_OPEN_ATSTARTUP):
            self.start()


    def start(self):
        """Start plugin interface"""
        if self.__bsStarted:
            # user interface is already started, bring to front and exit
            self.commandViewBringToFront()
            return
        elif self.__bsStarting:
            # user interface is already starting, exit
            return

        self.__bsStarting = True

        # Check if windows are opened and then, connect signal if needed
        self.__checkKritaWindows()


        self.__initialised = False
        self.__window = BSMainWindow(self)
        self.__window.dialogShown.connect(self.__initSettings)

        self.__window.documents().documentChanged.connect(self.__documentChanged)

        # initialise docker widgets
        self.__dwLangageReference=BSDockWidgetLangageReference(self.__window, self.__languageDef)
        self.__dwLangageReference.setObjectName('__dwLangageReference')
        self.__dwLangageReference.languageReferenceSelected.connect(self.commandDockLangageQuickHelpSet)
        self.__dwLangageReference.languageReferenceDblClicked.connect(self.commandLanguageInsert)
        self.__dwLangageReferenceAction=self.__dwLangageReference.toggleViewAction()
        self.__dwLangageReferenceAction.setText(i18n("Reference"))
        self.__window.menuViewLanguage.addAction(self.__dwLangageReferenceAction)
        self.__window.addDockWidget(Qt.RightDockWidgetArea, self.__dwLangageReference)

        self.__dwLangageQuickHelp=BSDockWidgetLangageQuickHelp(self.__window)
        self.__dwLangageQuickHelp.setObjectName('__dwLangageQuickHelp')
        self.__dwLangageQuickHelp.visibilityChanged.connect(lambda visible: self.__window.documents().setCompletionHelpEnabled(not visible))
        self.__dwLangageQuickHelpAction=self.__dwLangageQuickHelp.toggleViewAction()
        self.__dwLangageQuickHelpAction.setText(i18n("Quick Help"))
        self.__window.menuViewLanguage.addAction(self.__dwLangageQuickHelpAction)
        self.__window.addDockWidget(Qt.RightDockWidgetArea, self.__dwLangageQuickHelp)

        self.__window.setWindowTitle(self.__bsTitle)
        self.__window.show()
        self.__window.activateWindow()


    # region: initialisation methods -------------------------------------------

    def __initSettings(self):
        """There's some visual settings that need to have the window visible
        (ie: the widget size are known) to be applied
        """
        if self.__initialised:
            self.__bsStarted = True
            self.bsWindowShown.emit()
            # already initialised, do nothing
            return

        # Here we know we have an active window
        if self.__kraActiveWindow is None:
            self.__kraActiveWindow=Krita.instance().activeWindow()
        try:
            # should not occurs as uicontroller is initialised only once, but...
            self.__kraActiveWindow.themeChanged.disconnect(self.__themeChanged)
        except:
            pass
        self.__kraActiveWindow.themeChanged.connect(self.__themeChanged)

        self.__window.initMainView()

        # reload
        BSSettings.load()

        self.commandSettingsSaveSessionOnExit(BSSettings.get(BSSettingsKey.CONFIG_SESSION_SAVE))
        self.commandSettingsSysTrayMode(BSSettings.get(BSSettingsKey.CONFIG_SYSTRAY_MODE))
        self.commandSettingsOpenAtStartup(BSSettings.get(BSSettingsKey.CONFIG_OPEN_ATSTARTUP))

        self.commandViewMainWindowGeometry(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY))
        self.commandViewMainWindowMaximized(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED))
        self.commandViewMainSplitterPosition(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION))
        self.commandViewSecondarySplitterPosition(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION))

        self.commandViewShowCanvasVisible(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE))
        self.commandViewShowCanvasOrigin(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN))
        self.commandViewShowCanvasGrid(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID))
        self.commandViewShowCanvasPosition(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION))
        self.commandViewShowConsoleVisible(BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE))

        qtlayoutNfoB64=BSSettings.get(BSSettingsKey.SESSION_MAINWINDOW_VIEW_DOCKERS_LAYOUT)
        if qtlayoutNfoB64!='':
            qtLayoutNfo=base64.b64decode(qtlayoutNfoB64.encode())
            self.__window.restoreState(qtLayoutNfo)

            # to init completer
            self.__window.documents().setCompletionHelpEnabled(False)
        else:
            self.commandViewDockLangageQuickHelpVisible(False)
            self.commandViewDockLangageReferenceVisible(False)

        self.__lastDocumentDirectoryOpen=BSSettings.get(BSSettingsKey.SESSION_PATH_LASTOPENED)
        self.__lastDocumentDirectorySave=BSSettings.get(BSSettingsKey.SESSION_PATH_LASTSAVED)

        # do not load from here, already loaded from BSDocuments() initialisation
        # for fileName in BSSettings.get(BSSettingsKey.SESSION_DOCUMENTS_OPENED):
        #     self.__window.documents().openDocument(fileName)

        self.__historyFiles.setMaxItems(BSSettings.get(BSSettingsKey.CONFIG_SESSION_DOCUMENTS_RECENTS_COUNT))
        self.__historyFiles.setItems(BSSettings.get(BSSettingsKey.SESSION_DOCUMENTS_RECENTS))
        self.__historyFiles.removeMissingFiles()

        self.__window.initMenu()

        self.__initialised = True
        self.__bsStarted = True
        self.__bsStarting = False
        self.bsWindowShown.emit()

        self.__currentDocument=self.__window.documents().document()
        self.updateMenu()

    def __themeChanged(self):
        """Theme has been changed, reload resources"""
        def buildPixmapList(widget):
            pixmaps=[]
            for propertyName in widget.dynamicPropertyNames():
                pName=bytes(propertyName).decode()
                if re.match('__bsIcon_', pName):
                    # a reference to resource path has been stored,
                    # reload icon from it
                    if pName == '__bsIcon_normalon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Normal, QIcon.On) )
                    elif pName == '__bsIcon_normaloff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Normal, QIcon.Off) )
                    elif pName == '__bsIcon_disabledon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Disabled, QIcon.On) )
                    elif pName == '__bsIcon_disabledoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Disabled, QIcon.Off) )
                    elif pName == '__bsIcon_activeon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Active, QIcon.On) )
                    elif pName == '__bsIcon_activeoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Active, QIcon.Off) )
                    elif pName == '__bsIcon_selectedon':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Selected, QIcon.On) )
                    elif pName == '__bsIcon_selectedoff':
                        pixmaps.append( (QPixmap(widget.property(propertyName)), QIcon.Selected, QIcon.Off) )
            return pixmaps

        UITheme.reloadResources()

        # need to apply new palette to widgets
        # otherwise it seems they keep to refer to the old palette...
        palette = QApplication.palette()
        widgetList = self.__window.getWidgets()

        for widget in widgetList:
            if isinstance(widget, BCWPathBar) or isinstance(widget, BreadcrumbsAddressBar):
                widget.updatePalette()
            elif hasattr(widget, 'setPalette'):
                # force palette to be applied to widget
                widget.setPalette(palette)

            if isinstance(widget, QTabWidget):
                # For QTabWidget, it's not possible to set icon directly,
                # need to use setTabIcon()
                for tabIndex in range(widget.count()):
                    tabWidget = widget.widget(tabIndex)

                    if not widget.tabIcon(tabIndex) is None:
                        pixmaps=buildPixmapList(tabWidget)
                        if len(pixmaps) > 0:
                            widget.setTabIcon(tabIndex, buildIcon(pixmaps))

            # need to do something to relad icons...
            elif hasattr(widget, 'icon'):
                pixmaps=buildPixmapList(widget)
                if len(pixmaps) > 0:
                    widget.setIcon(buildIcon(pixmaps))

    def __documentChanged(self, document):
        """Current active document has been changed"""
        self.__currentDocument=document
        self.updateMenu()

    def __checkKritaWindows(self):
        """Check if windows signal windowClosed() is already defined and, if not,
        define it
        """
        # applicationClosing signal can't be used, because when while BS is opened,
        # application is still running and then signal is not trigerred..
        #
        # solution is, when a window is closed, to check how many windows are still
        # opened
        #
        for window in Krita.instance().windows():
            # DO NOT SET PROPERTY ON WINDOW
            # but on qwindow() as the qwindow() is always the same
            # and as window is just an instance that wrap the underlied QMainWindow
            # a new object is returned each time windows() list is returned
            if window.qwindow().property('__bsWindowClosed') != True:
                window.windowClosed.connect(self.__windowClosed)
                window.qwindow().setProperty('__bsWindowClosed', True)

    def __windowClosed(self):
        """A krita window has been closed"""
        # check how many windows are still opened
        # if there's no window opened, close BS

        # need to ensure that all windows are connected to close signal
        # (maybe, since BS has been opened, new Krita windows has been created...)
        self.__checkKritaWindows()

        if len( Krita.instance().windows()) == 0:
            self.commandQuit()

    def __updateMenuEditPaste(self):
        """Update menu Edit > Paste according to clipboard content"""
        if self.__currentDocument:
            scriptIsRunning=False
            self.__window.actionEditPaste.setEnabled(self.__currentDocument.codeEditor().canPaste() and not (scriptIsRunning or self.__currentDocument.readOnly()))

    def updateMenu(self):
        """Update menu for current active document"""
        if not self.__currentDocument:
            # no active document? does nothing
            return

        scriptIsRunning=False
        cursor=self.__currentDocument.codeEditor().cursorPosition()

        # Menu FILE
        # ----------------------------------------------------------------------
        self.__window.actionFileNew.setEnabled(not scriptIsRunning)
        self.__window.actionFileOpen.setEnabled(not scriptIsRunning)

        self.__window.actionFileReload.setEnabled(not (scriptIsRunning or self.__currentDocument.fileName() is None) and os.path.isfile(self.__currentDocument.fileName()))
        self.__window.actionFileSave.setEnabled(self.__currentDocument.modified() and not(scriptIsRunning or self.__currentDocument.readOnly()))

        self.__window.actionFileSaveAs.setEnabled(not scriptIsRunning)
        self.__window.actionFileSaveAll.setEnabled(not scriptIsRunning)
        self.__window.actionFileClose.setEnabled(not scriptIsRunning)
        self.__window.actionFileCloseAll.setEnabled(not scriptIsRunning)

        # Menu EDIT
        # ----------------------------------------------------------------------
        self.__window.actionEditUndo.setEnabled(self.__currentDocument.codeEditor().document().isUndoAvailable() and not (scriptIsRunning or self.__currentDocument.readOnly()))
        self.__window.actionEditRedo.setEnabled(self.__currentDocument.codeEditor().document().isRedoAvailable() and not (scriptIsRunning or self.__currentDocument.readOnly()))
        self.__window.actionEditCut.setEnabled(cursor[3]>0 and not (scriptIsRunning or self.__currentDocument.readOnly()))
        self.__window.actionEditCopy.setEnabled(cursor[3]>0 and not (scriptIsRunning or self.__currentDocument.readOnly()))
        self.__updateMenuEditPaste()

        # menu LANGUAGE
        # ----------------------------------------------------------------------
        for index, item in enumerate(self.__window.menuLanguage.children()):
            if index==0:
                # first children is a QAction thatdefine QMenu?
                continue
            if isinstance(item, QMenu) or isinstance(item, QAction):
                item.setEnabled(not (self.__currentDocument.readOnly() or scriptIsRunning))

        # Menu SCRIPT
        # ----------------------------------------------------------------------
        self.__window.actionScriptExecute.setEnabled(not scriptIsRunning)
        self.__window.actionScriptBreakPause.setEnabled(scriptIsRunning)
        self.__window.actionScriptStop.setEnabled(scriptIsRunning)

        # Menu VIEW
        # ----------------------------------------------------------------------
        self.__window.actionViewCanvasShowCanvas.setEnabled(not scriptIsRunning)
        self.__window.actionViewCanvasShowCanvasOrigin.setEnabled(not scriptIsRunning)
        self.__window.actionViewCanvasShowCanvasGrid.setEnabled(not scriptIsRunning)
        self.__window.actionViewCanvasShowCanvasPosition.setEnabled(not scriptIsRunning)

        # Menu SETTINGS
        # ----------------------------------------------------------------------
        self.__window.actionSettingsPreferences.setEnabled(not scriptIsRunning)

    def buildmenuFileRecent(self, menu):
        """Menu for 'file recent' is about to be displayed

        Build menu content
        """
        @pyqtSlot('QString')
        def menuFileRecent_Clicked(action):
            # open document
            self.commandFileOpen(self.sender().property('fileName'))

        menu.clear()

        if self.__historyFiles.length()==0:
            action = QAction(i18n("(no recent scripts)"), self)
            action.setEnabled(False)
            menu.addAction(action)
        else:
            for fileName in reversed(self.__historyFiles.list()):
                action = QAction(fileName.replace('&', '&&'), self)
                action.setProperty('fileName', fileName)
                action.triggered.connect(menuFileRecent_Clicked)
                menu.addAction(action)


    # endregion: initialisation methods ----------------------------------------


    # region: getter/setters ---------------------------------------------------

    def name(self):
        """Return BuliScript plugin name"""
        return self.__bsName

    def theme(self):
        """Return theme object"""
        return self.__theme

    def started(self):
        """Return True if BuliScript interface is started"""
        return self.__bsStarted

    def version(self):
        """Return BuliScript plugin version"""
        return self.__bsVersion

    def title(self):
        """Return BuliScript plugin title"""
        return self.__bsTitle

    def languageDef(self):
        """Return BuliScript language definition"""
        return self.__languageDef

    def cachePath(self, subDirectory=None):
        """Return BuliScript cache directory"""
        if subDirectory is None or subDirectory=='':
            return self.__bsCachePath
        elif isinstance(subDirectory, str):
            return os.path.join(self.__bsCachePath, subDirectory)
        else:
            raise EInvalidType('Given ` subDirectory` must be None or <str>')

    # endregion: getter/setters ------------------------------------------------




    # region: define commands --------------------------------------------------

    def saveSettings(self):
        """Save the current settings"""
        BSSettings.set(BSSettingsKey.CONFIG_SESSION_SAVE, self.__window.actionSettingsSaveSessionOnExit.isChecked())

        if BSSettings.get(BSSettingsKey.CONFIG_SESSION_SAVE):
            # save current session properties only if allowed
            if self.__window.actionViewCanvasShowCanvas.isChecked():
                # if not checked, hidden panel size is 0 so, do not save it (splitter position is already properly defined)
                BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION, self.__window.splMain.sizes())

            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_VISIBLE, self.__window.actionViewCanvasShowCanvas.isChecked())
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN, self.__window.actionViewCanvasShowCanvasOrigin.isChecked())
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID, self.__window.actionViewCanvasShowCanvasGrid.isChecked())
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION, self.__window.actionViewCanvasShowCanvasPosition.isChecked())

            BSSettings.set(BSSettingsKey.SESSION_PATH_LASTOPENED, self.__lastDocumentDirectoryOpen)
            BSSettings.set(BSSettingsKey.SESSION_PATH_LASTSAVED, self.__lastDocumentDirectorySave)

            BSSettings.set(BSSettingsKey.SESSION_DOCUMENTS_RECENTS, self.__historyFiles.list())

            tmpList=[]
            for document in self.__window.documents().documents():
                tmpList.append(f"@{document.cacheUuid()}")

            BSSettings.set(BSSettingsKey.SESSION_DOCUMENTS_OPENED, tmpList)
            BSSettings.set(BSSettingsKey.SESSION_DOCUMENTS_ACTIVE, self.__window.documents().currentIndex())


            if self.__window.actionViewShowConsole.isChecked():
                # if not checked, hidden panel size is 0 so, do not save it (splitter position is already properly defined)
                BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION, self.__window.splSecondary.sizes())

            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CONSOLE_VISIBLE, self.__window.actionViewShowConsole.isChecked())

            qtlayoutNfoB64=self.__window.saveState()
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_DOCKERS_LAYOUT, base64.b64encode(qtlayoutNfoB64).decode())

            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_MAXIMIZED, self.__window.isMaximized())
            if not self.__window.isMaximized():
                # when maximized geometry is full screen geomtry, then do it only if no in maximized
                BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY, [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()])

        return BSSettings.save()

    def close(self):
        """When window is about to be closed, execute some cleanup/backup/stuff before exiting BuliScript"""
        # save current settings
        for document in self.__window.documents().documents():
            document.saveCache()

        self.saveSettings()

        # need to close dockers, because if they're floating, close BuliScript
        # don't close floating dockers
        self.__dwLangageReference.close()
        self.__dwLangageQuickHelp.close()

        self.__dwLangageReference=None
        self.__dwLangageQuickHelp=None

        self.__bsStarted = False
        self.bsWindowClosed.emit()

    def optionIsMaximized(self):
        """Return current option value"""
        return self.__window.isMaximized()

    def commandQuit(self):
        """Close Buli Script"""
        self.__window.close()

    def commandFileNew(self):
        """Create a new empty document"""
        self.__window.documents().newDocument()

    def commandFileOpen(self, file=None):
        """Open file"""
        if file is None or isinstance(file, bool):
            # if bool=>triggered from menu
            fileNames, dummy=QFileDialog.getOpenFileNames(self.__window,
                                                          i18n("Open a Buli Script document"),
                                                          self.__lastDocumentDirectoryOpen,
                                                          "BuliScript Files (*.bs);;All Files (*.*)")

            if len(fileNames)>0:
                for fileName in fileNames:
                    self.commandFileOpen(fileName)
        elif isinstance(file, str):
            try:
                if not self.__window.documents().openDocument(file):
                    raise EInvalidStatus("Unable to open file")

                self.__lastDocumentDirectoryOpen=os.path.dirname(file)

                self.__historyFiles.remove(file)

            except Exception as e:
                Debug.print('[BSUIController.commandFileOpen] unable to open file {0}: {1}', file, str(e))
                return False
            return True
        else:
            raise EInvalidType('Given `file` is not valid')

    def commandFileSave(self, index=None):
        """Save document designed by `index` (or current document if `index` is None),
        using document filename

        If document has never been saved, will execute "save as" to request for a file name
        """
        if isinstance(index, bool):
            # probably called from menu event
            index=None

        document=self.__window.documents().document(index)

        if not document.modified():
            # don(t need to save is not modified
            return False


        if document.fileName() is None:
            # document never been saved (no path/file name)
            # then switch to "save as" to aks user for a filename
            return self.commandFileSaveAs(index)

        try:
            if not self.__window.documents().saveDocument(index):
                raise EInvalidStatus("Unable to save file")

            self.updateMenu()
        except Exception as e:
            Debug.print('[BSUIController.commandFileSave] unable to save file {0}: {1}', file, str(e))
            return False
        return True

    def commandFileSaveAs(self, index=None, newFileName=None):
        """Save current document with another name"""
        if isinstance(index, bool):
            # probably called from menu event
            index=None

        document=self.__window.documents().document(index)

        if newFileName is None:
            oldFileName=document.fileName()
            fileName=oldFileName
        else:
            oldFileName=None
            fileName=newFileName

        if fileName is None:
            # if no filename, use last directory where a file has been saved
            # as default directory for dialog box
            fileName=self.__lastDocumentDirectorySave

        if index is None:
            index=self.__window.documents().currentIndex()

        # switch to tab as document (mostly: if "save all" is executed, this help
        # to determinate which document is saved)
        self.__window.documents().setCurrentIndex(index)



        if newFileName is None:
            fileName, dummy=QFileDialog.getSaveFileName(self.__window,
                                                        i18n("Save Buli Script document"),
                                                        fileName,
                                                        "BuliScript Files (*.bs);;All Files (*.*)")
        if fileName!='':
            try:
                if not self.__window.documents().saveDocument(index, fileName):
                    raise EInvalidStatus("Unable to save file")

                if not oldFileName is None and oldFileName!=fileName:
                    # as saved with on another location, consider old location
                    # is closed and add it to history
                    self.__historyFiles.append(oldFileName)

                # keep in memory
                self.__lastDocumentDirectorySave=os.path.dirname(fileName)

                self.updateMenu()
            except Exception as e:
                Debug.print('[BSUIController.commandFileSaveAs] unable to save file {0}: {1}', fileName, str(e))
                return False
            return True
        return False

    def commandFileSaveAll(self):
        """Save all documents at once"""
        for index in range(self.__window.documents().count()):
            self.commandFileSave(index)

    def commandFileClose(self, index=None, askIfNotSaved=True):
        """Close current document

        If document has been modified, ask for: save/don't save/cancel
        """
        if isinstance(index, bool):
            # probably called from menu event
            index=None

        document=self.__window.documents().document(index)

        if document.modified() and askIfNotSaved:
            # message box to confirm to close document
            if QMessageBox.question(self.__window, "Close document", "Document has been modified without being saved.\n\nClose without saving?", QMessageBox.Yes|QMessageBox.No)==QMessageBox.No:
                return False

        if not document.fileName() is None:
            # save in history when closed as, when opened/save, documents are in
            # cache and automatically opened on next startup
            self.__historyFiles.append(document.fileName())

        return self.__window.documents().closeDocument(index)

    def commandFileReload(self, index=None, askIfNotSaved=True):
        """Reload current document

        If document has been modified, ask confirmation for reload
        """
        if isinstance(index, bool):
            # probably called from menu event
            index=None

        document=self.__window.documents().document(index)

        if document.fileName() is None:
            # no file name, can't be reloaded
            return False

        if document.modified() and askIfNotSaved:
            # message box to confirm to close document
            if QMessageBox.question(self.__window, "Reload document", "Document has been modified and not saved.\n\nReload document?", QMessageBox.Yes|QMessageBox.No)==QMessageBox.No:
                return False

        return self.__window.documents().reloadDocument(index)

    def commandFileCloseAll(self, askIfNotSaved=True):
        """Close all documents

        If document has been modified, ask for: save/don't save/cancel
        """
        defaultChoice=None
        for index in reversed(range(self.__window.documents().count())):
            document=self.__window.documents().document(index)

            closeDocument=True
            if document.modified():
                if defaultChoice is None:
                    self.__window.documents().setCurrentIndex(index)

                    choice=QMessageBox.question(self.__window, "Close document", "Document has been modified without being saved.\n\nClose without saving?", QMessageBox.Yes|QMessageBox.YesToAll|QMessageBox.No|QMessageBox.NoToAll|QMessageBox.Cancel)
                else:
                    choice=defaultChoice


                if choice==QMessageBox.Cancel:
                    # cancel action
                    return
                elif choice==QMessageBox.No:
                    closeDocument=False
                elif choice==QMessageBox.NoToAll:
                    defaultChoice=QMessageBox.No
                elif choice==QMessageBox.YesToAll:
                    defaultChoice=QMessageBox.Yes

            if closeDocument:
                # save in history when closed as, when opened/save, documents are in
                # cache and automatically opened on next startup
                if not document.fileName() is None:
                    self.__historyFiles.append(document.fileName())
                self.__window.documents().closeDocument(index)


    def commandEditUndo(self):
        """Undo last modification on current document"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().document().undo()

    def commandEditRedo(self):
        """Undo undoed modification on current document"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().document().redo()

    def commandEditCut(self):
        """Cut selected text from current document to clipboard"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().cut()

    def commandEditCopy(self):
        """Copy selected text from current document to clipboard"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().copy()

    def commandEditPaste(self):
        """Paste clipboard content to current document"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().paste()

    def commandEditSelectAll(self):
        """Select all document content"""
        if self.__currentDocument:
            self.__currentDocument.codeEditor().selectAll()


    def commandScriptExecute(self):
        """Execute script"""
        if self.__currentDocument:
            self.__interpreter.setOptionVerboseMode(True)

            try:
                returned=self.__interpreter.setScript(self.__currentDocument.codeEditor().toPlainText())
            except Exception as e:
                print("commandScriptExecute/Error", str(e))
                return

            try:
                returned=self.__interpreter.execute()
            except Exception as e:
                print("commandScriptExecute/Error", str(e))
                return

            print('commandScriptExecute', returned)


    def commandScriptBreakPause(self):
        """Made Break/Pause in script execution"""
        print("TODO: implement commandScriptBreakPause")

    def commandScriptStop(self):
        """Stop script execution"""
        print("TODO: implement commandScriptStop")


    def commandLanguageInsert(self, text, setFocus=True):
        """Insert given `text` at current position in document

        If `setFocus` is True, current document got focus
        """
        if self.__currentDocument:
            self.__currentDocument.codeEditor().insertLanguageText(text)
            if setFocus:
                self.__currentDocument.codeEditor().setFocus()


    def commandViewBringToFront(self):
        """Bring main window to front"""
        self.__window.setWindowState( (self.__window.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.__window.activateWindow()

    def commandViewMainSplitterPosition(self, positions=None):
        """Set the mainwindow main splitter position

        Given `positions` is a list [<panel0 size>,<panel1 size>]
        If value is None, will define a default 50%-50%
        """
        if positions is None:
            positions = [1000, 1000]

        if not isinstance(positions, list) or len(positions) != 2:
            raise EInvalidValue('Given `positions` must be a list [l,r]')

        self.__window.splMain.setSizes(positions)

        return positions

    def commandViewSecondarySplitterPosition(self, positions=None):
        """Set the mainwindow secondary splitter position

        Given `positions` is a list [<panel0 size>,<panel1 size>]
        If value is None, will define a default 50%-50%
        """
        if positions is None:
            positions = [700, 300]

        if not isinstance(positions, list) or len(positions) != 2:
            raise EInvalidValue('Given `positions` must be a list [l,r]')

        self.__window.splSecondary.setSizes(positions)

        return positions

    def commandViewMainWindowMaximized(self, maximized=False):
        """Set the window state"""
        if not isinstance(maximized, bool):
            raise EInvalidValue('Given `maximized` must be a <bool>')

        if maximized:
            # store current geometry now because after window is maximized, it's lost
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_WINDOW_GEOMETRY, [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()])
            self.__window.showMaximized()
        else:
            self.__window.showNormal()

        return maximized

    def commandViewMainWindowGeometry(self, geometry=[-1,-1,-1,-1]):
        """Set the window geometry

        Given `geometry` is a list [x,y,width,height] or a QRect()
        """
        if isinstance(geometry, QRect):
            geometry = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]

        if not isinstance(geometry, list) or len(geometry)!=4:
            raise EInvalidValue('Given `geometry` must be a <list[x,y,w,h]>')

        rect = self.__window.geometry()

        if geometry[0] >= 0:
            rect.setX(geometry[0])

        if geometry[1] >= 0:
            rect.setY(geometry[1])

        if geometry[2] >= 0:
            rect.setWidth(geometry[2])

        if geometry[3] >= 0:
            rect.setHeight(geometry[3])

        self.__window.setGeometry(rect)

        return [self.__window.geometry().x(), self.__window.geometry().y(), self.__window.geometry().width(), self.__window.geometry().height()]

    def commandViewShowCanvasVisible(self, visible=None):
        """Display/Hide canvas"""
        if visible is None:
            visible = self.__window.actionViewCanvasShowCanvas.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewCanvasShowCanvas.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        if not visible:
            # when hidden, canvas panel width is set to 0, then save current size now
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_MAIN_POSITION, self.__window.splMain.sizes())

        self.__window.wRightArea.setVisible(visible)

    def commandViewShowCanvasOrigin(self, visible=None):
        """Display/Hide canvas origin"""
        if visible is None:
            visible = self.__window.actionViewCanvasShowCanvasOrigin.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewCanvasShowCanvasOrigin.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_ORIGIN, visible)
        Debug.print('TODO: update canvas (origin)')

    def commandViewShowCanvasGrid(self, visible=None):
        """Display/Hide canvas grid"""
        if visible is None:
            visible = self.__window.actionViewCanvasShowCanvasGrid.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewCanvasShowCanvasGrid.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_GRID, visible)
        Debug.print('TODO: update canvas (grid)')

    def commandViewShowCanvasPosition(self, visible=None):
        """Display/Hide canvas position"""
        if visible is None:
            visible = self.__window.actionViewCanvasShowCanvasPosition.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewCanvasShowCanvasPosition.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        # updated in saveSettings()
        #BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_VIEW_CANVAS_POSITION, visible)
        Debug.print('TODO: update canvas (position)')

    def commandViewShowConsoleVisible(self, visible=None):
        """Display/Hide canvas"""
        if visible is None:
            visible = self.__window.actionViewShowConsole.isChecked()
        elif isinstance(visible, bool):
            self.__window.actionViewShowConsole.setChecked(visible)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

        if not visible:
            # when hidden, canvas panel width is set to 0, then save current size now
            BSSettings.set(BSSettingsKey.SESSION_MAINWINDOW_SPLITTER_SECONDARY_POSITION, self.__window.splSecondary.sizes())

        self.__window.wConsoleArea.setVisible(visible)


    def commandViewDockLangageQuickHelpVisible(self, visible=None):
        """Display/Hide Language Quick Help docker"""
        if visible is None:
            visible = self.__dwLangageQuickHelpAction.isChecked()
        elif not isinstance(visible, bool):
            raise EInvalidValue('Given `visible` must be a <bool>')

        if self.__dwLangageQuickHelp:
            if visible:
                self.__dwLangageQuickHelp.show()
            else:
                self.__dwLangageQuickHelp.hide()
            self.__window.documents().setCompletionHelpEnabled(not visible)

    def commandViewDockLangageReferenceVisible(self, visible=None):
        """Display/Hide Language Quick Help docker"""
        if visible is None:
            visible = self.__dwLangageReferenceAction.isChecked()
        elif not isinstance(visible, bool):
            raise EInvalidValue('Given `visible` must be a <bool>')

        if self.__dwLangageReference:
            if visible:
                self.__dwLangageReference.show()
            else:
                self.__dwLangageReference.hide()



    def commandDockLangageQuickHelpSet(self, keyword):
        """Define language quick help docker content from given `keyword`

        Given `keyword` is a language instruction (like "print", "set variable", ...)
        """
        if self.__dwLangageQuickHelp:
            if '\x01' in keyword:
                keyword=keyword.split('\x01')[0]

            descriptionProposal=self.__languageDef.getTextProposal(keyword, True)

            if len(descriptionProposal)>0:
                # from description, retrieve title, description, example
                title=TokenizerRule.descriptionExtractSection(descriptionProposal[0][2], 'title')
                description=TokenizerRule.descriptionExtractSection(descriptionProposal[0][2], 'description')
                example=TokenizerRule.descriptionExtractSection(descriptionProposal[0][2], 'example')

                self.__dwLangageQuickHelp.set(title, descriptionProposal[0][1], description, example)


    def commandSettingsSaveSessionOnExit(self, saveSession=None):
        """Define if current session properties have to be save or not"""
        if saveSession is None:
            saveSession = self.__window.actionSettingsSaveSessionOnExit.isChecked()
        elif isinstance(saveSession, bool):
            self.__window.actionSettingsSaveSessionOnExit.setChecked(saveSession)
        else:
            raise EInvalidValue('Given `visible` must be a <bool>')

    def commandSettingsSysTrayMode(self, value=BSSysTray.SYSTRAY_MODE_WHENACTIVE):
        """Set mode for systray notifier"""
        BSSettings.set(BSSettingsKey.CONFIG_SYSTRAY_MODE, value)
        self.__systray.setVisibleMode(value)

    def commandSettingsOpenAtStartup(self, value=False):
        """Set option to start BS at Krita's startup"""
        BSSettings.set(BSSettingsKey.CONFIG_OPEN_ATSTARTUP, value)

    def commandSettingsOpen(self):
        """Open dialog box settings"""
        #if BSSettingsDialogBox.open(f'{self.__bsName}::Settings', self):
        #    self.saveSettings()
        print("TODO: implement commandSettingsOpen")


    def commandAboutBs(self):
        """Display 'About Buli Script' dialog box"""
        AboutWindow(self.__bsName, self.__bsVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':BuliScript')

    def commandHelpBs(self, text):
        """Display BuliScript help"""
        print("TODO: implement commandHelpBs")


    # endregion: define commands -----------------------------------------------
