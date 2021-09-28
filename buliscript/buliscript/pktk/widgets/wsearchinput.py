#-----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2021 - Grum999
#
# A toolkit to make pykrita plugin coding easier :-)
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




# -----------------------------------------------------------------------------

import html

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )


from ..modules.imgutils import buildIcon
from .wseparator import WVLine


class SearchOptions:
    REGEX =               0b0000000000000001
    CASESENSITIVE =       0b0000000000000010
    WHOLEWORD =           0b0000000000000100
    BACKWARD =            0b0000000000001000
    HIGHLIGHT =           0b0000000000010000


class WSearchInput(QWidget):
    """A LineEdit combined with some buttons to provide a ready-to-use search bar tool"""
    searchActivated = Signal(str, int)              # when RETURN key has been pressed
    searchModified = Signal(str, int)               # when search value has been modified
    searchOptionModified = Signal(str, int)         # when at least one search option has been modified value has been modified

    OPTION_SHOW_BUTTON_SEARCH =         0b0000000100000000
    OPTION_SHOW_BUTTON_REGEX =          0b0000001000000000
    OPTION_SHOW_BUTTON_CASESENSITIVE =  0b0000010000000000
    OPTION_SHOW_BUTTON_WHOLEWORD =      0b0000100000000000
    OPTION_SHOW_BUTTON_BACKWARD =       0b0001000000000000
    OPTION_SHOW_BUTTON_HIGHLIGHTALL =   0b0010000000000000
    OPTION_SHOW_BUTTON_SHOWHIDE =       0b0100000000000000

    OPTION_STATE_BUTTONSHOW =           0b1000000000000000

    OPTION_ALL_BUTTONS =                0b0111111100000000
    OPTION_ALL_SEARCH =                 0b0000000000011111
    OPTION_ALL =                        0b1111111100011111

    def __init__(self, options=None, parent=None):
        super(WSearchInput, self).__init__(parent)

        self.__layout=QHBoxLayout()
        self.__leSearch=QLineEdit(self)
        self.__leSearch.returnPressed.connect(self.applySearch)
        self.__leSearch.textChanged.connect(self. __searchTextModified)
        self.__leSearch.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.__leSearch.setClearButtonEnabled(True)
        self.__leSearch.findChild(QToolButton).setIcon(buildIcon("pktk:edit_text_clear"))

        self.__btSearch=QToolButton(self)
        self.__btRegEx=QToolButton(self)
        self.__btCaseSensitive=QToolButton(self)
        self.__btWholeWord=QToolButton(self)
        self.__btBackward=QToolButton(self)
        self.__btHighlightAll=QToolButton(self)
        self.__btShowHide=QToolButton(self)

        self.__btSearch.setAutoRaise(True)
        self.__btRegEx.setAutoRaise(True)
        self.__btCaseSensitive.setAutoRaise(True)
        self.__btWholeWord.setAutoRaise(True)
        self.__btBackward.setAutoRaise(True)
        self.__btHighlightAll.setAutoRaise(True)
        self.__btShowHide.setAutoRaise(True)

        self.__btRegEx.setCheckable(True)
        self.__btCaseSensitive.setCheckable(True)
        self.__btWholeWord.setCheckable(True)
        self.__btBackward.setCheckable(True)
        self.__btHighlightAll.setCheckable(True)
        self.__btShowHide.setCheckable(True)

        self.__btSearch.setToolTip(i18n('Search'))
        self.__btRegEx.setToolTip(i18n('Search from regular expression'))
        self.__btCaseSensitive.setToolTip(i18n('Search with case sensitive'))
        self.__btWholeWord.setToolTip(i18n('Search for whole words only'))
        self.__btBackward.setToolTip(i18n('Search in backward direction'))
        self.__btHighlightAll.setToolTip(i18n('Highlight all occurences found'))
        self.__btShowHide.setToolTip(i18n('Show/Hide search options'))

        self.__btSearch.setIcon(buildIcon("pktk:search"))
        self.__btRegEx.setIcon(buildIcon("pktk:filter_regex"))
        self.__btCaseSensitive.setIcon(buildIcon("pktk:filter_case"))
        self.__btWholeWord.setIcon(buildIcon("pktk:filter_wholeword"))
        self.__btBackward.setIcon(buildIcon("pktk:filter_backward"))
        self.__btHighlightAll.setIcon(buildIcon("pktk:filter_highlightall"))
        self.__btShowHide.setIcon(buildIcon("pktk:tune"))


        self.__btSearch.clicked.connect(self.applySearch)
        self.__btRegEx.toggled.connect(self.__searchOptionChanged)
        self.__btCaseSensitive.toggled.connect(self.__searchOptionChanged)
        self.__btWholeWord.toggled.connect(self.__searchOptionChanged)
        self.__btBackward.toggled.connect(self.__searchOptionChanged)
        self.__btHighlightAll.toggled.connect(self.__searchOptionChanged)
        self.__btShowHide.toggled.connect(self.__updateInterface)

        self.__vlN1=WVLine(self)
        self.__vlN2=WVLine(self)

        self.__layout.addWidget(self.__leSearch)
        self.__layout.addWidget(self.__btSearch)
        self.__layout.addWidget(self.__vlN1)
        self.__layout.addWidget(self.__btRegEx)
        self.__layout.addWidget(self.__btCaseSensitive)
        self.__layout.addWidget(self.__btWholeWord)
        self.__layout.addWidget(self.__btBackward)
        self.__layout.addWidget(self.__btHighlightAll)
        self.__layout.addWidget(self.__vlN2)
        self.__layout.addWidget(self.__btShowHide)

        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(3)

        self.setLayout(self.__layout)

        self.__options=0
        if options is None:
            options=WSearchInput.OPTION_ALL_BUTTONS|WSearchInput.OPTION_STATE_BUTTONSHOW

        self.__btShowHide.setChecked(self.__options&WSearchInput.OPTION_STATE_BUTTONSHOW==WSearchInput.OPTION_STATE_BUTTONSHOW)
        self.setOptions(options)


    def __updateInterface(self, visible=None):
        """Update user interface"""
        self.__btSearch.setVisible(self.__options&WSearchInput.OPTION_SHOW_BUTTON_SEARCH==WSearchInput.OPTION_SHOW_BUTTON_SEARCH)
        self.__btShowHide.setVisible(self.__options&WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE==WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE)

        if visible is None:
            # use value from __options (called from setOption() method)
            self.__btShowHide.setChecked(self.__options&WSearchInput.OPTION_STATE_BUTTONSHOW==WSearchInput.OPTION_STATE_BUTTONSHOW)
        else:
            # use value from parameter visible (called from signal emitted when button is toggled)
            self.__btShowHide.setChecked(visible)

        # group is not empty if at least one button is defined as available in options
        groupNotEmpty=(WSearchInput.OPTION_SHOW_BUTTON_REGEX|
                       WSearchInput.OPTION_SHOW_BUTTON_CASESENSITIVE|
                       WSearchInput.OPTION_SHOW_BUTTON_WHOLEWORD|
                       WSearchInput.OPTION_SHOW_BUTTON_BACKWARD|
                       WSearchInput.OPTION_SHOW_BUTTON_HIGHLIGHTALL)!=0

        # group is visible if not empty AND:
        # - button show/hide is not visible
        # OR
        # - button show/hide is visible AND checked
        groupVisible=groupNotEmpty and ((not (self.__options&WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE==WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE)) or self.__btShowHide.isChecked())

        # buttons are visible is group is visible AND button is defined as available in options
        self.__btRegEx.setVisible(groupVisible and (self.__options&WSearchInput.OPTION_SHOW_BUTTON_REGEX==WSearchInput.OPTION_SHOW_BUTTON_REGEX))
        self.__btCaseSensitive.setVisible(groupVisible and (self.__options&WSearchInput.OPTION_SHOW_BUTTON_CASESENSITIVE==WSearchInput.OPTION_SHOW_BUTTON_CASESENSITIVE))
        self.__btWholeWord.setVisible(groupVisible and (self.__options&WSearchInput.OPTION_SHOW_BUTTON_WHOLEWORD==WSearchInput.OPTION_SHOW_BUTTON_WHOLEWORD))
        self.__btBackward.setVisible(groupVisible and (self.__options&WSearchInput.OPTION_SHOW_BUTTON_BACKWARD==WSearchInput.OPTION_SHOW_BUTTON_BACKWARD))
        self.__btHighlightAll.setVisible(groupVisible and (self.__options&WSearchInput.OPTION_SHOW_BUTTON_HIGHLIGHTALL==WSearchInput.OPTION_SHOW_BUTTON_HIGHLIGHTALL))

        # separator 1 is visible is button search is available in options AND group is visible
        self.__vlN1.setVisible((self.__options&WSearchInput.OPTION_SHOW_BUTTON_SEARCH==WSearchInput.OPTION_SHOW_BUTTON_SEARCH) and groupVisible)

        # separator 2 is visible if group is visible AND button show/hide is not visible
        self.__vlN2.setVisible((self.__options&WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE==WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE) and groupVisible)

        self.__btRegEx.setChecked(self.__options&SearchOptions.REGEX==SearchOptions.REGEX)
        self.__btCaseSensitive.setChecked(self.__options&SearchOptions.CASESENSITIVE==SearchOptions.CASESENSITIVE)
        self.__btWholeWord.setChecked(self.__options&SearchOptions.WHOLEWORD==SearchOptions.WHOLEWORD)
        self.__btBackward.setChecked(self.__options&SearchOptions.BACKWARD==SearchOptions.BACKWARD)
        self.__btHighlightAll.setChecked(self.__options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT)


    def __searchOptionChanged(self):
        """Search option has been changed, emit signal"""
        self.searchOptionModified.emit(self.__leSearch.text(), self.options()&WSearchInput.OPTION_ALL_SEARCH)


    def __searchTextModified(self):
        """Search value has been modified, emit signal"""
        self.searchModified.emit(self.__leSearch.text(), self.options()&WSearchInput.OPTION_ALL_SEARCH)


    def options(self):
        """Return current options flags"""
        currentSearch=0
        if self.__btRegEx.isChecked():
            currentSearch|=SearchOptions.REGEX

        if self.__btCaseSensitive.isChecked():
            currentSearch|=SearchOptions.CASESENSITIVE

        if self.__btWholeWord.isChecked():
            currentSearch|=SearchOptions.WHOLEWORD

        if self.__btBackward.isChecked():
            currentSearch|=SearchOptions.BACKWARD

        if self.__btHighlightAll.isChecked():
            currentSearch|=SearchOptions.HIGHLIGHT

        if self.__btShowHide.isChecked() or (self.__options&WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE!=WSearchInput.OPTION_SHOW_BUTTON_SHOWHIDE):
            currentSearch|=WSearchInput.OPTION_STATE_BUTTONSHOW

        self.__options=(self.__options&WSearchInput.OPTION_ALL_BUTTONS)|currentSearch

        return self.__options


    def setOptions(self, options):
        """Set current options flags"""
        if isinstance(options, int):
            self.__options=options&WSearchInput.OPTION_ALL
            self.__updateInterface()


    def applySearch(self):
        """Search button clicked or Return key pressed, emit signal"""
        self.searchActivated.emit(self.__leSearch.text(), self.options()&WSearchInput.OPTION_ALL_SEARCH)


    def searchText(self):
        """Return current search text"""
        return self.__leSearch.text()


    def setSearchText(self, text):
        """Set current search text"""
        self.__leSearch.setText(text)




class SearchFromPlainTextEdit:
    """Provide high level method to search ocurences in a QPlainTextEdit"""

    COLOR_SEARCH_ALL = 0
    COLOR_SEARCH_CURRENT_BG = 'highlightSearchCurrent.bg'
    COLOR_SEARCH_CURRENT_FG = 'highlightSearchCurrent.fg'

    def __init__(self, plainTextEdit):
        if not isinstance(plainTextEdit, QPlainTextEdit):
            raise EInvalidType("Given `plainTextEdit` must be a <QPlainTextEdit>")

        self.__plainTextEdit=plainTextEdit

        # search results
        self.__extraSelectionsFoundAll=[]
        self.__extraSelectionsFoundCurrent=None
        self.__lastFound=None

        self.__searchColors={
                SearchFromPlainTextEdit.COLOR_SEARCH_ALL:           QColor("#77ffc706"),
                SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_BG:    QColor("#9900b86f"),
                SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_FG:    QColor("#ffff00")
            }


    def __highlightedSelections(self):
        """Build extra selection for highlighting"""
        foundCurrentAdded=False
        if self.__extraSelectionsFoundCurrent is None:
            returned=self.__extraSelectionsFoundAll
        else:
            returned=[]
            for cursorFromAll in self.__extraSelectionsFoundAll:
                if cursorFromAll.cursor==self.__extraSelectionsFoundCurrent.cursor:
                    returned.append(self.__extraSelectionsFoundCurrent)
                    foundCurrentAdded=True
                else:
                    returned.append(cursorFromAll)

        if not foundCurrentAdded and not self.__extraSelectionsFoundCurrent is None:
            returned.append(self.__extraSelectionsFoundCurrent)

        return returned


    def searchAll(self, text, options=0):
        """Search all occurences of `text` in console

        If `text` is None or empty string, and option SEARCH_OPTION_HIGHLIGHT is set,
        it will clear all current selected items

        Options is combination of SearchOptions flags:
            HIGHLIGHT =       highlight the found occurences in console
            REGEX =           consider text as a regular expression
            WHOLEWORD =       search for while words only
            CASESENSITIVE =   search with case sensitive

        Return list of cursors
        """
        extraSelectionsFoundAll=[]

        if (text is None or text=='') and options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            # clear current selections
            self.__extraSelectionsFoundAll=[]
            self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())
            return self.__extraSelectionsFoundAll

        findFlags=0
        if options&SearchOptions.WHOLEWORD==SearchOptions.WHOLEWORD:
            findFlags|=QTextDocument.FindWholeWords
        if options&SearchOptions.CASESENSITIVE==SearchOptions.CASESENSITIVE:
            findFlags|=QTextDocument.FindCaseSensitively
        if options&SearchOptions.REGEX==SearchOptions.REGEX:
            text=QRegularExpression(text)


        cursor=self.__plainTextEdit.document().find(text, 0, QTextDocument.FindFlags(findFlags))
        while cursor.position()>0:
            extraSelection=QTextEdit.ExtraSelection()

            extraSelection.cursor=cursor
            extraSelection.format.setBackground(QBrush(self.__searchColors[SearchFromPlainTextEdit.COLOR_SEARCH_ALL]))

            extraSelectionsFoundAll.append(extraSelection)
            cursor=self.__plainTextEdit.document().find(text, cursor, QTextDocument.FindFlags(findFlags))

        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            self.__extraSelectionsFoundAll=extraSelectionsFoundAll
        else:
            self.__extraSelectionsFoundAll=[]

        self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())

        return extraSelectionsFoundAll


    def search(self, text, options=0):
        """Search for first occurence of `text`

        If `text` is None or empty string, and option SEARCH_OPTION_HIGHLIGHT is set,
        it will clear all current selected items

        Options is combination of SearchOptions flags:
            HIGHLIGHT =       highlight the found occurences in console
            REGEX =           consider text as a regular expression
            WHOLEWORD =       search for while words only
            CASESENSITIVE =   search with case sensitive
            BACKWARD =        search in backward direction, otherwise search in forward direction

        Return a cursor or None
        """
        if (text is None or text=='') and options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            self.__extraSelectionsFoundCurrent=None
            self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())
            return self.__extraSelectionsFoundCurrent

        findFlags=0
        if options&SearchOptions.WHOLEWORD==SearchOptions.WHOLEWORD:
            findFlags|=QTextDocument.FindWholeWords
        if options&SearchOptions.CASESENSITIVE==SearchOptions.CASESENSITIVE:
            findFlags|=QTextDocument.FindCaseSensitively
        if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
            findFlags|=QTextDocument.FindBackward

        if options&SearchOptions.REGEX==SearchOptions.REGEX:
            text=QRegularExpression(text)

        if self.__extraSelectionsFoundCurrent is None:
            if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
                cursor=self.__plainTextEdit.document().characterCount()
            else:
                cursor=0
        else:
            if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
                cursor=min(self.__plainTextEdit.document().characterCount(), self.__extraSelectionsFoundCurrent.cursor.position()+1)
            else:
                cursor=max(0, self.__extraSelectionsFoundCurrent.cursor.position()-1)

        found=self.__plainTextEdit.document().find(text, cursor, QTextDocument.FindFlags(findFlags))

        if found is None or found.position()==-1:
            # may be we need to loop
            if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
                cursor=self.__plainTextEdit.document().characterCount()
            else:
                cursor=0

            found=self.__plainTextEdit.document().find(text, cursor, QTextDocument.FindFlags(findFlags))

            if not found is None and found.position()==-1:
                found=None


        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT and not found is None:
            self.__extraSelectionsFoundCurrent=QTextEdit.ExtraSelection()
            self.__extraSelectionsFoundCurrent.format.setBackground(QBrush(self.__searchColors[SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_BG]))
            self.__extraSelectionsFoundCurrent.format.setForeground(QBrush(self.__searchColors[SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_FG]))
            self.__extraSelectionsFoundCurrent.cursor=found
        else:
            self.__extraSelectionsFoundCurrent=None

        self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())

        if not self.__extraSelectionsFoundCurrent is None:
            cursor=QTextCursor(self.__extraSelectionsFoundCurrent.cursor)
            cursor.clearSelection()
            self.__plainTextEdit.setTextCursor(cursor)
            self.__plainTextEdit.centerCursor()

        return found


    def searchNext(self, text, options=0):
        """Search for next occurence of `text`

        If `text` is None or empty string, and option SEARCH_OPTION_HIGHLIGHT is set,
        it will clear all current selected items

        Options is combination of SearchOptions flags:
            HIGHLIGHT =       highlight the found occurences in console
            REGEX =           consider text as a regular expression
            WHOLEWORD =       search for while words only
            CASESENSITIVE =   search with case sensitive
            BACKWARD =        search in backward direction, otherwise search in forward direction

        Return a cursor or None
        """
        if (text is None or text=='') and options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            self.__extraSelectionsFoundCurrent=None
            self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())
            return self.__extraSelectionsFoundCurrent

        findFlags=0
        if options&SearchOptions.WHOLEWORD==SearchOptions.WHOLEWORD:
            findFlags|=QTextDocument.FindWholeWords
        if options&SearchOptions.CASESENSITIVE==SearchOptions.CASESENSITIVE:
            findFlags|=QTextDocument.FindCaseSensitively
        if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
            findFlags|=QTextDocument.FindBackward

        if options&SearchOptions.REGEX==SearchOptions.REGEX:
            text=QRegularExpression(text)

        if self.__extraSelectionsFoundCurrent is None:
            if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
                cursor=self.__plainTextEdit.document().characterCount()
            else:
                cursor=0
        else:
            cursor=self.__extraSelectionsFoundCurrent.cursor

        found=self.__plainTextEdit.document().find(text, cursor, QTextDocument.FindFlags(findFlags))
        loopNumber=0
        while loopNumber<=1:
            # check found occurence
            if found is None or found.position()==-1:
                loopNumber+=1

                # nothing found: may be we need to loop
                if options&SearchOptions.BACKWARD==SearchOptions.BACKWARD:
                    cursor=self.__plainTextEdit.document().characterCount()
                else:
                    cursor=0

                found=self.__plainTextEdit.document().find(text, cursor, QTextDocument.FindFlags(findFlags))

                if not found is None and found.position()==-1:
                    found=None


            if found and not found.block().isVisible():
                # something found, but not visible
                found=self.__plainTextEdit.document().find(text, found, QTextDocument.FindFlags(findFlags))
            elif found:
                break



        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT and not found is None:
            self.__extraSelectionsFoundCurrent=QTextEdit.ExtraSelection()
            self.__extraSelectionsFoundCurrent.format.setBackground(QBrush(self.__searchColors[SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_BG]))
            self.__extraSelectionsFoundCurrent.format.setForeground(QBrush(self.__searchColors[SearchFromPlainTextEdit.COLOR_SEARCH_CURRENT_FG]))
            self.__extraSelectionsFoundCurrent.cursor=found
        else:
            self.__extraSelectionsFoundCurrent=None

        self.__plainTextEdit.setExtraSelections(self.__highlightedSelections())

        if not self.__extraSelectionsFoundCurrent is None:
            cursor=QTextCursor(self.__extraSelectionsFoundCurrent.cursor)
            cursor.clearSelection()
            self.__plainTextEdit.setTextCursor(cursor)
            self.__plainTextEdit.centerCursor()

        return found
