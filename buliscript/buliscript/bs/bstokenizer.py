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

# Buli Script language definition

from PyQt5.Qt import *

from .bslist import BSList

import re

from .bstheme import BSTheme


class BSTokenFamily:
    # define token family identifiers
    TOKEN_STRING = 0
    TOKEN_NUMBER = 1
    TOKEN_COMMENT = 2
    TOKEN_ACTION = 3
    TOKEN_FLOW = 4
    TOKEN_FUNCTION = 5
    TOKEN_OPERATOR = 6
    TOKEN_VARIABLE_INTERNAL = 7
    TOKEN_VARIABLE_USERDEFINED = 8
    TOKEN_BRACES = 9
    TOKEN_UNCOMPLETE = 10
    TOKEN_UNCOMPLETEFLOW = 11
    TOKEN_UNCOMPLETEFUNCTION = 12
    TOKEN_CONSTANT = 13
    TOKEN_UNKNOWN = 14
    TOKEN_SPACE_NL = 15
    TOKEN_SPACE_WC = 16
    TOKEN_COLOR = 17

    @staticmethod
    def letter(family):
        """Return a letter that define a family"""
        if family == BSTokenFamily.TOKEN_ACTION:
            return "Action"
        elif family == BSTokenFamily.TOKEN_CONSTANT:
            return "Const."
        elif family == BSTokenFamily.TOKEN_FLOW:
            return "Flow"
        elif family == BSTokenFamily.TOKEN_FUNCTION:
            return "Func."
        elif family == BSTokenFamily.TOKEN_VARIABLE_INTERNAL:
            return "Var."
        elif family == BSTokenFamily.TOKEN_VARIABLE_USERDEFINED:
            return "Var."
        else:
            return ""


class BSTokenFamilyStyle:
    """Define styles applied for tokens families"""

    def __init__(self):
        """Initialise token family"""
        self.__currentThemeId = BSTheme.DARK_THEME

        # define default styles for tokens
        self.__tokenStyles = {}

        styles = {
                BSTheme.DARK_THEME: [
                        (BSTokenFamily.TOKEN_STRING, '#9ac07c', False, False),
                        (BSTokenFamily.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSTokenFamily.TOKEN_COLOR, '#c9986a', False, False),
                        (BSTokenFamily.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSTokenFamily.TOKEN_ACTION, '#e5dd82', True, False),
                        (BSTokenFamily.TOKEN_FLOW, '#c278da', True, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True, None, i18n('Flow instruction is not complete')),
                        (BSTokenFamily.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETEFUNCTION, '#6aafec', False, True),
                        (BSTokenFamily.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSTokenFamily.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSTokenFamily.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSTokenFamily.TOKEN_BRACES, '#c278da', False, False),
                        (BSTokenFamily.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETE, '#884823', False, True, '#b07f63', i18n('Action instruction is not complete')),
                        (BSTokenFamily.TOKEN_UNKNOWN, '#d85151', True, True, '#7b1b1b'),
                        (BSTokenFamily.TOKEN_SPACE_WC, None, False, False),
                        (BSTokenFamily.TOKEN_SPACE_NL, None, False, False)
                    ],
                BSTheme.LIGHT_THEME: [
                        (BSTokenFamily.TOKEN_STRING, '#9ac07c', False, False),
                        (BSTokenFamily.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSTokenFamily.TOKEN_COLOR, '#c9986a', False, False),
                        (BSTokenFamily.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSTokenFamily.TOKEN_ACTION, '#FFFF00', True, False),
                        (BSTokenFamily.TOKEN_FLOW, '#c278da', True, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True),
                        (BSTokenFamily.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETEFUNCTION, '#6aafec', False, True),
                        (BSTokenFamily.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSTokenFamily.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSTokenFamily.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSTokenFamily.TOKEN_BRACES, '#c278da', False, False),
                        (BSTokenFamily.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSTokenFamily.TOKEN_UNCOMPLETE, '#FFFF88', False, True, '#ffb770'),
                        (BSTokenFamily.TOKEN_UNKNOWN, '#880000', True, True, '#d29090'),
                        (BSTokenFamily.TOKEN_SPACE_WC, None, False, False),
                        (BSTokenFamily.TOKEN_SPACE_NL, None, False, False)
                    ]
            }

        for style in styles:
            for definition in styles[style]:
                self.setStyle(style, *definition)

    def style(self, type):
        """Return style to apply for a token family"""
        if isinstance(type, int):
            if type in self.__tokenStyles[self.__currentThemeId]:
                return self.__tokenStyles[self.__currentThemeId][type]
        # in all other case, token style is not known...
        return self.__tokenStyles[self.__currentThemeId][BSTokenFamily.TOKEN_UNKNOWN]

    def setStyle(self, themeId, tokenFamily, fgColor, bold, italic, bgColor=None, tooltip=None):
        """Define style for a token family"""
        textFmt = QTextCharFormat()
        textFmt.setFontItalic(italic)
        if bold:
            textFmt.setFontWeight(QFont.Bold)

        if not fgColor is None:
            textFmt.setForeground(QColor(fgColor))
        if not bgColor is None:
            textFmt.setBackground(QColor(bgColor))
        if not tooltip is None:
            textFmt.setToolTip(tooltip)

        if not themeId in self.__tokenStyles:
            self.__tokenStyles[themeId]={}

        self.__tokenStyles[themeId][tokenFamily]=textFmt

    def theme(self):
        """Return current defined theme"""
        return self.__currentThemeId

    def setTheme(self, themeId):
        """Set current theme

        If theme doesn't exist, current theme is not changed"""
        if themeId in self.__currentThemeId:
            self.__currentThemeId=themeId


class BSTokenizerRule:
    """Define a rule for tokenizer"""
    def __init__(self, languageDef, regEx, type, family, asReadableText=None):
        if isinstance(regEx, str):
            regEx = QRegularExpression(regEx, QRegularExpression.CaseInsensitiveOption)
        if not regEx.isValid():
            print("invalid regex", regEx.pattern(), type)
        self.__regEx = regEx
        self.__type = type
        self.__languageDef = languageDef
        self.__readableTextList = []
        self.__family = family

        if isinstance(asReadableText, str):
            self.__readableTextList=[asReadableText]
        elif isinstance(asReadableText, list):
            self.__readableTextList=[text for text in asReadableText if isinstance(text, str)]

    def __repr__(self):
        return f"<BSTokenizerRule({self.__regEx.pattern()}, {self.__type})>"

    def regEx(self):
        """Return regular expression for rule (as QRegularExpression)"""
        return self.__regEx

    def type(self):
        """Return type for rule"""
        return self.__type

    def family(self):
        """Return family for rule"""
        return self.__family

    def readableTextList(self):
        """Return rule as a readable text (return list of str, or None if there's no text representation)"""
        return self.__readableTextList

    def matchText(self, matchText):
        """Return rule as a readable text (return list of tuple (str, rule), or empty list if there's no text representation) and
        that match the given `matchText`

        given `matchText` can be a str or a regular expression
        """
        returned=[]
        if isinstance(matchText, str):
            matchText=re.compile(re.escape(re.sub('\s+', '\x01', matchText)).replace('\x01', r'\s+'))

        if isinstance(matchText, re.Pattern):
            for text in self.__readableTextList:
                if matchText.match(text):
                    returned.append((text, self))

        return returned


class BSToken:
    """A token"""
    __LINE_NUMBER = 0
    __LINE_POSSTART = 0

    @staticmethod
    def resetTokenizer():
        BSToken.__LINE_NUMBER = 1
        BSToken.__LINE_POSSTART = 0

    def __init__(self, text, rule, positionStart, positionEnd, length):
        self.__text = text.lstrip()
        self.__rule = rule
        self.__positionStart=positionStart
        self.__positionEnd=positionEnd
        self.__length=length
        self.__lineNumber=BSToken.__LINE_NUMBER
        self.__linePositionStart=(positionStart - BSToken.__LINE_POSSTART)+1
        self.__linePositionEnd=self.__linePositionStart + length
        self.__next = None
        self.__previous = None

        if self.__rule.family()==BSTokenFamily.TOKEN_SPACE_NL:
            self.__indent=0
            BSToken.__LINE_NUMBER+=1
            BSToken.__LINE_POSSTART=positionEnd
        else:
            self.__indent=len(text) - len(self.__text)

    def __repr__(self):
        if self.__rule.family()==BSTokenFamily.TOKEN_SPACE_NL:
            txt=''
        else:
            txt=self.__text
        return (f"<BSToken({self.__indent}, '{txt}', Type[{self.type()}], Family[{self.family()}], "
                f"Length: {self.__length}, "
                f"Global[Start: {self.__positionStart}, End: {self.__positionEnd}], "
                f"Line[Start: {self.__linePositionStart}, End: {self.__linePositionEnd}, Number: {self.__lineNumber}])>")

    def type(self):
        """return token type"""
        return self.__rule.type()

    def family(self):
        """return token family"""
        return self.__rule.family()

    def style(self):
        """return token style"""
        return self.__rule.style()

    def isUnknown(self):
        """return if it's an unknown token"""
        return (self.__rule.family() == BSTokenFamily.TOKEN_UNKNOWN)

    def positionStart(self):
        """Return position (start) in text"""
        return self.__positionStart

    def positionEnd(self):
        """Return position (end) in text"""
        return self.__positionEnd

    def length(self):
        """Return text length"""
        return self.__length

    def indent(self):
        """Return token indentation"""
        return self.__indent

    def text(self):
        """Return token text"""
        return self.__text

    def rule(self):
        """Return token rule"""
        return self.__rule

    def setNext(self, token=None):
        """Set next token"""
        self.__next = token

    def setPrevious(self, token=None):
        """Set previous token"""
        self.__previous = token

    def next(self):
        """Return next token, or None if current token is the last one"""
        return self.__next

    def previous(self):
        """Return previous token, or None if current token is the last one"""
        return self.__previous


class BSTokenizer:
    """A tokenizer, using language definition"""
    def __init__(self):
        """Intialise tokenizer"""
        # internal storage for rules (list of BSTokenizerRule)
        self.__rules = []

        # a global regEx with all rules
        self.__regEx = None

        # a flag to determinate if regular expression need to be updated
        self.__needUpdate = True

    def add(self, rule):
        """Add a new rule for tokenizer

        A `rule` is a BSTokenizerRule
        """
        self.__rules.append(rule)
        self.__needUpdate = True

    def regEx(self):
        """Return current built regular expression used for lexer"""
        if self.__needUpdate:
            self.__needUpdate = False
            self.__regEx=QRegularExpression('|'.join([rule.regEx().pattern() for rule in self.__rules]), QRegularExpression.CaseInsensitiveOption|QRegularExpression.MultilineOption)

        return self.__regEx

    def rules(self):
        """Return all language rules as a list of BSTokenizerRule"""
        return self.__rules

    def tokenize(self, text):
        """Return tokenized text as BSList

        Each list item is BSToken object
        """
        matchIterator = self.regEx().globalMatch(text)

        BSToken.resetTokenizer()

        previousToken = None
        returned=[]
        # iterate all found tokens
        while matchIterator.hasNext():
            match = matchIterator.next()

            if match.hasMatch():
                for textIndex in range(len(match.capturedTexts())):
                    value = match.captured(textIndex)

                    position = 0
                    for rule in self.__rules:
                        ruleMatch = rule.regEx().match(value)
                        if ruleMatch.hasMatch():
                            token = BSToken(match.captured(textIndex), rule,
                                                    match.capturedStart(textIndex),
                                                    match.capturedEnd(textIndex),
                                                    match.capturedLength(textIndex))
                            token.setPrevious(previousToken)
                            if not previousToken is None:
                                previousToken.setNext(token)
                            returned.append(token)
                            previousToken=token
                            # do not need to continue to check for another token type
                            break
        return BSList(returned)


