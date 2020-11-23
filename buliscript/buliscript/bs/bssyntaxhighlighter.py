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


# From Qt documentation example "Syntax Highlighter"
# https://doc.qt.io/qtforpython-5.12/overviews/qtwidgets-richtext-syntaxhighlighter-example.html#syntax-highlighter-example


from PyQt5.Qt import *
from PyQt5.QtGui import (
        QSyntaxHighlighter
    )


class BSSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Buli Script language"""

    def __init__(self, parent, languageDef, editor):
        """When subclassing the QSyntaxHighlighter class you must pass the parent parameter to the base class constructor.

        The parent is the text document upon which the syntax highlighting will be applied.

        Given `languageDef` is a BSLanguageDef object that define language
        """
        super(BSSyntaxHighlighter, self).__init__(parent)

        self.__languageDef = languageDef
        self.__cursorLastToken = None
        self.__cursorToken = None
        self.__editor=editor


    def highlightBlock(self, text):
        """Highlight given text according to the type"""
        tokens = self.__languageDef.tokenizer().tokenize(text)
        self.__cursorToken = None
        self.__cursorPreviousToken = None

        # determinate if current processed block is current line
        notCurrentLine = (self.currentBlock().firstLineNumber() != self.__editor.textCursor().block().firstLineNumber())

        cursor = self.__editor.textCursor()
        cursorPosition = cursor.selectionEnd()
        cursor.movePosition(QTextCursor.StartOfLine)
        cursorPosition-=cursor.selectionEnd()

        while not (token:=tokens.next()) is None:
            if cursorPosition <= token.positionEnd():
                self.__cursorLastToken=token

            if token.isUnknown() and notCurrentLine or not token.isUnknown():
                # highlight unknown token only if leave current line, otherwise apply style
                self.setFormat(token.positionStart(), token.length(), self.__languageDef.style(token))

            if not notCurrentLine and self.__cursorToken is None and cursorPosition >= token.positionStart() and cursorPosition <= token.positionEnd():
                self.__cursorPreviousToken = self.__cursorToken
                self.__cursorToken = token


    def currentCursorToken(self):
        """Return token on which cursor is"""
        return self.__cursorToken


    def lastCursorToken(self):
        """Return last token processed before current token on which cursor is"""
        return self.__cursorLastToken
