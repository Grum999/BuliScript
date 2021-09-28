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

import html
import re
import random

from PyQt5.Qt import *
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )


from buliscript.pktk.modules.imgutils import buildIcon
from buliscript.pktk.widgets.wseparator import WVLine
from buliscript.pktk.widgets.wconsole import (
        WConsole,
        WConsoleType
    )
from buliscript.pktk.widgets.wsearchinput import (
        WSearchInput,
        SearchOptions
    )


class BSDockWidgetConsoleOutput(QDockWidget):
    """A dock widget to display reference language

    Docker is made of:
    - A QLineEdit: used as search filter
    - QButtons: used to define quick filters & actions
    - A WConsole: used to provide output content
    """
    sourceRefClicked = Signal(str, int, int, int, int)   # source, col start, row start, col end, row end

    OPTION_BTN_REGEX =               0b0000000000000001
    OPTION_BTN_CASESENSITIVE =       0b0000000000000010
    OPTION_BTN_WHOLEWORD =           0b0000000000000100
    OPTION_BTN_BACKWARD =            0b0000000000001000
    OPTION_BTN_HIGHLIGHT =           0b0000000000010000
    # available bits:                       <---->
    OPTION_BTN_BUTTONSHOW =          0b1000000000000000
    OPTION_TXT_SEARCH =              0b0100000000000000
    OPTION_FILTER_TYPES =            0b0010000000000000
    OPTION_BUFFER_SIZE =             0b0001000000000000
    OPTION_AUTOCLEAR =               0b0000100000000000

    def __init__(self, parent, name='Output'):
        super(BSDockWidgetConsoleOutput, self).__init__(name, parent)

        self.__widget=QWidget(self)
        self.__widget.setMinimumWidth(200)

        self.__layout=QVBoxLayout(self.__widget)
        self.__widget.setLayout(self.__layout)

        self.__cConsole=WConsole(self)
        self.__tbFilter=BSConsoleTBar(self.__cConsole)

        self.__layout.addWidget(self.__tbFilter)
        self.__layout.addWidget(self.__cConsole)

        self.__cConsole.setOptionBufferSize(1500)

        self.__origConsoleMouseEvent=self.__cConsole.mousePressEvent
        self.__cConsole.mousePressEvent=self.__mouseClick

        self.setWidget(self.__widget)

    def __mouseClick(self, event):
        """Clicked on console"""
        if self.__origConsoleMouseEvent:
            self.__origConsoleMouseEvent(event)

        cursor=self.__cConsole.cursorForPosition(event.pos())
        if cursor:
            data=cursor.block().userData()
            if data is None:
                return
            data=data.data('position')
            if not data is None:
                self.sourceRefClicked.emit('', data['from']['column'], data['from']['row'], data['to']['column'], data['to']['row'] )

    def option(self, optionId):
        """Return current option value

        Option Id refer to:                                                 Returned Value
            BSDockWidgetConsoleOutput.OPTION_BTN_REGEX                      Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE              Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD                   Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW                 Boolean
            BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH                     String
            BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES                   List
            BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE                    Integer
            BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR                      Boolean
        """
        if optionId&BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE==BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE:
            return self.__cConsole.optionBufferSize()
        else:
            return self.__tbFilter.option(optionId)


    def setOption(self, optionId, value):
        """Set option value

        Option Id refer to:                                                 Value
            BSDockWidgetConsoleOutput.OPTION_BTN_REGEX                      Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE              Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD                   Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW                 Boolean
            BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH                     String
            BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES                   List
            BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE                    Integer
            BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR                      Boolean
        """
        if optionId&BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE==BSDockWidgetConsoleOutput.OPTION_BUFFER_SIZE:
            self.__cConsole.setOptionBufferSize(value)
        else:
            self.__tbFilter.setOption(optionId, value)


    def console(self):
        """Return console instance"""
        return self.__cConsole

    def append(self, text, type=WConsoleType.NORMAL, data=None, cReturn=True):
        """Append `text` to console, using given `type`
        If `cReturn` is True, apply a carriage return
        """
        if cReturn==True:
            self.__cConsole.appendLine(text, type, data)
        else:
            self.__cConsole.append(text)


class BSConsoleTBar(QWidget):
    """Interface to manage filter + buttons"""

    def __init__(self, console, parent=None):
        super(BSConsoleTBar, self).__init__(parent)
        self.__console=console

        self.__layout=QHBoxLayout(self)

        self.__btFilterType=QToolButton(self)
        self.__btFilterType.setAutoRaise(True)
        self.__btFilterType.setIcon(buildIcon('pktk:filter_alt'))
        self.__btFilterType.setToolTip(i18n('Apply filter'))
        self.__btFilterType.setPopupMode(QToolButton.InstantPopup)

        self.__btClear=QToolButton(self)
        self.__btClear.setAutoRaise(True)
        self.__btClear.setIcon(buildIcon('pktk:clear'))
        self.__btClear.setToolTip(i18n('Clear console output'))
        self.__btClear.setStatusTip(i18n('When checked, clear console output automatically before script execution'))
        self.__btClear.setPopupMode(QToolButton.MenuButtonPopup)
        self.__btClear.clicked.connect(self.__console.clear)

        self.__siSearch=WSearchInput(WSearchInput.OPTION_ALL_BUTTONS|WSearchInput.OPTION_STATE_BUTTONSHOW, self)
        self.__siSearch.searchActivated.connect(self.__searchActivated)
        self.__siSearch.searchModified.connect(self.__searchModified)
        self.__siSearch.searchOptionModified.connect(self.__searchOptionModified)
        self.__siSearch.setToolTip(i18n('Search for text'))

        self.__currentOptions=0

        self.__layout.addWidget(self.__btClear)
        self.__layout.addWidget(WVLine(self))
        self.__layout.addWidget(self.__btFilterType)
        self.__layout.addWidget(self.__siSearch)
        self.__layout.setContentsMargins(0,0,0,0)

        # -- build menu for filter type
        self.__actionFilterTypeError=QAction(i18n('Show errors'), self)
        self.__actionFilterTypeError.setCheckable(True)
        self.__actionFilterTypeError.setChecked(True)
        self.__actionFilterTypeError.toggled.connect(self.__filterOptionModified)
        self.__actionFilterTypeWarning=QAction(i18n('Show warnings'), self)
        self.__actionFilterTypeWarning.setCheckable(True)
        self.__actionFilterTypeWarning.setChecked(True)
        self.__actionFilterTypeWarning.toggled.connect(self.__filterOptionModified)
        self.__actionFilterTypeInfo=QAction(i18n('Show verbose'), self)
        self.__actionFilterTypeInfo.setCheckable(True)
        self.__actionFilterTypeInfo.setChecked(True)
        self.__actionFilterTypeInfo.toggled.connect(self.__filterOptionModified)
        self.__actionFilterTypeValid=QAction(i18n('Show informations'), self)
        self.__actionFilterTypeValid.setCheckable(True)
        self.__actionFilterTypeValid.setChecked(True)
        self.__actionFilterTypeValid.toggled.connect(self.__filterOptionModified)

        self.__menuFilterType = QMenu(self.__btFilterType)
        self.__menuFilterType.addAction(self.__actionFilterTypeError)
        self.__menuFilterType.addAction(self.__actionFilterTypeWarning)
        self.__menuFilterType.addAction(self.__actionFilterTypeInfo)
        self.__menuFilterType.addAction(self.__actionFilterTypeValid)
        self.__btFilterType.setMenu(self.__menuFilterType)

        # -- build menu for clear button
        self.__actionAutoClear=QAction(i18n('Auto clear'), self)
        self.__actionAutoClear.setCheckable(True)
        self.__actionAutoClear.setChecked(True)

        self.__menuClearOptions = QMenu(self.__btClear)
        self.__menuClearOptions.addAction(self.__actionAutoClear)
        self.__btClear.setMenu(self.__menuClearOptions)


        self.setLayout(self.__layout)

    def __searchActivated(self, text, options):
        """Ask to search for text"""
        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            # select all occurences
            self.__console.search().searchAll(text, options)
        else:
            # deselect all highlighted occurences
            self.__console.search().searchAll(None, SearchOptions.HIGHLIGHT)

        # force highlight option when searching a text
        self.__console.search().searchNext(text, options|SearchOptions.HIGHLIGHT)

        self.__currentOptions=options

    def __searchModified(self, text, options):
        """Ask to search for text -- search made only for highlighted text"""
        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            # select all occurences
            self.__console.search().searchAll(text, options)
        else:
            # deselect all highlighted occurences
            self.__console.search().searchAll(None, SearchOptions.HIGHLIGHT)

        self.__currentOptions=options

    def __searchOptionModified(self, text, options):
        """option have been modified, ask to search for text taking in account new options"""
        if options&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT:
            # select all occurences
            self.__console.search().searchAll(text, options)
        else:
            # deselect all highlighted occurences
            self.__console.search().searchAll(None, SearchOptions.HIGHLIGHT)

        if (self.__currentOptions^options)&SearchOptions.HIGHLIGHT!=SearchOptions.HIGHLIGHT:
            # search only if modified option is not highlight all

            # force highlight option when searching a text
            self.__console.search().search(text, options|SearchOptions.HIGHLIGHT)

        self.__currentOptions=options

    def __filterOptionModified(self):
        """A filter option has been modified"""
        filtered=[]
        if not self.__actionFilterTypeError.isChecked():
            filtered.append(WConsoleType.ERROR)
        if not self.__actionFilterTypeWarning.isChecked():
            filtered.append(WConsoleType.WARNING)
        if not self.__actionFilterTypeInfo.isChecked():
            filtered.append(WConsoleType.INFO)
        if not self.__actionFilterTypeValid.isChecked():
            filtered.append(WConsoleType.VALID)
        self.__console.setOptionFilteredTypes(filtered)

    def search(self):
        """Return current applied filter"""
        return self.__search

    def option(self, optionId):
        """Return current option value

        Option Id refer to:                                                 Returned Value
            BSDockWidgetConsoleOutput.OPTION_BTN_REGEX                      Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE              Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD                   Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW                 Boolean
            BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH                     String
            BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES                   List
            BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR                      Boolean
        """
        if optionId&BSDockWidgetConsoleOutput.OPTION_BTN_REGEX==BSDockWidgetConsoleOutput.OPTION_BTN_REGEX:
            return self.__siSearch.options()&SearchOptions.REGEX==SearchOptions.REGEX
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE==BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE:
            return self.__siSearch.options()&SearchOptions.CASESENSITIVE==SearchOptions.CASESENSITIVE
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD==BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD:
            return self.__siSearch.options()&SearchOptions.WHOLEWORD==SearchOptions.WHOLEWORD
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD==BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD:
            return self.__siSearch.options()&SearchOptions.BACKWARD==SearchOptions.BACKWARD
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT==BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT:
            return self.__siSearch.options()&SearchOptions.HIGHLIGHT==SearchOptions.HIGHLIGHT
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW==BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW:
            return self.__siSearch.options()&WSearchInput.OPTION_STATE_BUTTONSHOW==WSearchInput.OPTION_STATE_BUTTONSHOW
        elif optionId&BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH==BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH:
            return self.__siSearch.searchText()
        elif optionId&BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES==BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES:
            returned=[]
            if self.__actionFilterTypeError.isChecked():
                returned.append(WConsoleType.ERROR)
            if self.__actionFilterTypeWarning.isChecked():
                returned.append(WConsoleType.WARNING)
            if self.__actionFilterTypeInfo.isChecked():
                returned.append(WConsoleType.INFO)
            if self.__actionFilterTypeValid.isChecked():
                returned.append(WConsoleType.VALID)
            return returned
        elif optionId&BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR==BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR:
            return self.__actionAutoClear.isChecked()

    def setOption(self, optionId, value):
        """Set option value

        Option Id refer to:                                                 Value
            BSDockWidgetConsoleOutput.OPTION_BTN_REGEX                      Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE              Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD                   Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT                  Boolean
            BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW                 Boolean
            BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH                     String
            BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES                   List
            BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR                      Boolean
        """
        if optionId&BSDockWidgetConsoleOutput.OPTION_BTN_REGEX==BSDockWidgetConsoleOutput.OPTION_BTN_REGEX:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|SearchOptions.REGEX)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^SearchOptions.REGEX))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE==BSDockWidgetConsoleOutput.OPTION_BTN_CASESENSITIVE:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|SearchOptions.CASESENSITIVE)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^SearchOptions.CASESENSITIVE))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD==BSDockWidgetConsoleOutput.OPTION_BTN_WHOLEWORD:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|SearchOptions.WHOLEWORD)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^SearchOptions.WHOLEWORD))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD==BSDockWidgetConsoleOutput.OPTION_BTN_BACKWARD:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|SearchOptions.BACKWARD)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^SearchOptions.BACKWARD))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT==BSDockWidgetConsoleOutput.OPTION_BTN_HIGHLIGHT:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|SearchOptions.HIGHLIGHT)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^SearchOptions.HIGHLIGHT))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW==BSDockWidgetConsoleOutput.OPTION_BTN_BUTTONSHOW:
            if value:
                self.__siSearch.setOptions(self.__siSearch.options()|WSearchInput.OPTION_STATE_BUTTONSHOW)
            else:
                self.__siSearch.setOptions(self.__siSearch.options()&(WSearchInput.OPTION_ALL^WSearchInput.OPTION_STATE_BUTTONSHOW))
        elif optionId&BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH==BSDockWidgetConsoleOutput.OPTION_TXT_SEARCH:
            self.__siSearch.setSearchText(value)
        elif optionId&BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES==BSDockWidgetConsoleOutput.OPTION_FILTER_TYPES:
            self.__actionFilterTypeError.setChecked(WConsoleType.ERROR in value)
            self.__actionFilterTypeWarning.setChecked(WConsoleType.WARNING in value)
            self.__actionFilterTypeInfo.setChecked(WConsoleType.INFO in value)
            self.__actionFilterTypeValid.setChecked(WConsoleType.VALID in value)
        elif optionId&BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR==BSDockWidgetConsoleOutput.OPTION_AUTOCLEAR:
            self.__actionAutoClear.setChecked(value)
