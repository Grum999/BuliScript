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
import uuid
import hashlib

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal,
        QFileSystemWatcher
    )

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )

from .bssettings import (
        BSSettings,
        BSSettingsKey
    )

from buliscript.pktk.modules.utils import Debug
from buliscript.pktk.modules.bytesrw import BytesRW
from buliscript.pktk.widgets.wcodeeditor import WCodeEditor
from buliscript.pktk.widgets.wmsgbuttonbar import (
        WMessageButton,
        WMessageButtonBar
    )




class BSDocument(QWidget):
    """An extension of code editor to get an easier integration in BuliScript user interface"""

    ALERT_FILE_DELETED =    0x01
    ALERT_FILE_MODIFIED =   0x02
    ALERT_FILE_TIMESTAMP =  0x03
    ALERT_FILE_CANTOPEN =   0x04
    ALERT_FILE_CANTSAVE =   0x05

    ACTION_CLOSE =          0x01
    ACTION_SAVE =           0x02
    ACTION_SAVEAS =         0x03
    ACTION_CANCEL =         0x04
    ACTION_RELOAD =         0x05


    def __init__(self, parent=None, languageDef=None, uiController=None):
        super(BSDocument, self).__init__(parent)

        self.__layout=QVBoxLayout(self)
        self.__layout.setContentsMargins(3,3,3,3)

        self.__msgButtonBar=WMessageButtonBar(self)
        self.__codeEditor=WCodeEditor(self, languageDef)

        self.__layout.addWidget(self.__msgButtonBar)
        self.__layout.addWidget(self.__codeEditor)

        self.__msgButtonBar.buttonClicked.connect(self.__msgAlertBtnClicked)


        self.__codeEditor.setLanguageDefinition(languageDef)
        self.__codeEditor.setOptionCommentCharacter('#')
        self.__codeEditor.setOptionMultiLine(True)
        self.__codeEditor.setOptionShowLineNumber(True)
        self.__codeEditor.setOptionAllowWheelSetFontSize(True)


        self.__fsWatcher=QFileSystemWatcher()
        self.__fsWatcher.fileChanged.connect(self.__externalFileModification)

        self.__alerts=[]
        self.__currentAlert=None
        self.__newDocNumber=0
        self.__uiController=uiController
        self.__documentFileName=None
        self.__documentCacheUuid=str(uuid.uuid4())
        self.applySettings()


    def __repr__(self):
        return f"<BSDocument({self.__documentFileName}, {self.modified()})>"

    def __stopWatcher(self):
        """Stop watching file"""
        files=self.__fsWatcher.files()
        if len(files)>0:
            self.__fsWatcher.removePaths(files)

    def __initWatcher(self):
        """Initialise QFileSystemWatcher()"""
        def init():
            self.__stopWatcher()
            if not self.__documentFileName is None:
                self.__fsWatcher.addPath(self.__documentFileName)

        # note:
        #   Some text editor don't save modifications on an existing file but recreate a new one
        #   (then delete+create instead of modify)
        #
        # when file is deleted, watcher stops to watch it (even if recreated)
        # solution is initialise watcher with a few delay (250ms here) to be sure file is
        # watched in this case
        QTimer.singleShot(250, init)

    def __externalFileModification(self, fileName):
        """File has been modified by an external process"""
        Debug.print('[BSDocument.__externalFileModification] File has been modified {0}', fileName)

        if os.path.isfile(fileName):
            self.__addAlert(BSDocument.ALERT_FILE_MODIFIED)
        else:
            self.__addAlert(BSDocument.ALERT_FILE_DELETED)

        # reinitialise watcher to be sure watch is not lost in case file has been deleted/recreated
        self.__initWatcher()

    def __addAlert(self, alertCode):
        """Add alert to list, update alert messages"""
        if alertCode in self.__alerts or self.__currentAlert==alertCode:
            # no need to add same alert more than once
            return

        self.__alerts.append(alertCode)
        self.__updateAlerts()

    def __updateAlerts(self):
        """Update alerts if any"""
        Debug.print('[BSDocument.__updateAlerts] File {0}: {1}', self.__documentFileName, self.__alerts)
        if len(self.__alerts)==0:
            self.__currentAlert=None
            return
        elif not self.__currentAlert is None:
            # if no alerts, or already wait for user action on a previous alert, do nothing
            return
        else:
            # get current alert
            self.__currentAlert=self.__alerts[0]
            # replace it with a waiting action
            # display alert

            if self.__currentAlert==BSDocument.ALERT_FILE_DELETED:
                # document is open in editor, and version on disk has been deleted
                self.setReadOnly(True)
                if self.modified():
                    self.__msgButtonBar.message(i18n('<html><p><b>File has been deleted on disk!</b><br><i>Close document?</i></p></html>'),
                            WMessageButton(i18n('Close'),     BSDocument.ACTION_CLOSE,    i18n('Close current document\nAs file has been deleted on disk, current modified document will be lost')),
                            WMessageButton(i18n('Save'),      BSDocument.ACTION_SAVE,     i18n('Save current modified document using current location')),
                            WMessageButton(i18n('Save as'),   BSDocument.ACTION_SAVEAS,   i18n('Save current modified document using a different location')),
                            WMessageButton(i18n('Cancel'),    BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current modified document opened in editor')),
                        )
                else:
                    self.__msgButtonBar.message(i18n('<html><p><b>File has been deleted on disk!</b><br><i>Close document?</i></p></html>'),
                            WMessageButton(i18n('Close'),     BSDocument.ACTION_CLOSE,    i18n('Close current document\nAs file has been deleted on disk, current content will be lost')),
                            WMessageButton(i18n('Save'),      BSDocument.ACTION_SAVE,     i18n('Save current document using current location')),
                            WMessageButton(i18n('Save as'),   BSDocument.ACTION_SAVEAS,   i18n('Save current document using a different location')),
                            WMessageButton(i18n('Cancel'),    BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor')),
                        )
            elif self.__currentAlert==BSDocument.ALERT_FILE_MODIFIED:
                # document is open in editor, and version on disk has been modified
                self.setReadOnly(True)
                if self.modified():
                    self.__msgButtonBar.message(i18n('<html><p><b>File has been modified on disk!</b><br><i>Reload document?</i></p></html>'),
                            WMessageButton(i18n('Reload'),    BSDocument.ACTION_RELOAD,   i18n('Reload document from disk\nAs your document is modified, current modifications will be lost')),
                            WMessageButton(i18n('Overwrite'), BSDocument.ACTION_SAVE,     i18n('Save current modified document using current location\nModifications made by an external process to file will be lost')),
                            WMessageButton(i18n('Save as'),   BSDocument.ACTION_SAVEAS,   i18n('Save current modified document using a different location')),
                            WMessageButton(i18n('Cancel'),    BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor')),
                        )
                else:
                    self.__msgButtonBar.message(i18n('<html><p><b>File has been modified on disk!</b><br><i>Reload document?</i></p></html>'),
                            WMessageButton(i18n('Reload'),    BSDocument.ACTION_RELOAD,   i18n('Reload document from disk')),
                            WMessageButton(i18n('Overwrite'), BSDocument.ACTION_SAVE,     i18n('Save current document using current location\nModifications made by an external process to file will be lost')),
                            WMessageButton(i18n('Save as'),   BSDocument.ACTION_SAVEAS,   i18n('Save current document using a different location')),
                            WMessageButton(i18n('Cancel'),    BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor'))
                        )
            elif self.__currentAlert==BSDocument.ALERT_FILE_TIMESTAMP:
                # document opened from cache (then from a restore session)
                # cache version is modified ad then there's might be a mismatch between version in editor and version on disk
                self.setReadOnly(True)
                self.__msgButtonBar.message(i18n('<html><p><b>Document has been restored from last session with unsaved modifications, but document on disk has also been modified</b><br><i>Reload document?</i></p></html>'),
                        WMessageButton(i18n('Reload'),        BSDocument.ACTION_RELOAD,   i18n('Reload document from current location\nCurrent modifications will be lost')),
                        WMessageButton(i18n('Overwrite'),     BSDocument.ACTION_SAVE,     i18n('Save current modified document using current location\nModifications applied to file will be lost')),
                        WMessageButton(i18n('Save as'),       BSDocument.ACTION_SAVEAS,   i18n('Save current modified document using a different location')),
                        WMessageButton(i18n('Cancel'),        BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor'))
                    )
            elif self.__currentAlert==BSDocument.ALERT_FILE_CANTOPEN:
                self.setReadOnly(True)
                if os.path.isfile(self.__documentFileName):
                    self.__msgButtonBar.message(i18n('<html><p><b>File can\'t be opened!</b><br><i>Close document?</i></p></html>'),
                            WMessageButton(i18n('Close'),         BSDocument.ACTION_CLOSE,    i18n('Close current document')),
                            WMessageButton(i18n('Cancel'),        BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor'))
                        )
                else:
                    self.__msgButtonBar.message(i18n('<html><p><b>File doesn\'t exists anymore!</b><br><i>Close document?</i></p></html>'),
                            WMessageButton(i18n('Close'),         BSDocument.ACTION_CLOSE,    i18n('Close current document')),
                            WMessageButton(i18n('Cancel'),        BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current document opened in editor'))
                        )
            elif self.__currentAlert==BSDocument.ALERT_FILE_CANTSAVE:
                self.setReadOnly(True)
                self.__msgButtonBar.message(i18n('<html><p><b>File can\'t be saved!</b><br><i>Save document to an another location?</i></p></html>'),
                        WMessageButton(i18n('Save as'),       BSDocument.ACTION_SAVEAS,   i18n('Save current modified document using a different location')),
                        WMessageButton(i18n('Close'),         BSDocument.ACTION_CLOSE,    i18n('Close current modified document\nModifications will be lost')),
                        WMessageButton(i18n('Cancel'),        BSDocument.ACTION_CANCEL,   i18n('Ignore alert and let current modified document opened in editor'))
                    )

    def __msgAlertBtnClicked(self, value):
        """Button from message alert has been clicked

        manage action to execute
        """
        if len(self.__alerts)==0:
            # normally shoulnd't occurs
            self.__currentAlert=None
            return
        elif not self.__currentAlert is None:
            # remove waiting action from alerts
            self.__alerts.pop(0)

            self.setReadOnly(False)

            if value==BSDocument.ACTION_CLOSE:
                # close document, ignore current modifications
                self.__uiController.commandFileClose(askIfNotSaved=False)
            elif value==BSDocument.ACTION_SAVE:
                self.__uiController.commandFileSaveAs(newFileName=self.__documentFileName)
            elif value==BSDocument.ACTION_SAVEAS:
                self.__uiController.commandFileSaveAs()
            elif value==BSDocument.ACTION_CANCEL:
                # do nothing, just hide message
                self.setModified(True)
            elif value==BSDocument.ACTION_RELOAD:
                self.__uiController.commandFileReload(askIfNotSaved=False)
            else:
                # shouldn't occurs
                raise EInvalidValue(f"Unknown action code: {value}")

            self.__currentAlert=None
            self.__updateAlerts()

    def applySettings(self):
        """Apply BuliScript settings on editor"""
        font = QFont()
        font.setFamily(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_FONT_NAME))
        font.setPointSize(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_FONT_SIZE))
        font.setFixedPitch(True)
        self.__codeEditor.setFont(font)

        # TODO: implement color theme...

        self.__codeEditor.setIndentWidth(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_INDENT_WIDTH))
        self.__codeEditor.setOptionShowIndentLevel(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_INDENT_VISIBLE))

        self.__codeEditor.setOptionShowSpaces(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_SPACES_VISIBLE))

        self.__codeEditor.setOptionShowRightLimit(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_VISIBLE))
        self.__codeEditor.setOptionRightLimitPosition(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_WIDTH))

        self.__codeEditor.setOptionAutoCompletion(BSSettings.get(BSSettingsKey.CONFIG_EDITOR_AUTOCOMPLETION_ACTIVE))

    def modified(self):
        """Return if document is modified or not"""
        return self.__codeEditor.document().isModified()

    def setModified(self, value):
        """Set if document is modified or not"""
        return self.__codeEditor.document().setModified(value)

    def readOnly(self):
        """Return if document is in read only mode"""
        return self.__codeEditor.isReadOnly()

    def setReadOnly(self, value):
        """Set if document is in read only mode"""
        self.__codeEditor.setReadOnly(value)

    def close(self):
        """Close document"""
        self.__stopWatcher()
        self.deleteCache()

    def open(self, fileName):
        """Open document from given `fileName`

        If document can't be opened (doesn't exists or no read access) return False
        otherwise returns True
        """
        try:
            self.__documentFileName=fileName
            with open(self.__documentFileName, "r") as fHandle:
                self.__codeEditor.setPlainText(fHandle.read())
            self.setModified(False)
            self.__initWatcher()
        except Exception as e:
            self.__addAlert(BSDocument.ALERT_FILE_CANTOPEN)
            Debug.print('[BSDocument.open] unable to open file {0}: {1}', fileName, str(e))
            return False

        return True

    def reload(self):
        """Open document from given `fileName`

        If document can't be opened (doesn't exists or no read access) return False
        otherwise returns True
        """
        if self.__documentFileName is None:
            return

        return self.open(self.__documentFileName)

    def save(self, forceSave=False):
        """Save document

        If document don't have fileName, return False (ie: the saveAs() must be explicitely called)
        If document can't be saved, raise an exception
        """
        if self.__documentFileName is None:
            return False

        if self.modified() or forceSave:
            # save only if has been modified
            try:
                self.__stopWatcher()
                with open(self.__documentFileName, "w") as fHandle:
                    fHandle.write(self.__codeEditor.toPlainText())
                self.setModified(False)
                self.__initWatcher()
            except Exception as e:
                self.__addAlert(BSDocument.ALERT_FILE_CANTSAVE)
                Debug.print('[BSDocument.save] unable to save file {0}: {1}', self.__documentFileName, str(e))
                return False

        return True

    def saveAs(self, fileName):
        """Save document with given `fileName`

        If document can't be saved, raise an exception (and fileName is not modified!)
        """
        # save only if has been modified
        try:
            self.__stopWatcher()
            with open(fileName, "w") as fHandle:
                fHandle.write(self.__codeEditor.toPlainText())
            self.setModified(False)
            self.__documentFileName=fileName
            self.__newDocNumber=0
            self.__initWatcher()
        except Exception as e:
            self.__addAlert(BSDocument.ALERT_FILE_CANTSAVE)
            Debug.print('[BSDocument.saveAs] unable to save file {0}: {1}', self.__documentFileName, str(e))
            return False

        return True

    def fileName(self):
        """Return document file name, or None if not yet defined"""
        return self.__documentFileName

    def cacheFileName(self):
        """Return document file name from cache"""
        return os.path.join(self.__uiController.cachePath('documents'), self.__documentCacheUuid)

    def cacheUuid(self):
        """Return document uuid"""
        return self.__documentCacheUuid

    def saveCache(self, stopWatch=True):
        """Save current content to cache

        If document is in modified state, doesn't flag to unmodified

        A cache file is made of:
            Flags
            0000 0000 0000 0001: document has a selection
            0000 0000 0000 0010: document is modified
            0000 0000 0000 0100: document have a file name

            . a UInt2 integer (version)
            . a UInt2 integer (contains flags)
            . a UInt2 integer (contains new document number)
            . a UInt4 integer (contains selection position start, from cursor in document)
            . a UInt4 integer (contains selection position end, from cursor in document; 0 if no selection)
            . a PStr2 string (contains full path/name of original document, empty if none)
            . a Float8 timestamp (contain timestamp of last file modification, 0 if no file)
            . a PStr4 string (contains document content, empty id not modified)
        """
        if stopWatch:
            self.__stopWatcher()

        cursor = self.__codeEditor.textCursor()
        dataWrite=BytesRW()


        flags=0x00

        if cursor.selectionStart()!=cursor.selectionEnd():
            flags|=0b00000001

        if self.modified():
            flags|=0b00000010

        if not (self.__documentFileName is None or self.__documentFileName==''):
            flags|=0b00000100

        dataWrite.writeUInt2(0x01)
        dataWrite.writeUInt2(flags)
        dataWrite.writeUInt2(self.__newDocNumber)

        if cursor.selectionStart()==cursor.selectionEnd():
            dataWrite.writeUInt4(cursor.position())
            dataWrite.writeUInt4(0)
        else:
            dataWrite.writeUInt4(cursor.selectionStart())
            dataWrite.writeUInt4(cursor.selectionEnd())

        if not (self.__documentFileName is None or self.__documentFileName==''):
            dataWrite.writePStr2(self.__documentFileName)
            if os.path.isfile(self.__documentFileName):
                dataWrite.writeFloat8(os.path.getmtime(self.__documentFileName))
            else:
                dataWrite.writeFloat8(0.0)
        else:
            dataWrite.writePStr2('')
            dataWrite.writeFloat8(0.0)

        if self.modified():
            dataWrite.writePStr4(self.__codeEditor.toPlainText())
        else:
            dataWrite.writePStr4('')

        try:
            with open(self.cacheFileName(), "wb") as fHandle:
                fHandle.write(dataWrite.getvalue())
            dataWrite.close()
        except Exception as e:
            Debug.print('[BSDocument.saveCache] unable to save file {0}: {1}', self.cacheFileName(), str(e))
            if dataWrite:
                dataWrite.close()
            return False

        return True

    def openCache(self, uuid):
        """Open content from cache

        Force to modified when opened
        """
        self.__documentCacheUuid=uuid

        try:
            dataRead=None
            with open(self.cacheFileName(), "rb") as fHandle:
                dataRead=BytesRW(fHandle.read())
        except Exception as e:
            Debug.print('[BSDocument.openCache] unable to open file {0}: {1}', self.cacheFileName(), str(e))
            if dataRead:
                dataRead.close()
            return False

        # version, ignore it
        dataRead.readUInt2()

        flags=dataRead.readUInt2()
        newDocNumber=dataRead.readUInt2()

        cursorSelStart=dataRead.readUInt4()
        cursorSelEnd=dataRead.readUInt4()

        fullPathFileName=dataRead.readPStr2()
        timestamp=dataRead.readFloat8()
        docContent=dataRead.readPStr4()

        dataRead.close()


        if flags&0b00000100==0b00000100 and fullPathFileName!='':
            # file name provided, read file content
            newDocNumber=0
            if not self.open(fullPathFileName):
                # force document to keep file name
                self.__documentFileName=fullPathFileName
                # alert already defined by open() method, so none to add here
            else:
                if os.path.getmtime(self.__documentFileName)!=timestamp:
                    self.__addAlert(BSDocument.ALERT_FILE_TIMESTAMP)

        self.__newDocNumber=newDocNumber

        if flags&0b00000010==0b00000010:
            # document has been modified
            # apply last modified version
            # => can't use setPlainText() as it clear undo/redo stack
            #self.setPlainText(docContent)
            #self.setModified(True)
            cursor=self.__codeEditor.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.insertText(docContent)

        # manage cursor position
        cursor=self.__codeEditor.textCursor()
        cursor.setPosition(cursorSelStart, QTextCursor.MoveAnchor)
        if flags&0b00000001==0b00000001:
            # there a selection, go selection end
            cursor.setPosition(cursorSelEnd, QTextCursor.KeepAnchor)
        self.__codeEditor.setTextCursor(cursor)

        self.__updateAlerts()
        return True

    def deleteCache(self):
        """Delete cache file, if exists"""
        fileName=self.cacheFileName()
        if os.path.isfile(fileName):
            try:
                os.remove(fileName)
            except Exception as e:
                pass

    def newDocNumber(self):
        """Return document number

        =0: document has been opened from a file
        >0: document is a new created document
        """
        return self.__newDocNumber

    def setNewDocNumber(self, number):
        """Set document number """
        self.__newDocNumber=number

    def codeEditor(self):
        """Return codeEditor instance"""
        return self.__codeEditor



class BSDocuments(QTabWidget):
    """<Super lazy mode>
    Yes, I used a QTabWidget to write the document manager ^_^'

    Ideally I suppose writing a non widget class, connected to a widget might be
    a better solution, but I decided to use the easy way
    </Super lazy mode>

    The BSDocuments manage documents:
    - open
    - close
    - saved/unsaved
    - ...
    """
    documentChanged=Signal(BSDocument)

    def __init__(self, parent=None):
        super(BSDocuments, self).__init__(parent)

        # use a customized QTabBar, to display unsaved document differently than
        # saved documents
        self.__tabBar=BSDocumentsTabBar(self)
        self.setTabBar(self.__tabBar)

        self.__counterNewDocument=0
        self.__documents=[]
        self.__mainWindow=None
        self.__uiController=None

        self.__currentDocument=None

        self.currentChanged.connect(self.__tabChanged)
        self.tabCloseRequested.connect(self.__tabRequestClose)

    def __updateStatusBarOverwrite(self, dummy=None):
        """Update status bar STATUSBAR_INSOVR_MODE"""
        if self.__currentDocument.codeEditor().overwriteMode():
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_INSOVR_MODE, 'OVR')
        else:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_INSOVR_MODE, 'INS')

    def __updateStatusBarCursor(self, v1=None, v2=None, v3=None):
        """Update status bar STATUSBAR_ROW, STATUSBAR_COLUMN, STATUSBAR_SELECTION"""
        position=self.__currentDocument.codeEditor().cursorPosition()
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_ROWS, self.__currentDocument.codeEditor().blockCount())
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_POS, f'{position[0].x()}:{position[0].y()}')

        if position[3]==0:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_SELECTION, '')
        else:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_SELECTION, f'{position[1].x()}:{position[1].y()} - {position[2].x()}:{position[2].y()} [{position[3]}]')

    def __updateStatusBarFileName(self):
        """Update status bar STATUSBAR_FILENAME"""
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_FILENAME, self.__documentTabName(self.__currentDocument, True))

    def __updateStatusBarReadOnly(self, index=None):
        """Update status bar STATUSBAR_RO"""
        if self.__currentDocument.readOnly():
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_RO, 'RO')
        else:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_RO, '')

    def __updateTabBarModified(self, index=None):
        """Update tab bar for current document, taking in account modification status"""

        if index is None or isinstance(index, bool):
            document=self.__currentDocument
            index=self.currentIndex()
        else:
            document=self.document(index)

        self.__tabBar.setTabData(index, document.modified())
        self.__tabBar.update()

    def __documentTabName(self, document, full=False):
        """Return expected name to apply to tab for given `document`

        - File name (without path) if available
        - "<New document X>" otherwise
        """
        fileName=document.fileName()
        if fileName is None:
            return f"<New document {document.newDocNumber()}>"
        elif full:
            return fileName
        else:
            return os.path.basename(fileName)

    def __addDocument(self, document, counterNewDocument=0):
        """Add a tab for document"""
        self.__documents.append(document)
        document.setNewDocNumber(counterNewDocument)
        newTabIndex=self.addTab(document, self.__documentTabName(document))

        # set document as "unmodified" state
        self.__updateTabBarModified(newTabIndex)

        document.codeEditor().readOnlyModeChanged.connect(self.__updateStatusBarReadOnly)
        document.codeEditor().overwriteModeChanged.connect(self.__updateStatusBarOverwrite)
        document.codeEditor().cursorCoordinatesChanged.connect(self.__updateStatusBarCursor)
        document.codeEditor().modificationChanged.connect(self.__updateTabBarModified)
        document.codeEditor().modificationChanged.connect(self.__uiController.updateMenu)

        # switch to new opened/created document
        self.setCurrentIndex(newTabIndex)

    def __tabChanged(self, index):
        """Active tab has been changed"""
        if index==-1:
            return
        self.__currentDocument=self.document(index)
        self.__updateStatusBarFileName()
        self.__updateStatusBarReadOnly()
        self.__updateStatusBarOverwrite()
        self.__updateStatusBarCursor()
        self.__currentDocument.setFocus(Qt.OtherFocusReason)
        self.documentChanged.emit(self.__currentDocument)

    def __tabRequestClose(self, index):
        """Trying to close a document"""
        self.__uiController.commandFileClose(index)

    def initialise(self, mainWindow, uiController):
        """Define mainwindow on which documents manager is connected on
        Also define uiController
        """
        self.__counterNewDocument=0
        self.__mainWindow=mainWindow
        self.__uiController=uiController

        openedDocumentsFileName=BSSettings.get(BSSettingsKey.SESSION_DOCUMENTS_OPENED)
        for fileName in openedDocumentsFileName:
            self.openDocument(fileName)
            document=self.document()

            if document and document.newDocNumber()>self.__counterNewDocument:
                self.__counterNewDocument=document.newDocNumber()

        if len(self.__documents)==0:
            # if no document opened (from previous session) then automatically create a new one
            # (always have a document)
            self.newDocument()

    def updateSettings(self):
        """Settings has been modified, update documents according to settings"""
        if not isinstance(settings, BSSettings):
            raise EInvalidType('Given `settings` must be <BSSettings>')

        for document in self.__documents:
            document.applySettings()

    def documents(self):
        """Return a list of BSDocument

        => Index in list match with tab position
        """
        return [self.widget(index) for index in range(self.count())]

    def document(self, index=None):
        """Return document from index

        If `index` is None, return current document
        """
        if index is None:
            return self.currentWidget()
        elif index >=0 and index < self.count():
            return self.widget(index)
        else:
            raise EInvalidValue(f'Given `index` is not valid: {index}')

    def newDocument(self):
        """Create a new empty document

        - New tab
        - New BSDocument
        """
        self.__counterNewDocument+=1

        document=BSDocument(None, self.__uiController.languageDef(), self.__uiController)
        self.__addDocument(document, self.__counterNewDocument)
        return True

    def openDocument(self, fileName):
        """open a document from given `fileName`

        if `fileName` start with a "@" file is opened as a cache file

        - New tab
        - New BSDocument

        Return False if document can't be opened
        Return True if document has been opened OR is already opened
        """
        fromCache=False
        if result:=re.match('@(.*)',fileName):
            fileName=result.groups()[0]
            fromCache=True

        if not fromCache:
            for document in self.__documents:
                if fileName==document.fileName():
                    # document is already opened, just switch to matching tab
                    self.setCurrentIndex(self.indexOf(document))
                    return True

        document=BSDocument(None, self.__uiController.languageDef(), self.__uiController)

        if fromCache:
            opened=document.openCache(fileName)
        else:
            opened=document.open(fileName)

        if opened:
            # Document has been opened, add a new tab
            self.__addDocument(document, document.newDocNumber())
            return True
        else:
            # unable to open document
            return False

    def reloadDocument(self, index=None):
        """reload content of opened document defined by given `index`

        If `index` is None, reload current document

        If can't reload (ie: a new document never saved), does nothing
        """
        if index is None:
            index=self.currentIndex()
            document=self.__currentDocument
        else:
            document=self.document(index)

        if document.fileName() is None:
            return False

        returned=document.reload()

        if returned:
            self.__updateStatusBarFileName()
            self.__updateTabBarModified(index)
            self.setTabText(index, self.__documentTabName(document))
        return returned

    def closeDocument(self, index=None):
        """Close document defined by given `index`

        If `index` is None, close current document
        """
        if index is None:
            index=self.currentIndex()
            document=self.__currentDocument
        else:
            document=self.document(index)

        document.close()
        self.removeTab(index)
        self.__documents.pop(index)

        if len(self.__documents)==0:
            self.__counterNewDocument=0
            self.newDocument()

        return True

    def saveDocument(self, index=None, fileName=None):
        """Save document defined by given `index`

        If `index` is None, save current document
        """
        if index is None:
            document=self.__currentDocument
            index=self.currentIndex()
        else:
            document=self.document(index)

        if fileName is None:
            # no file name provided
            # save document, considering a name is already defined on document
            returned=document.save()
        else:
            returned=document.saveAs(fileName)

        if returned:
            self.__updateStatusBarFileName()
            self.__updateTabBarModified(index)
            self.setTabText(index, self.__documentTabName(document))
        return returned



class BSDocumentsTabBar(QTabBar):
    """Implement a tabbar that let possibility in code editor to made distinction
    between saved and unsaved document (ie: customized tab content)

    Also, close button is not visible by default and displayed only when mouse is
    over tab

    Implementation made from solution found here: https://stackoverflow.com/a/64346097
    """
    class MovingTab(QWidget):
        """A private QWidget that paints the current moving tab"""
        def setPixmap(self, pixmap):
            self.pixmap = pixmap
            self.update()

        def paintEvent(self, event):
            qp = QPainter(self)
            qp.drawPixmap(0, 0, self.pixmap)

    def __init__(self,parent, *args, **kwargs):
        QTabBar.__init__(self,parent, *args, **kwargs)
        self.__movingTab = None
        self.__isMoving = False
        self.__pressedIndex = -1
        self.__overIndex=-1
        self.setMouseTracking(True)

    def __drawTab(self, painter, index, tabOption, forPixmap=False):
        """Draw tab according to current state

        tabData=True => unsaved
        """
        if self.tabData(index)==True:
            # set font bold as bold for unsaved tab
            font=painter.font()
            font.setBold(True)
            painter.setFont(font)

        painter.drawControl(QStyle.CE_TabBarTab, tabOption)

        if self.tabData(index)==True:
            # draw bullet
            painter.setRenderHint(QPainter.Antialiasing)

            rect=self.tabRect(index)
            text=self.tabText(index)

            bRadius=rect.height()/8


            closeButton=self.tabButton(index, QTabBar.RightSide)
            if closeButton:
                if closeButton.isVisible():
                    return

                oX=rect.x()
                rect=closeButton.rect()
                pos=closeButton.pos()

                pX=pos.x() + rect.width()/2
                pY=pos.y() + rect.height()/2

                if forPixmap:
                    pX-=oX
            else:
                # should not occurs, but as a workaround solution if occurs ^_^''
                pX=rect.x() + painter.fontMetrics().boundingRect(text).width()
                pY=rect.y() + rect.height()/2

            painter.setPen(QPen(Qt.transparent))
            painter.setBrush(QBrush(self.palette().highlight().color()))

            painter.drawEllipse(QPointF(pX, pY), bRadius, bRadius)


    def tabInserted(self, index):
        """When a new tab is inserted, hide close button"""
        closeButton=self.tabButton(index, QTabBar.RightSide)
        if closeButton:
            closeButton.hide()

    def isVertical(self):
        """Return if tabs are in vertical mode"""
        return self.shape() in (
            self.RoundedWest,
            self.RoundedEast,
            self.TriangularWest,
            self.TriangularEast)

    def layoutTab(self, overIndex):
        oldIndex = self.__pressedIndex
        self.__pressedIndex = overIndex
        self.moveTab(oldIndex, overIndex)

    def finishedMovingTab(self):
        """Once tab is moved, reset references on tab"""
        self.__movingTab.hide()
        self.__movingTab.deleteLater()
        self.__movingTab = None
        self.__pressedIndex = -1
        self.update()

    def mousePressEvent(self, event):
        """Start to move, get current tab under mouse cursor"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            # left button, start "drag"
            self.__pressedIndex = self.tabAt(event.pos())
            if self.__pressedIndex < 0:
                return
            self.startPos = event.pos()

    def mouseMoveEvent(self,event):
        if not event.buttons() & Qt.LeftButton or self.__pressedIndex < 0:
            # not moving a tab
            super().mouseMoveEvent(event)

            overIndex=self.tabAt(event.pos())

            if overIndex!=self.__overIndex:
                # over another tab
                if self.__overIndex!=-1:
                    # hide button for previous tab, if any
                    closeButton=self.tabButton(self.__overIndex, QTabBar.RightSide)
                    closeButton.hide()

                if overIndex!=-1:
                    # show button for current tab, if any
                    closeButton=self.tabButton(overIndex, QTabBar.RightSide)
                    closeButton.show()

                self.__overIndex=overIndex
        else:
            if not self.__isMoving:
                closeButton=self.tabButton(self.__pressedIndex, QTabBar.RightSide)
                closeButton.hide()

            delta = event.pos() - self.startPos
            if not self.__isMoving and delta.manhattanLength() < QApplication.startDragDistance():
                # ignore the movement as it's too small to be considered a drag
                return

            if not self.__movingTab:
                # create a private widget that appears as the current (moving) tab
                tabRect = self.tabRect(self.__pressedIndex)
                overlap = self.style().pixelMetric(QStyle.PM_TabBarTabOverlap, None, self)

                tabRect.adjust(-overlap, 0, overlap, 0)

                # create pixmap used while moving
                pm = QPixmap(tabRect.size())
                pm.fill(Qt.transparent)

                qp = QStylePainter(pm, self)
                opt = QStyleOptionTab()
                self.initStyleOption(opt, self.__pressedIndex)
                if self.isVertical():
                    opt.rect.moveTopLeft(QPoint(0, overlap))
                else:
                    opt.rect.moveTopLeft(QPoint(overlap, 0))
                opt.position = opt.OnlyOneTab

                self.__drawTab(qp, self.__pressedIndex, opt, True)
                qp.end()

                self.__movingTab = self.MovingTab(self)
                self.__movingTab.setPixmap(pm)
                self.__movingTab.setGeometry(tabRect)
                self.__movingTab.show()


            self.__isMoving = True


            self.startPos = event.pos()
            isVertical = self.isVertical()
            startRect = self.tabRect(self.__pressedIndex)
            if isVertical:
                delta = delta.y()
                translate = QPoint(0, delta)
                startRect.moveTop(startRect.y() + delta)
            else:
                delta = delta.x()
                translate = QPoint(delta, 0)
                startRect.moveLeft(startRect.x() + delta)

            movingRect = self.__movingTab.geometry()
            movingRect.translate(translate)
            self.__movingTab.setGeometry(movingRect)

            if delta < 0:
                overIndex = self.tabAt(startRect.topLeft())
            else:
                if isVertical:
                    overIndex = self.tabAt(startRect.bottomLeft())
                else:
                    overIndex = self.tabAt(startRect.topRight())
            if overIndex < 0:
                return

            # if the target tab is valid, move the current whenever its position
            # is over the half of its size
            overRect = self.tabRect(overIndex)
            if isVertical:
                if ((overIndex < self.__pressedIndex and movingRect.top() < overRect.center().y()) or
                    (overIndex > self.__pressedIndex and movingRect.bottom() > overRect.center().y())):
                        self.layoutTab(overIndex)
            elif ((overIndex < self.__pressedIndex and movingRect.left() < overRect.center().x()) or
                (overIndex > self.__pressedIndex and movingRect.right() > overRect.center().x())):
                    self.layoutTab(overIndex)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        if self.__movingTab:
            self.finishedMovingTab()
        else:
            self.__pressedIndex = -1
        self.__isMoving = False
        self.update()

    def leaveEvent(self,event):
        if self.__overIndex!=-1:
            closeButton=self.tabButton(self.__overIndex, QTabBar.RightSide)
            if closeButton:
                closeButton.hide()
            self.__overIndex=-1

    def paintEvent(self, event):
        painter = QStylePainter(self)
        tabOption = QStyleOptionTab()
        for index in range(self.count()):

            if index == self.__pressedIndex and self.__isMoving:
                continue
            self.initStyleOption(tabOption, index)

            painter.save()
            self.__drawTab(painter, index, tabOption)
            painter.restore()

Debug.setEnabled(True)
