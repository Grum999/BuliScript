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
        pyqtSignal
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




class BSDocument(WCodeEditor):
    """An extension of code editor to get an easier integration in BuliScript user interface"""

    def __init__(self, parent=None, languageDef=None, uiController=None):
        super(BSDocument, self).__init__(parent, languageDef)

        self.setLanguageDefinition(languageDef)
        self.setOptionCommentCharacter('#')
        self.setOptionMultiLine(True)
        self.setOptionShowLineNumber(True)
        self.setOptionAllowWheelSetFontSize(True)

        self.__newDocNumber=0
        self.__uiController=uiController
        self.__documentFileName=None
        self.__documentCacheUuid=str(uuid.uuid4())
        self.applySettings(self.__uiController.settings())

    def __repr__(self):
        return f"<BSDocument({self.__documentFileName}, {self.modified()})>"

    def applySettings(self, settings):
        """Apply BuliScript settings on editor"""
        if not isinstance(settings, BSSettings):
            raise EInvalidType('Given `settings` must be <BSSettings>')

        font = QFont()
        font.setFamily(settings.option(BSSettingsKey.CONFIG_EDITOR_FONT_NAME))
        font.setPointSize(settings.option(BSSettingsKey.CONFIG_EDITOR_FONT_SIZE))
        font.setFixedPitch(True)
        self.setFont(font)

        # TODO: implement color theme...

        self.setIndentWidth(settings.option(BSSettingsKey.CONFIG_EDITOR_INDENT_WIDTH))
        self.setOptionShowIndentLevel(settings.option(BSSettingsKey.CONFIG_EDITOR_INDENT_VISIBLE))

        self.setOptionShowSpaces(settings.option(BSSettingsKey.CONFIG_EDITOR_SPACES_VISIBLE))

        self.setOptionShowRightLimit(settings.option(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_VISIBLE))
        self.setOptionRightLimitPosition(settings.option(BSSettingsKey.CONFIG_EDITOR_RIGHTLIMIT_WIDTH))

        self.setOptionAutoCompletion(settings.option(BSSettingsKey.CONFIG_EDITOR_AUTOCOMPLETION_ACTIVE))

    def modified(self):
        """Return if document is modified or not"""
        return self.document().isModified()

    def setModified(self, value):
        """Set if document is modified or not"""
        return self.document().setModified(value)

    def open(self, fileName):
        """Open document from given `fileName`

        If document can't be opened (doesn't exists or no read access) return False
        otherwise returns True
        """
        try:
            with open(fileName, "r") as fHandle:
                self.setPlainText(fHandle.read())
        except Exception as e:
            Debug.print('[BSDocument.open] unable to save file {0}: {1}', fileName, str(e))
            return False

        self.__documentFileName=fileName
        self.setModified(False)
        return True

    def save(self):
        """Save document

        If document don't have fileName, return False (ie: the saveAs() must be explicitely called)
        If document can't be saved, raise an exception
        """
        if self.__documentFileName is None:
            return False

        if self.modified():
            # save only if has been modified
            try:
                with open(self.__documentFileName, "w") as fHandle:
                    fHandle.write(self.toPlainText())
                    self.setModified(False)
            except Exception as e:
                Debug.print('[BSDocument.save] unable to save file {0}: {1}', self.__documentFileName, str(e))
                return False

        return True

    def saveAs(self, fileName):
        """Save document with given `fileName`

        If document can't be saved, raise an exception (and fileName is not modified!)
        """
        if self.modified():
            # save only if has been modified
            try:
                with open(fileName, "w") as fHandle:
                    fHandle.write(self.toPlainText())
                    self.setModified(False)
                    self.__documentFileName=fileName
                    self.__newDocNumber=0
            except Exception as e:
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

    def saveCache(self):
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
            . a PStr4 string (contains document content, empty id not modified)
        """
        cursor = self.textCursor()
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
        else:
            dataWrite.writePStr2('')

        if self.modified():
            dataWrite.writePStr4(self.toPlainText())
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
        docContent=dataRead.readPStr4()

        dataRead.close()


        if flags&0b00000100==0b00000100:
            # file name provided, read file content
            newDocNumber=0
            if not self.open(fullPathFileName):
                # force document to keep file name
                self.__documentFileName=fullPathFileName

        self.__newDocNumber=newDocNumber

        if flags&0b00000010==0b00000010:
            # document has been modified
            # apply last modified version
            # => can't use setPlainText() as it clear undo/redo stack
            #self.setPlainText(docContent)
            #self.setModified(True)
            cursor=self.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.insertText(docContent)

        # manage cursor position
        cursor=self.textCursor()
        cursor.setPosition(cursorSelStart, QTextCursor.MoveAnchor)
        if flags&0b00000001==0b00000001:
            # there a selection, go selection end
            cursor.setPosition(cursorSelEnd, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
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
        if self.__currentDocument.overwriteMode():
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_INSOVR_MODE, 'OVR')
        else:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_INSOVR_MODE, 'INS')

    def __updateStatusBarCursor(self, v1=None, v2=None, v3=None):
        """Update status bar STATUSBAR_ROW, STATUSBAR_COLUMN, STATUSBAR_SELECTION"""
        position=self.__currentDocument.cursorPosition()
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_ROWS, self.__currentDocument.blockCount())
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_POS, f'{position[0].x()}:{position[0].y()}')

        if position[3]==0:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_SELECTION, '')
        else:
            self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_SELECTION, f'{position[1].x()}:{position[1].y()} - {position[2].x()}:{position[2].y()} [{position[3]}]')

    def __updateStatusBarFileName(self):
        """Update status bar STATUSBAR_FILENAME"""
        self.__mainWindow.setStatusBarText(self.__mainWindow.STATUSBAR_FILENAME, self.__documentTabName(self.__currentDocument))

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

        print("__addDocument", document, counterNewDocument)
        # set document as "unmodified" state
        self.__updateTabBarModified(newTabIndex)

        document.overwriteModeChanged.connect(self.__updateStatusBarOverwrite)
        document.cursorCoordinatesChanged.connect(self.__updateStatusBarCursor)
        document.modificationChanged.connect(self.__updateTabBarModified)

        # switch to new opened/created document
        self.setCurrentIndex(newTabIndex)

    def __tabChanged(self, index):
        """Active tab has been changed"""
        if index==-1:
            return
        self.__currentDocument=self.document(index)
        self.__updateStatusBarFileName()
        self.__updateStatusBarOverwrite()
        self.__updateStatusBarCursor()
        self.__currentDocument.setFocus(Qt.OtherFocusReason)

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

        openedDocumentsFileName=self.__uiController.settings().option(BSSettingsKey.SESSION_DOCUMENTS_OPENED)
        for fileName in openedDocumentsFileName:
            self.openDocument(fileName)
            document=self.document()

            if document.newDocNumber()>self.__counterNewDocument:
                self.__counterNewDocument=document.newDocNumber()

        if len(self.__documents)==0:
            # if no document opened (from previous session) then automatically create a new one
            # (always have a document)
            self.newDocument()

    def updateSettings(self):
        """Settings has been modified, update documents according to settings"""
        if not isinstance(settings, BSSettings):
            raise EInvalidType('Given `settings` must be <BSSettings>')

        settings=self.__uiController.settings()
        for document in self.__documents:
            document.applySettings(settings)

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

    def closeDocument(self, index=None):
        """Close document defined by given `index`

        If `index` is None, close current document
        """
        if index is None:
            index=self.currentIndex()
            document=self.__currentDocument
        else:
            document=self.document(index)

        document.deleteCache()
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

    def saveAllDocuments(self):
        """Save all documents"""
        print('saveAllDocuments')

    def closeAllDocuments(self):
        """Close all documents"""
        print('closeAllDocuments')



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
