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


from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QWidget,
        QPlainTextEdit
    )
from .bssyntaxhighlighter import BSSyntaxHighlighter
from .bslanguagedef import (
        BSLanguageDef
    )


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

    def __init__(self, parent=None):
        super(BSWCodeEditor, self).__init__(parent)

        # instanciate line number area
        self.__lineNumberArea = BSWLineNumberArea(self)

        # initialise signals
        self.blockCountChanged.connect(self.__updateLineNumberAreaWidth)
        self.updateRequest.connect(self.__updateLineNumberArea)
        self.cursorPositionChanged.connect(self.__highlightCurrentLine)

        # define editor properties
        self.__colorGutter=BSColorProp(QColor('#4c5363'), QColor('#282c34'))
        self.__colorHighlightedLine=BSColorProp(QColor('#000000'), QColor('#2d323c'))

        font = QFont()
        font.setFamily("Monospace")
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)

        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Base, QColor('#282c34'))
        palette.setColor(QPalette.Inactive, QPalette.Base, QColor('#282c34'))


        self.__highlighter = BSSyntaxHighlighter(self.document(), BSLanguageDef())

        # default values
        self.__updateLineNumberAreaWidth()
        self.__highlightCurrentLine()


    def __updateLineNumberAreaWidth(self, dummy=None):
        """Called on signal blockCountChanged()

        Update viewport margins, taking in account (new) total number of lines
        """
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)


    def __updateLineNumberArea(self, rect, dy):
        """Called on signal updateRequest()

        Invoked when the editors viewport has been scrolled

        The given `rect` is the part of the editing area that need to be updated (redrawn)
        The given `dy` holds the number of pixels the view has been scrolled vertically
        """
        if dy>0:
            self.__lineNumberArea.scroll(0, dy)
        else:
            self.__lineNumberArea.update(0, rect.y(), self.__lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.__updateLineNumberAreaWidth(0)


    def __highlightCurrentLine(self):
        """When the cursor position changes, highlight the current line (the line containing the cursor)"""
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            selection.format.setBackground(self.__colorHighlightedLine.background())
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()

            # QPlainTextEdit gives the possibility to have more than one selection at the same time.
            # We can set the character format (QTextCharFormat) of these selections.
            # We clear the cursors selection before setting the new new QPlainTextEdit.ExtraSelection, else several
            # lines would get highlighted when the user selects multiple lines with the mouse
            selection.cursor.clearSelection()

            extraSelections.append(selection)

        self.setExtraSelections(extraSelections)


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
        painter.fillRect(event.rect(), self.__colorGutter.background())

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
                painter.setPen(self.__colorGutter.foreground())
                painter.drawText(0, top, self.__lineNumberArea.width(), self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber+=1


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


