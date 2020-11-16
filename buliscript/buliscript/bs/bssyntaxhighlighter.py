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

    def __init__(self, parent, syntaxRules):
        """When subclassing the QSyntaxHighlighter class you must pass the parent parameter to the base class constructor.

        The parent is the text document upon which the syntax highlighting will be applied.

        Given `syntaxRules` is a BSSyntaxRules object that define language
        Given `syntaxStyles` is a BSSyntaxStyles object that define styles to apply
        """
        super(BSSyntaxHighlighter, self).__init__(parent)

        self.__highlightingRules = syntaxRules

    def highlightBlock(self, text):
        """Highlight given text according to the type"""

        tokens = self.__highlightingRules.tokenized(text)

        #for rule in self.__highlightingRules.rules():
        #    matchIterator = rule.regEx().globalMatch(text, position)
        #    while matchIterator.hasNext():
        #        match = matchIterator.next()
        #        index=len(match.capturedTexts()) - 1
        #        print('==>', match.captured(index), rule)
        #        self.setFormat(match.capturedStart(index), match.capturedLength(index), rule.style())
        #        position=match.capturedEnd(index)

        while not (token:=tokens.next()) is None:
            self.setFormat(token.positionStart(), token.length(), token.style())
