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


# From Qt documentation example "Code Editor"
#  https://doc.qt.io/qtforpython-5.12/overviews/qtwidgets-widgets-codeeditor-example.html

from math import ceil
import re

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget,
        QPlainTextEdit
    )
from .bssyntaxhighlighter import BSSyntaxHighlighter
from .bslanguagedef import (
        BSLanguageDef,
        BSTokenFamily
    )

from ..pktk.pktk import EInvalidType
from ..pktk.pktk import EInvalidValue


class BSColorProp:
    """Color properties"""
    def __init__(self, foreground, background):
        self.__foreground=foreground
        self.__background=background

    def background(self):
        return self.__background

    def foreground(self):
        return self.__foreground


class BSWCodeEditor(QPlainTextEdit):
    """Extended editor with syntax highlighting, autocompletion, line nubmer"""

    KEY_INDENT = 'indent'
    KEY_DEDENT = 'dedent'
    KEY_TOGGLE_COMMENT = 'toggleComment'
    KEY_AUTOINDENT = 'autoIndent'
    KEY_COMPLETION = 'completion'

    CTRL_KEY_TRUE = True
    CTRL_KEY_FALSE = False

    def __init__(self, parent=None):
        super(BSWCodeEditor, self).__init__(parent)

        self.__languageDef = BSLanguageDef()
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # ---- options ----
        # > TODO: need to define setters/getters

        # Gutter colors
        # maybe font size/family/style can be modified
        self.__optionGutterText=QTextCharFormat()
        self.__optionGutterText.setForeground(QColor('#4c5363'))
        self.__optionGutterText.setBackground(QColor('#282c34'))

        # editor current's selected line
        self.__optionColorHighlightedLine=QColor('#2d323c')

        # space indent width
        self.__optionIndentWidth=4

        # right limit properties
        self.__optionRightLimitVisible=True
        self.__optionRightLimitPosition=80
        self.__optionRightLimitColor=QColor('#88555555')

        # spaces properties
        self.__optionSpacesVisible=True
        self.__optionSpacesColor=QColor("#88666666")

        # autocompletion is automatic (True) or manual (False)
        self.__optionAutoCompletion = True

        self.__shortCuts={
            Qt.Key_Tab: {
                    BSWCodeEditor.CTRL_KEY_FALSE: BSWCodeEditor.KEY_INDENT
                },
            Qt.Key_Backtab: {
                    # SHIFT+TAB = BACKTAB
                    BSWCodeEditor.CTRL_KEY_FALSE: BSWCodeEditor.KEY_DEDENT
                },
            Qt.Key_Slash: {
                    BSWCodeEditor.CTRL_KEY_TRUE: BSWCodeEditor.KEY_TOGGLE_COMMENT
                },
            Qt.Key_Return: {
                    BSWCodeEditor.CTRL_KEY_FALSE: BSWCodeEditor.KEY_AUTOINDENT
                },
            Qt.Key_Space: {
                    BSWCodeEditor.CTRL_KEY_TRUE: BSWCodeEditor.KEY_COMPLETION
                }
        }


        # ---- Set default font (monospace, 10pt)
        font = QFont()
        font.setFamily("Monospace")
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)

        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Base, QColor('#282c34'))
        palette.setColor(QPalette.Inactive, QPalette.Base, QColor('#282c34'))

        # ---- instanciate line number area
        self.__lineNumberArea = BSWLineNumberArea(self)

        # ---- initialise signals
        self.blockCountChanged.connect(self.__updateLineNumberAreaWidth)
        self.updateRequest.connect(self.__updateLineNumberArea)
        self.cursorPositionChanged.connect(self.__highlightCurrentLine)
        self.customContextMenuRequested.connect(self.__contextMenu)

        # ---- initialise completion list model
        self.__completerModel = BSWCodeEditorCompleterModel()

        # set dictionary
        for rule in self.__languageDef.tokenizer().rules():
            for text in rule.readableTextList():
                self.__completerModel.add(text, rule.family(),  self.__languageDef.style(rule))
        self.__completerModel.sort()

        # ---- initialise completer
        self.__completer = QCompleter()
        self.__completer.setModel(self.__completerModel)
        self.__completer.setWidget(self)
        self.__completer.setCompletionColumn(0)
        self.__completer.setCompletionRole(Qt.DisplayRole)
        self.__completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.__completer.setCompletionMode(QCompleter.PopupCompletion)
        self.__completer.activated.connect(self.__insertCompletion)

        # ---- initialise customized item rendering for completer
        delegate=BSWCodeEditorCompleterView(self)
        self.__completer.popup().setFont(font)
        self.__completer.popup().setItemDelegate(delegate)

        # ---- initialise highlighter for editor
        self.__highlighter = BSSyntaxHighlighter(self.document(), self.__languageDef, self)

        # default values
        self.__updateLineNumberAreaWidth()
        self.__highlightCurrentLine()


    def __insertCompletion(self, completion):
        """Text selected from completion list, insert it at cursor's place"""
        cursor = self.textCursor()
        extra = (len(completion) - len(self.__completer.completionPrefix()))
        cursor.movePosition(QTextCursor.Left)
        cursor.movePosition(QTextCursor.EndOfWord)
        cursor.insertText(completion[-extra:])
        self.setTextCursor(cursor)


    def __contextMenu(self):
        """Extend default context menu for editor"""
        standardMenu = self.createStandardContextMenu()

        #standardMenu.addSeparator()
        #standardMenu.addAction(u'Test', self.doAction)

        standardMenu.exec(QCursor.pos())


    def __updateLineNumberAreaWidth(self, dummy=None):
        """Called on signal blockCountChanged()

        Update viewport margins, taking in account (new) total number of lines
        """
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)


    def __updateLineNumberArea(self, rect, deltaY):
        """Called on signal updateRequest()

        Invoked when the editors viewport has been scrolled

        The given `rect` is the part of the editing area that need to be updated (redrawn)
        The given `dy` holds the number of pixels the view has been scrolled vertically
        """
        if deltaY>0:
            self.__lineNumberArea.scroll(0, deltaY)
        else:
            self.__lineNumberArea.update(0, rect.y(), self.__lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.__updateLineNumberAreaWidth(0)


    def __highlightCurrentLine(self):
        """When the cursor position changes, highlight the current line (the line containing the cursor)"""
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            selection.format.setBackground(self.__optionColorHighlightedLine)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()

            # QPlainTextEdit gives the possibility to have more than one selection at the same time.
            # We can set the character format (QTextCharFormat) of these selections.
            # We clear the cursors selection before setting the new new QPlainTextEdit.ExtraSelection, else several
            # lines would get highlighted when the user selects multiple lines with the mouse
            selection.cursor.clearSelection()

            extraSelections.append(selection)

        self.setExtraSelections(extraSelections)


    def __isEmptyBlock(self, blockNumber):
        """Check is line for current block is empty or not"""
        # get block text
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.NextBlock, n=blockNumber)
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        text = cursor.selectedText()
        if text.strip() == "":
            return True
        else:
            return False


    def __calculateIndent(self, position):
        """Calculate indent to apply according to current position"""
        indentValue = ceil(position/self.__optionIndentWidth)*self.__optionIndentWidth - position
        if indentValue == 0:
            indentValue = self.__optionIndentWidth
        return indentValue


    def __calculateDedent(self, position):
        """calculate indent to apply according to current position"""
        if position > 0:
            dedentValue = position%self.__optionIndentWidth
            if dedentValue==0:
                return self.__optionIndentWidth
            else:
                return dedentValue

        return 0


    # region: event overload ---------------------------------------------------

    def resizeEvent(self, event):
        """Code editor is resized

        Need to resize the line number area
        """
        super(BSWCodeEditor, self).resizeEvent(event)

        contentRect = self.contentsRect()
        self.__lineNumberArea.setGeometry(QRect(contentRect.left(), contentRect.top(), self.lineNumberAreaWidth(), contentRect.height()))


    def lineNumberAreaPaintEvent(self, event):
        """Paint gutter content"""
        # initialise painter on BSWLineNumberArea
        painter=QPainter(self.__lineNumberArea)

        # set background
        painter.fillRect(event.rect(), self.__optionGutterText.background())

        # Get the top and bottom y-coordinate of the first text block,
        # and adjust these values by the height of the current text block in each iteration in the loop
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Loop through all visible lines and paint the line numbers in the extra area for each line.
        # Note: in a plain text edit each line will consist of one QTextBlock
        #       if line wrapping is enabled, a line may span several rows in the text edit’s viewport
        while block.isValid() and top <= event.rect().bottom():
            # Check if the block is visible in addition to check if it is in the areas viewport
            #   a block can, for example, be hidden by a window placed over the text edit
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(self.__optionGutterText.foreground().color())
                painter.drawText(0, top, self.__lineNumberArea.width(), self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber+=1


    def wheelEvent(self, event):
        """CTRL + wheel os used to zoom in/out font size"""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta < 0:
                self.zoomOut()
            elif delta > 0:
                self.zoomIn()
        else:
            super(BSWCodeEditor, self).wheelEvent(event)


    def keyPressEvent(self, event):
        """Improve editor functionalities with some key bindings"""
        if self.__completer and self.__completer.popup().isVisible():
            # completion popup is visible, so keypressed is for popup
            if event.key() in (
                        Qt.Key_Enter,
                        Qt.Key_Return,
                        Qt.Key_Escape,
                        Qt.Key_Tab,
                        Qt.Key_Backtab):
                event.ignore()
                return

        # retrieve action from current shortcut
        action = self.shortCut(event.key(), event.modifiers())

        if action is None:
            super(BSWCodeEditor, self).keyPressEvent(event)
            # if no action is defined and autocompletion is active, display
            # completer list automatically
            if self.__optionAutoCompletion:
                action = BSWCodeEditor.KEY_COMPLETION
        elif event.key() == Qt.Key_Return:
            super(BSWCodeEditor, self).keyPressEvent(event)

        self.doAction(action)


    def paintEvent(self, event):
        """Customize painting"""
        super(BSWCodeEditor, self).paintEvent(event)

        # initialise som metrics
        rect = event.rect()
        font = self.currentCharFormat().font()
        charWidth = QFontMetricsF(font).averageCharWidth()
        leftOffset = self.contentOffset().x() + self.document().documentMargin()

        # initialise painter to editor's viewport
        painter = QPainter(self.viewport())

        if self.__optionRightLimitVisible:
            # draw right limit
            position = round(charWidth * self.__optionRightLimitPosition) + leftOffset
            painter.setPen(self.__optionRightLimitColor)
            painter.drawLine(position, rect.top(), position, rect.bottom())

        # draw spaces and/or level indent
        block = self.firstVisibleBlock()

        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        painter.setPen(self.__optionSpacesColor)
        previousIndent=0

        while block.isValid() and top <= event.rect().bottom():
            # Check if the block is visible in addition to check if it is in the areas viewport
            #   a block can, for example, be hidden by a window placed over the text edit
            if block.isVisible() and bottom >= event.rect().top():
                result=re.search("(\s*)$", block.text())
                posSpacesRight=0
                nbSpacesLeft = len(re.match("(\s*)", block.text()).groups()[0])
                nbSpacesRight = len(result.groups()[0])
                if nbSpacesRight>0:
                    posSpacesRight=result.start()

                left = leftOffset

                if self.__optionSpacesVisible:
                    # draw spaces
                    for i in range(nbSpacesLeft):
                        painter.drawText(left, top, charWidth, self.fontMetrics().height(), Qt.AlignLeft, '.')
                        left+=charWidth

                    left = leftOffset + charWidth * posSpacesRight
                    for i in range(nbSpacesRight):
                        painter.drawText(left, top, charWidth, self.fontMetrics().height(), Qt.AlignLeft, '.')
                        left+=charWidth

                # draw level indent
                if nbSpacesLeft>0 or previousIndent>0:
                    # if spaces or previous indent, check if level indent have to be drawn
                    if len(block.text()) == 0:
                        # current block is empty (even no spaces)
                        # look forward for next block with level > 0
                        # if found, keep current indent otherwhise, no indent
                        nBlockText=block.next()
                        while nBlockText.blockNumber() > -1 and nBlockText.isVisible():
                            if nBlockText is None:
                                break
                            if len(nBlockText.text())>0:
                                nNbSpacesLeft = len(re.match("(\s*)", nBlockText.text()).groups()[0])
                                if nNbSpacesLeft == 0:
                                    nbSpacesLeft = 0
                                else:
                                    nbSpacesLeft=previousIndent
                                break
                            nBlockText=nBlockText.next()
                    elif len(block.text().strip()) == 0:
                        # current block is only spaces, then draw level indent
                        nbSpacesLeft=max(previousIndent, nbSpacesLeft)
                    else:
                        previousIndent=nbSpacesLeft

                    left = leftOffset + round(charWidth*2/3,0)
                    nbChar = 0
                    while nbChar < nbSpacesLeft:
                        position = round(charWidth * nbChar) + leftOffset
                        painter.drawLine(position, top, position, top + self.blockBoundingRect(block).height() - 1)
                        nbChar+=self.__optionIndentWidth
                elif len(block.text().strip()) > 0:
                    previousIndent=0


            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()


    def insertFromMimeData(self, source):
        """Data from clipboad are being pasted

        replace tabs by spaces and paste content
        """
        if source.hasText():
            text = source.text().replace('\t', ' ' *self.__optionIndentWidth)
            cursor = self.textCursor()
            cursor.insertText(text);


    #def focusInEvent(self, event):
    #    if self.__completer:
    #        self.__completer.setWidget(self)
    #    super(BSWCodeEditor, self).focusInEvent(event)


    # endregion: event overload ------------------------------------------------


    def lineNumberAreaWidth(self):
        """Calculate width for line number area

        Width is calculated according to number of lines
           X lines => 1 digit
          XX lines => 2 digits
         XXX lines => 3 digits
        XXXX lines => 4 digits
        ...
        """
        # start with 2digits (always have space for one digit more)
        digits = 2
        maxBlock = max(1, self.blockCount())
        while maxBlock >= 10:
            maxBlock /= 10
            digits+=1

        # width = (witdh for digit '9') * (number of digits) + 3pixels
        return 3 + self.fontMetrics().width('9') * digits


    def doAction(self, action=None):
        """Execute given action"""
        if action is None:
            return
        elif action == BSWCodeEditor.KEY_INDENT:
            self.doIndent()
        elif action == BSWCodeEditor.KEY_DEDENT:
            self.doDedent()
        elif action == BSWCodeEditor.KEY_TOGGLE_COMMENT:
            self.doToggleComment()
        elif action == BSWCodeEditor.KEY_AUTOINDENT:
            self.doAutoIndent()
        elif action == BSWCodeEditor.KEY_COMPLETION:
            self.doCompletionPopup()


    def shortCut(self, key, modifiers):
        """Return action for given key/modifier shortCut

        If nothing is defined, return None
        """
        if key in self.__shortCuts:
            ctrlModifier=(Qt.ControlModifier & modifiers == Qt.ControlModifier)
            if ctrlModifier in self.__shortCuts[key]:
                return self.__shortCuts[key][ctrlModifier]
        return None


    def setShortCut(self, key, modifiers, action):
        """Set action for given key/modifier"""
        if not action in (BSWCodeEditor.KEY_INDENT,
                          BSWCodeEditor.KEY_DEDENT,
                          BSWCodeEditor.KEY_TOGGLE_COMMENT):
            raise EInvalidValue('Given `action` is not a valid value')

        if modifiers is None:
            modifiers = BSWCodeEditor.CTRL_KEY_FALSE

        if not key in self.__shortCuts:
            self.__shortCuts[key]={}

        self.__shortCuts[key][modifiers]=action


    def actionShortCut(self, action):
        """Return shortcut for given action

        If nothing is defined or action doesn't exists, return None
        If found, Shortcut is returned as a tuple (key, modifiers)
        """
        for key in self.__shortCuts:
            for modifiers in self.__shortCuts[key]:
                if self.__shortCuts[key][modifiers]==action:
                    return (key, modifiers)
        return None


    def indentWidth(self):
        """Return current indentation width"""
        return self.__indent


    def setIndentWidth(self, value):
        """Set current indentation width

        Must be a value greater than 0
        """
        if isinstance(value, int):
            if value>0:
                self.__indent=value
            else:
                raise EInvalidType("Given `value`must be an integer greater than 0")
        else:
            raise EInvalidType("Given `value`must be an integer greater than 0")


    def doAutoIndent(self):
        """Indent current line to match indent of previous line

        if no previous exists, then, no indent...
        """

        cursor = self.textCursor()

        selectionStart = cursor.selectionStart()
        selectionEnd = cursor.selectionEnd()

        # determinate block numbers
        cursor.setPosition(selectionStart)
        startBlock = cursor.blockNumber()

        cursor.setPosition(selectionEnd)
        endBlock = cursor.blockNumber()

        cursor.movePosition(QTextCursor.Start)

        indentSize=0
        if startBlock>0:
            cursor.movePosition(QTextCursor.NextBlock, n=startBlock-1)
            # calculate indentation of previous block
            indentSize=len(cursor.block().text()) - len(cursor.block().text().lstrip())
            cursor.movePosition(QTextCursor.NextBlock)
        else:
            cursor.movePosition(QTextCursor.NextBlock, n=startBlock)

        # determinate if spaces have to be added or removed
        nbChar=indentSize - (len(cursor.block().text()) - len(cursor.block().text().lstrip()))

        cursor.movePosition(QTextCursor.StartOfLine)
        if nbChar > 0:
            cursor.insertText(" " * nbChar)
        else:
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, -nbChar)
            cursor.removeSelectedText()


    def doIndent(self):
        """Indent current line or current selection"""

        cursor = self.textCursor()

        selectionStart = cursor.selectionStart()
        selectionEnd = cursor.selectionEnd()

        if selectionStart == selectionEnd:
            # No selection: just insert spaces
            # Note:
            #   Editor don't add a number of 'indent' spaces, but insert spaces
            #   to match to column position
            #
            #   Example: indent space = 4
            #            columns: 4, 8, 12, 16, 20, ...
            #
            #            x = cursor position
            #            o = cursor position after tab
            #            ...|...|...|...|...
            #            x  o
            #                x  o
            #                          xo

            # calculate position relative to start of line
            cursorSol = self.textCursor()
            cursorSol.movePosition(QTextCursor.StartOfLine)
            positionSol = (selectionStart - cursorSol.selectionStart())

            cursor.insertText(" " * self.__calculateIndent(positionSol))
            return

        # determinate block numbers
        cursor.setPosition(selectionStart)
        startBlock = cursor.blockNumber()

        cursor.setPosition(selectionEnd)
        endBlock = cursor.blockNumber()

        # determinate if last block have to be processed
        # exemple:
        #
        #   +-- Start of selection
        #   V
        #   *   Line 1
        #       Line 2
        #   *   Line 3
        #   ^
        #   +-- End of selection
        #
        #   In this case, only the first 2 lines are processed, not the last (nothing selected on last line)
        #
        #
        #   +-- Start of selection
        #   V
        #   *   Line 1
        #       Line 2
        #       Li*e 3
        #         ^
        #         +-- End of selection
        #
        #   In this case, the 3 lines are processed
        #
        processLastBlock=cursor.selectionStart()
        cursor.movePosition(QTextCursor.StartOfLine)
        processLastBlock-=cursor.selectionStart()
        if processLastBlock>0:
            processLastBlock=1


        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.NextBlock, n=startBlock)

        for blockNumber in range(startBlock, endBlock+processLastBlock):
            if not self.__isEmptyBlock(blockNumber):
                # empty lines are not indented
                nbChar=len(cursor.block().text()) - len(cursor.block().text().lstrip())
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.insertText(" " * self.__calculateIndent(nbChar))

            cursor.movePosition(QTextCursor.NextBlock)


    def doDedent(self):
        """Dedent current line or current selection"""
        cursor = self.textCursor()

        selectionStart = cursor.selectionStart()
        selectionEnd = cursor.selectionEnd()

        # determinate block numbers
        cursor.setPosition(selectionStart)
        startBlock = cursor.blockNumber()

        cursor.setPosition(selectionEnd)
        endBlock = cursor.blockNumber()

        processLastBlock = cursor.selectionStart()
        cursor.movePosition(QTextCursor.StartOfLine)
        processLastBlock-=cursor.selectionStart()
        if processLastBlock>0 or selectionStart == selectionEnd:
            processLastBlock=1

        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.NextBlock, n=startBlock)

        for blockNumber in range(startBlock, endBlock + processLastBlock):
            nbChar=self.__calculateDedent(len(cursor.block().text()) - len(cursor.block().text().lstrip()))
            if nbChar>0:
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, nbChar)
                cursor.removeSelectedText()

            cursor.movePosition(QTextCursor.NextBlock)


    def doToggleComment(self):
        """Toggle comment for current line or selected lines"""
        cursor = self.textCursor()

        selectionStart = cursor.selectionStart()
        selectionEnd = cursor.selectionEnd()

        # determinate block numbers
        cursor.setPosition(selectionStart)
        startBlock = cursor.blockNumber()

        cursor.setPosition(selectionEnd)
        endBlock = cursor.blockNumber()

        processLastBlock = cursor.selectionStart()
        cursor.movePosition(QTextCursor.StartOfLine)
        processLastBlock-=cursor.selectionStart()
        if processLastBlock>0 or selectionStart == selectionEnd:
            processLastBlock=1

        # True = COMMENT
        # False = UNCOMMENT
        hasUncommented=False

        # Work with 2 pass
        # Pass #1
        #    Look all blocks
        #       if at least one block is not commented, then active COMMENT
        #       if ALL block are commented, then active UNCOMMENT
        # Pass #2
        #    Apply COMMENT/UNCOMMENT

        # Pass 1
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.NextBlock, n=startBlock)

        for blockNumber in range(startBlock, endBlock + processLastBlock):
            blockText=cursor.block().text()

            if re.match(r'^\s*#', blockText) is None:
                hasUncommented = True
                # dont' need to continue to look content, we know that we have to comment selected text
                break
            cursor.movePosition(QTextCursor.NextBlock)

        # Pass 2
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.NextBlock, n=startBlock)

        for blockNumber in range(startBlock, endBlock + processLastBlock):
            blockText=cursor.block().text()

            commentPosition=len(blockText) - len(blockText.lstrip())
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, commentPosition)

            if hasUncommented:
                # Comment
                cursor.insertText("# ")
            else:
                # Uncomment
                # Remove hashtag and all following spaces
                hashtag=re.search('(#+[\s]*)', blockText)

                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(hashtag.groups()[0]))
                cursor.removeSelectedText()

            cursor.movePosition(QTextCursor.NextBlock)


    def doCompletionPopup(self):
        """Display autocompletion popup"""
        hidePopup=False
        minLength = 0
        currentToken = self.__highlighter.currentCursorToken()
        refToken = self.__highlighter.currentCursorToken()
        srcText=""

        # Determinate current text
        if currentToken is None:
            # try with last processed token
            currentToken = self.__highlighter.lastCursorToken()
        else:
            srcText=currentToken.text()

        if currentToken is None or currentToken.family() in (BSTokenFamily.TOKEN_STRING,
                                                             BSTokenFamily.TOKEN_NUMBER,
                                                             BSTokenFamily.TOKEN_COMMENT,
                                                             BSTokenFamily.TOKEN_OPERATOR,
                                                             BSTokenFamily.TOKEN_BRACES,
                                                             BSTokenFamily.TOKEN_SPACE_NL,
                                                             BSTokenFamily.TOKEN_COLOR,
                                                             BSTokenFamily.TOKEN_ACTION,
                                                             BSTokenFamily.TOKEN_FLOW,
                                                             BSTokenFamily.TOKEN_FUNCTION,
                                                             BSTokenFamily.TOKEN_VARIABLE_INTERNAL,
                                                             BSTokenFamily.TOKEN_CONSTANT):
            # no text, or text is a token for which we don't want to display popup
            self.__completer.popup().hide()
            return

        text = currentToken.text()
        if len(text)<1:
            # if current text is less than one character, do not display popup
            self.__completer.popup().hide()
            return

        # try to determinate text
        while True:
            if currentToken.previous() is None:
                break

            if not currentToken.family() in (BSTokenFamily.TOKEN_SPACE_WC, BSTokenFamily.TOKEN_UNKNOWN) and currentToken.previous().family() != currentToken.family():
                break

            currentToken=currentToken.previous()
            if currentToken.family() == BSTokenFamily.TOKEN_SPACE_WC:
                text = " " + text
            else:
                text = currentToken.text() + text

        proposals=self.__languageDef.getTextProposal(text)
        if len(proposals)==0:
            # if we can't found completion values from current text, use initial text
            text = srcText
        elif len(proposals)==1 and proposals[0][0]==text:
            # if we only found current text, do not display popup
            self.__completer.popup().hide()
            return

        if text != self.__completer.completionPrefix():
            self.__completer.setCompletionPrefix(text)
            popup = self.__completer.popup()
            popup.setCurrentIndex(self.__completer.completionModel().index(0,0))

        cursorRect = self.cursorRect()
        cursorRect.setWidth(self.__completer.popup().sizeHintForColumn(0) + self.__completer.popup().verticalScrollBar().sizeHint().width())
        self.__completer.complete(cursorRect)


class BSWLineNumberArea(QWidget):
    """Gutter area for line number

    # From example documentation
    We paint the line numbers on this widget, and place it over the BSWCodeEditor's viewport() 's left margin area.

    We need to use protected functions in QPlainTextEdit while painting the area.
    So to keep things simple, we paint the area in the CodeEditor class.
    The area also asks the editor to calculate its size hint.

    Note that we could simply paint the line numbers directly on the code editor, and drop the BSWLineNumberArea class.
    However, the QWidget class helps us to scroll() its contents.
    Also, having a separate widget is the right choice if we wish to extend the editor with breakpoints or other code editor features.
    The widget would then help in the handling of mouse events.
    """

    def __init__(self, codeEditor):
        super(BSWLineNumberArea, self).__init__(codeEditor)
        self.__codeEditor = codeEditor

    def sizeHint(self):
        return Qsize(self.__codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        """It Invokes the draw method(lineNumberAreaPaintEvent) in CodeEditor"""
        self.__codeEditor.lineNumberAreaPaintEvent(event)


class BSWCodeEditorCompleterModel(QAbstractListModel):
    """Dedicated model used to list completion values"""

    VALUE = Qt.UserRole + 1
    FAMILY = Qt.UserRole + 2
    STYLE = Qt.UserRole + 3

    def __init__(self, parent=None):
        """Initialise list"""
        super().__init__(parent)
        self.__items=[]

    def __repr__(self):
        print(f'<BSWCodeEditorCompleterModel({self.__items})>')

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        row = index.row()
        if role in (BSWCodeEditorCompleterModel.VALUE, Qt.DisplayRole):
            return self.__items[row]["value"]
        if role == BSWCodeEditorCompleterModel.FAMILY:
            return self.__items[row]["family"]
        if role == BSWCodeEditorCompleterModel.STYLE:
            return self.__items[row]["style"]

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows"""
        return len(self.__items)

    def roleNames(self):
        return {
            BSWCodeEditorCompleterModel.VALUE: b'value',
            BSWCodeEditorCompleterModel.FAMILY: b'family',
            BSWCodeEditorCompleterModel.STYLE: b'style'
        }

    @pyqtSlot(str, int)
    def add(self, value, family, style):
        """Add an item to model"""
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.__items.append({'value': value, 'family': family, 'style': style})
        self.endInsertRows()

    @pyqtSlot(int, str, int)
    def edit(self, row, value, age):
        """Modify an item from model"""
        ix = self.index(row, 0)
        self.__items[row] = {'value': value, 'family': family, 'style': style}
        self.dataChanged.emit(ix, ix, self.roleNames())

    @pyqtSlot(int)
    def delete(self, row):
        """Remove an item from model"""
        self.beginRemoveColumns(QModelIndex(), row, row)
        del self.__items[row]
        self.endRemoveRows()

    def clear(self):
        """Clear model"""
        self.beginRemoveColumns(QModelIndex(), 0, len(self.__items))
        self.__items=[]
        self.endRemoveRows()

    def sort(self):
        """Sort list content"""
        def sortKey(v):
            return f'{v["family"]:02}-{v["value"].lower()}'
        self.__items.sort(key=sortKey)


class BSWCodeEditorCompleterView(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build an improved QCompleter list that
    list completion value with improved style
    """
    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(BSWCodeEditorCompleterView, self).__init__(parent)


    def paint(self, painter, option, index):
        """Paint list item:
        - completion type ('F'=flow, 'a'=action, 'v'=variable...)
        - completion value, using editor's style
        """
        self.initStyleOption(option, index)

        # retrieve style from token
        style = index.data(BSWCodeEditorCompleterModel.STYLE)

        # memorize curent state
        painter.save()
        currentFontName=painter.font().family()
        currentFontSize=painter.font().pointSizeF()
        color = style.foreground().color()

        # -- completion type
        rect = QRect(option.rect.left(), option.rect.top(), 2 * option.rect.height(), option.rect.height())
        if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
            painter.fillRect(rect, QBrush(color.darker(200)))
        else:
            painter.fillRect(rect, QBrush(color.darker(300)))
        font = style.font()
        font.setFamily("DejaVu Sans [Qt Embedded]")
        font.setBold(True)
        font.setPointSizeF(currentFontSize * 0.65)

        painter.setFont(font)
        painter.setPen(QPen(color.lighter(300)))

        painter.drawText(rect, Qt.AlignHCenter|Qt.AlignVCenter, BSTokenFamily.letter(index.data(BSWCodeEditorCompleterModel.FAMILY)))

        # -- completion value
        font = style.font()
        font.setFamily(currentFontName)
        font.setPointSizeF(currentFontSize)


        painter.setFont(font)
        painter.setPen(QPen(color))

        if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
            rect = QRect(option.rect.left() + 2 * option.rect.height(), option.rect.top(), option.rect.width(), option.rect.height())
            painter.fillRect(rect, option.palette.color(QPalette.AlternateBase))
        rect = QRect(option.rect.left() + 2 *  option.rect.height() + 5, option.rect.top(), option.rect.width(), option.rect.height())
        painter.drawText(rect, Qt.AlignLeft|Qt.AlignVCenter, index.data(BSWCodeEditorCompleterModel.VALUE))

        painter.restore()

    def sizeHint(self, option, index):
        """Caclulate size for rendered completion item"""
        size = super(BSWCodeEditorCompleterView, self).sizeHint(option, index)
        size.setWidth(size.width() + 2 * size.height() + 5)
        return size


