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

class BSLanguageRule:
    """Define a rule for language"""
    def __init__(self, languageDef, regEx, type, asText=None):
        if isinstance(regEx, str):
            regEx = QRegularExpression(regEx, QRegularExpression.CaseInsensitiveOption)
        if not regEx.isValid():
            print("invalid regex", regEx.pattern(), type)
        self.__regEx = regEx
        self.__type = type
        self.__languageDef = languageDef
        self.__asText = []

        if isinstance(asText, str):
            self.__asText=[asText]
        elif isinstance(asText, list):
            self.__asText=[text for text in asText if isinstance(text, str)]

    def __repr__(self):
        return f"<BSLanguageRule({self.__regEx.pattern()}, {self.__type})>"

    def regEx(self):
        """Return regular expression for rule"""
        return self.__regEx

    def type(self):
        """Return type for rule"""
        return self.__type

    def familly(self):
        """Return familly for rule"""
        return self.__languageDef.familly(self.__type)

    def style(self):
        """Return style for rule"""
        return self.__languageDef.style(self.__type)

    def asText(self):
        """Return rule as a readable text (return list of str, or None if there's no text representation)"""
        return self.__asText

    def matchText(self, matchText):
        """Return rule as a readable text (return list of tuple (str, rule), or empty list if there's no text representation) and
        that match the given `matchText`

        given `matchText` can be a str or a regular expression
        """
        returned=[]
        if isinstance(matchText, str):
            matchText=re.compile(re.escape(re.sub('\s+', '\x01', matchText)).replace('\x01', r'\s+'))

        if isinstance(matchText, re.Pattern):
            for text in self.__asText:
                if matchText.match(text):
                    returned.append((text, self))

        return returned


class BSLanguageToken:
    """A token"""
    __LINE_NUMBER = 0
    __LINE_POSSTART = 0

    @staticmethod
    def resetTokenizer():
        BSLanguageToken.__LINE_NUMBER = 1
        BSLanguageToken.__LINE_POSSTART = 0

    def __init__(self, text, rule, positionStart, positionEnd, length):
        self.__text = text.lstrip()
        self.__rule = rule
        self.__positionStart=positionStart
        self.__positionEnd=positionEnd
        self.__length=length
        self.__lineNumber=BSLanguageToken.__LINE_NUMBER
        self.__linePositionStart=(positionStart - BSLanguageToken.__LINE_POSSTART)+1
        self.__linePositionEnd=self.__linePositionStart + length
        self.__next = None
        self.__previous = None

        if self.__rule.familly()==BSLanguageDef.TOKEN_SPACE_NL:
            self.__indent=0
            BSLanguageToken.__LINE_NUMBER+=1
            BSLanguageToken.__LINE_POSSTART=positionEnd
        else:
            self.__indent=len(text) - len(self.__text)

    def __repr__(self):
        if self.__rule.familly()==BSLanguageDef.TOKEN_SPACE_NL:
            txt=''
        else:
            txt=self.__text
        return (f"<BSLanguageToken({self.__indent}, '{txt}', Type[{self.type()}], Familly[{self.familly()}], "
                f"Length: {self.__length}, "
                f"Global[Start: {self.__positionStart}, End: {self.__positionEnd}], "
                f"Line[Start: {self.__linePositionStart}, End: {self.__linePositionEnd}, Number: {self.__lineNumber}])>")

    def type(self):
        """return token type"""
        return self.__rule.type()

    def familly(self):
        """return token familly"""
        return self.__rule.familly()

    def style(self):
        """return token style"""
        return self.__rule.style()

    def isUnknown(self):
        """return if it's an unknown token"""
        return (self.__rule.familly() == BSLanguageDef.TOKEN_UNKNOWN)

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


class BSLanguageDef:
    # define token familly identifiers
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

    # define token types
    ACTION_ID_UNCOMPLETE = 'uncomplete'
    ACTION_ID_SET = 'set'
    ACTION_ID_SET_UNIT = 'setUnit'
    ACTION_ID_SET_PEN = 'setPen'
    ACTION_ID_SET_FILL = 'setFill'
    ACTION_ID_SET_TEXT = 'setText'
    ACTION_ID_SET_PAPER = 'setPaper'
    ACTION_ID_SET_CANVAS = 'setCanvas'
    ACTION_ID_SET_LAYER = 'setLayer'
    ACTION_ID_SET_SELECTION = 'setSelection'
    ACTION_ID_SET_EXECUTION = 'setExecution'

    ACTION_ID_DRAW = 'draw'
    ACTION_ID_FILL = 'fill'
    ACTION_ID_PEN = 'pen'

    ACTION_ID_MOVE = 'move'
    ACTION_ID_TURN = 'turn'

    ACTION_ID_POP = 'pop'
    ACTION_ID_PUSH = 'push'

    ACTION_ID_FILTER = 'filter'

    ACTION_ID_CANVAS = 'canvas'

    ACTION_ID_DOCUMENT = 'document'
    ACTION_ID_LAYER = 'layer'
    ACTION_ID_SELECTION = 'selection'

    ACTION_ID_CONSOLE = 'console'
    ACTION_ID_DIALOG = 'dialog'

    ACTION_ID_FLOW = 'flow'
    ACTION_ID_UNCOMPLETEFLOW = 'uncompleteFlow'

    VARIABLE_ID = 'var'
    VARIABLE_ID_INTERNAL = 'varint'

    CONSTANT_ID_SETONOFF = 'constSetOnOff'
    CONSTANT_ID_SETUNITCOORD = 'constSetUnitCoord'
    CONSTANT_ID_SETUNITROT = 'constSetUnitRot'
    CONSTANT_ID_SETPENSTYLE = 'constSetPenStyle'
    CONSTANT_ID_SETPENCAP = 'constSetPenCap'
    CONSTANT_ID_SETPENJOIN = 'constSetPenJoin'
    CONSTANT_ID_SETFILLRULE = 'constSetFillRule'
    CONSTANT_ID_SETTXTHALIGN = 'constSetTxtHAlign'
    CONSTANT_ID_SETTXTVALIGN = 'constSetTxtVAlign'
    CONSTANT_ID_SETPAPERBLEND = 'constSetPaperBlend'
    CONSTANT_ID_SETSELECTMODE = 'constSetSelectMode'

    FUNCTION_ID_MATH = 'funcMath'
    FUNCTION_ID_STR = 'funcStr'
    FUNCTION_ID_COLOR = 'funcColor'
    FUNCTION_ID_UNCOMPLETE = 'uncompleteFunc'

    OPERATORS_ID = 'operator'
    SEPARATOR_ID = 'separator'
    BRACES_ID_PARENTHESIS_OPEN = 'bracesParenthesisO'
    BRACES_ID_PARENTHESIS_CLOSE = 'bracesParenthesisC'

    TYPE_STRING = 'typeStr'
    TYPE_NUMBER = 'typeNum'
    TYPE_COLOR = 'typeCol'

    SPACE_NL = 'spNl'
    SPACE_WC = 'spWc'

    COMMENT = 'comment'

    UNKNOWN = 'unknown'

    # styles identifier
    STYLE_DARK = 'dark'
    STYLE_LIGHT = 'light'

    def __init__(self):
        """Initialise language & styles"""
        # internal storage for rules (list of BSLanguageRule)
        self.__rules = []
        # a global regEx with all rules
        self.__regEx = None

        # styles => relation between a TOKEN type and TOKEN familly
        self.__tokenFamillies = {}
        # stylesDef => define styles applied for token
        self.__tokenStyles = {}
        #
        self.__currentStyleId = 'dark'

        self.__initialiseRules()
        self.__initialiseStyles()


    def __initialiseRules(self):
        """set language rules"""
        rules = [   (r'"[^"\\]*(?:\\.[^"\\]*)*"', BSLanguageDef.TYPE_STRING, None),
                    (r"'[^'\\]*(?:\\.[^'\\]*)*'", BSLanguageDef.TYPE_STRING, None),

                    (r"\n", BSLanguageDef.SPACE_NL, None),

                    (r'#(?:\b[a-f0-9]{6}\b|[a-f0-9]{8}\b)', BSLanguageDef.TYPE_COLOR, None),
                    (r'#[^\n]*', BSLanguageDef.COMMENT, None),

                    (r"-?(?:\d+\.\d*|\.\d+|\d+)", BSLanguageDef.TYPE_NUMBER, None),

                    (r"^\s*\bset\s+unit\s+coordinates\b", BSLanguageDef.ACTION_ID_SET_UNIT, "set unit coordinates"),
                    (r"^\s*\bset\s+unit\s+rotation\b", BSLanguageDef.ACTION_ID_SET_UNIT, "set unit rotation"),
                    (r"^\s*\bset\s+unit\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+pen\s+color\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen color"),
                    (r"^\s*\bset\s+pen\s+width\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen width"),
                    (r"^\s*\bset\s+pen\s+style\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen style"),
                    (r"^\s*\bset\s+pen\s+cap\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen cap"),
                    (r"^\s*\bset\s+pen\s+join\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen join"),
                    (r"^\s*\bset\s+pen\s+brush\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen brush"),
                    (r"^\s*\bset\s+pen\s+opacity\b", BSLanguageDef.ACTION_ID_SET_PEN, "set pen opacity"),
                    (r"^\s*\bset\s+pen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+fill\s+color\b", BSLanguageDef.ACTION_ID_SET_FILL, "set fill color"),
                    (r"^\s*\bset\s+fill\s+brush\b", BSLanguageDef.ACTION_ID_SET_FILL, "set fill brush"),
                    (r"^\s*\bset\s+fill\s+rule\b", BSLanguageDef.ACTION_ID_SET_FILL, "set fill rule"),
                    (r"^\s*\bset\s+fill\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+text\s+font\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text font"),
                    (r"^\s*\bset\s+text\s+size\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text size"),
                    (r"^\s*\bset\s+text\s+bold\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text bold"),
                    (r"^\s*\bset\s+text\s+italic\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text italic"),
                    (r"^\s*\bset\s+text\s+letter\s+spacing\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text letter spacing"),
                    (r"^\s*\bset\s+text\s+letter\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+text\s+stretch\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text stretch"),
                    (r"^\s*\bset\s+text\s+color\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text color"),
                    (r"^\s*\bset\s+text\s+align\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text align"),
                    (r"^\s*\bset\s+text\s+position\b", BSLanguageDef.ACTION_ID_SET_TEXT, "set text position"),
                    (r"^\s*\bset\s+text\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+paper\s+antialiasing\b", BSLanguageDef.ACTION_ID_SET_PAPER, "set paper antialiasing"),
                    (r"^\s*\bset\s+paper\s+blending\b", BSLanguageDef.ACTION_ID_SET_PAPER, "set paper blending"),
                    (r"^\s*\bset\s+paper\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+canvas\s+grid\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas grid color"),
                    (r"^\s*\bset\s+canvas\s+grid\s+width\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas grid width"),
                    (r"^\s*\bset\s+canvas\s+grid\s+style\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas grid style"),
                    (r"^\s*\bset\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+canvas\s+origin\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas origin color"),
                    (r"^\s*\bset\s+canvas\s+origin\s+width\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas origin width"),
                    (r"^\s*\bset\s+canvas\s+origin\s+style\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas origin style"),
                    (r"^\s*\bset\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+canvas\s+position\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS, "set canvas position color"),
                    (r"^\s*\bset\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+layer\s+opacity\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer opacity"),
                    (r"^\s*\bset\s+layer\s+name\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer name"),
                    (r"^\s*\bset\s+layer\s+visible\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer visible"),
                    (r"^\s*\bset\s+layer\s+lock\s+alpha\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer lock alpha"),
                    (r"^\s*\bset\s+layer\s+lock\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+layer\s+inherit\s+alpha\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer inherit alpha"),
                    (r"^\s*\bset\s+layer\s+inherit\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+layer\s+blending\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer blending"),
                    (r"^\s*\bset\s+layer\s+color\s+label\b", BSLanguageDef.ACTION_ID_SET_LAYER, "set layer color label"),
                    (r"^\s*\bset\s+layer\s+color\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bset\s+layer\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+select\s+mode\b", BSLanguageDef.ACTION_ID_SET_SELECTION, "set select mode"),
                    (r"^\s*\bset\s+select\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\s+execution\s+verbose\b", BSLanguageDef.ACTION_ID_SET_EXECUTION, "set execution verbose"),
                    (r"^\s*\bset\s+execution\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bset\b", BSLanguageDef.ACTION_ID_SET, "set"),


                    (r"^\s*\bdraw\s+square\b", BSLanguageDef.ACTION_ID_DRAW, "draw square"),
                    (r"^\s*\bdraw\s+round\s+square\b", BSLanguageDef.ACTION_ID_DRAW, "draw round square"),
                    (r"^\s*\bdraw\s+rect\b", BSLanguageDef.ACTION_ID_DRAW, "draw rect"),
                    (r"^\s*\bdraw\s+round\s+rect\b", BSLanguageDef.ACTION_ID_DRAW, "draw round rect"),
                    (r"^\s*\bdraw\s+circle\b", BSLanguageDef.ACTION_ID_DRAW, "draw circle"),
                    (r"^\s*\bdraw\s+ellipse\b", BSLanguageDef.ACTION_ID_DRAW, "draw ellipse"),
                    (r"^\s*\bdraw\s+dot\b", BSLanguageDef.ACTION_ID_DRAW, "draw dot"),
                    (r"^\s*\bdraw\s+pixel\b", BSLanguageDef.ACTION_ID_DRAW, "draw pixel"),
                    (r"^\s*\bdraw\s+scaled\s+image\b", BSLanguageDef.ACTION_ID_DRAW, "draw scaled image"),
                    (r"^\s*\bdraw\s+image\b", BSLanguageDef.ACTION_ID_DRAW, "draw image"),
                    (r"^\s*\bdraw\s+text\b", BSLanguageDef.ACTION_ID_DRAW, "draw text"),
                    (r"^\s*\bdraw\s+star\b", BSLanguageDef.ACTION_ID_DRAW, "draw star"),
                    (r"^\s*\bdraw\s+arc\b", BSLanguageDef.ACTION_ID_MOVE, "draw arc"),
                    (r"^\s*\bdraw\s+bezier\b", BSLanguageDef.ACTION_ID_MOVE, "draw bezier"),
                    (r"^\s*\bdraw\s+spline\b", BSLanguageDef.ACTION_ID_MOVE, "draw spline"),
                    (r"^\s*\bdraw\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bclear\b", BSLanguageDef.ACTION_ID_DRAW, "clear"),
                    (r"^\s*\bapply\b", BSLanguageDef.ACTION_ID_DRAW, "apply"),

                    (r"^\s*\bfill\s+activate\b", BSLanguageDef.ACTION_ID_FILL, "fill activate"),
                    (r"^\s*\bfill\s+deactivate\b", BSLanguageDef.ACTION_ID_FILL, "fill deactivate"),
                    (r"^\s*\bfill\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bpen\s+up\b", BSLanguageDef.ACTION_ID_PEN, "pen up"),
                    (r"^\s*\bpen\s+down\b", BSLanguageDef.ACTION_ID_PEN, "pen down"),
                    (r"^\s*\bpen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bmove\s+home\b", BSLanguageDef.ACTION_ID_MOVE, "move home"),
                    (r"^\s*\bmove\s+forward\b", BSLanguageDef.ACTION_ID_MOVE, "move forward"),
                    (r"^\s*\bmove\s+backward\b", BSLanguageDef.ACTION_ID_MOVE, "move backward"),
                    (r"^\s*\bmove\s+left\b", BSLanguageDef.ACTION_ID_MOVE, "move left"),
                    (r"^\s*\bmove\s+right\b", BSLanguageDef.ACTION_ID_MOVE, "move right"),
                    (r"^\s*\bmove\s+to\b", BSLanguageDef.ACTION_ID_MOVE, "move to"),
                    (r"^\s*\bmove\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bturn\s+left\b", BSLanguageDef.ACTION_ID_MOVE, "turn left"),
                    (r"^\s*\bturn\s+right\b", BSLanguageDef.ACTION_ID_MOVE, "turn right"),
                    (r"^\s*\bturn\s+absolute\b", BSLanguageDef.ACTION_ID_MOVE, "turn absolute"),
                    (r"^\s*\bturn\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bpush\s+state\b", BSLanguageDef.ACTION_ID_PUSH, "push state"),
                    (r"^\s*\bpush\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bpop\s+state\b", BSLanguageDef.ACTION_ID_POP, "pop state"),
                    (r"^\s*\bpop\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bfilter\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, "filter"),


                    (r"^\s*\bshow\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_CANVAS, "show canvas grid"),
                    (r"^\s*\bshow\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_CANVAS, "show canvas origin"),
                    (r"^\s*\bshow\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_CANVAS, "show canvas position"),
                    (r"^\s*\bshow\s+canvas\s+background\b", BSLanguageDef.ACTION_ID_CANVAS, "show canvas background"),
                    (r"^\s*\bshow\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bshow\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bhide\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_CANVAS, "hide canvas grid"),
                    (r"^\s*\bhide\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_CANVAS, "hide canvas origin"),
                    (r"^\s*\bhide\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_CANVAS, "hide canvas position"),
                    (r"^\s*\bhide\s+canvas\s+background\b", BSLanguageDef.ACTION_ID_CANVAS, "hide canvas background"),
                    (r"^\s*\bhide\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bhide\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bopen\s+document\b", BSLanguageDef.ACTION_ID_DOCUMENT, "open document"),
                    (r"^\s*\bopen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bsave\s+document\s+as\b", BSLanguageDef.ACTION_ID_CANVAS, "save document as"),
                    (r"^\s*\bsave\s+document\b", BSLanguageDef.ACTION_ID_CANVAS, "save document"),
                    (r"^\s*\bsave\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bcrop\s+document\b", BSLanguageDef.ACTION_ID_CANVAS, "crop document"),
                    (r"^\s*\bcrop\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\badd\s+paint\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "add paint layer"),
                    (r"^\s*\badd\s+paint\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\badd\s+group\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "add group layer"),
                    (r"^\s*\badd\s+group\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\badd\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\buse\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "use layer"),
                    (r"^\s*\buse\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bdelete\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "delete layer"),
                    (r"^\s*\bdelete\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bmerge\s+layer\s+down\b", BSLanguageDef.ACTION_ID_LAYER, "merge layer down"),
                    (r"^\s*\bmerge\s+layer\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bmerge\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\brotate\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "rotate layer"),
                    (r"^\s*\brotate\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bshear\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "shear layer"),
                    (r"^\s*\bshear\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\btranslate\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "translate layer"),
                    (r"^\s*\btranslate\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bscale\s+layer\b", BSLanguageDef.ACTION_ID_LAYER, "scale layer"),
                    (r"^\s*\bscale\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bselect\s+all\b", BSLanguageDef.ACTION_ID_SELECTION, "select all"),
                    (r"^\s*\bselect\s+none\b", BSLanguageDef.ACTION_ID_SELECTION, "select none"),
                    (r"^\s*\bselect\s+invert\b", BSLanguageDef.ACTION_ID_SELECTION, "select invert"),
                    (r"^\s*\bselect\s+alpha\b", BSLanguageDef.ACTION_ID_SELECTION, "select alpha"),
                    (r"^\s*\bselect\s+region\b", BSLanguageDef.ACTION_ID_SELECTION, "select region"),
                    (r"^\s*\bselect\s+area\b", BSLanguageDef.ACTION_ID_SELECTION, "select area"),
                    (r"^\s*\bselect\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),

                    (r"^\s*\bstop\b", BSLanguageDef.ACTION_ID_FLOW, "stop"),
                    (r"^\s*\bimport\s+macro\sfrom\b", BSLanguageDef.ACTION_ID_FLOW, "import macro from"),
                    (r"^\s*\bimport\s+macro\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bimport\s+image\sfrom\b", BSLanguageDef.ACTION_ID_FLOW, "import image from"),
                    (r"^\s*\bimport\s+image\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bimport\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\brepeat\b", BSLanguageDef.ACTION_ID_FLOW, "repeat"),
                    (r"^\s*\bfor\s+each\b", BSLanguageDef.ACTION_ID_FLOW, "for each"),
                    (r"^\s*\bfor\b", BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW, None),
                    (r"^\s*\bcall\b", BSLanguageDef.ACTION_ID_FLOW, "call"),
                    (r"^\s*\bdefine\s+macro\b", BSLanguageDef.ACTION_ID_FLOW, "define macro"),
                    (r"^\s*\bdefine\b", BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW, None),
                    (r"^\s*\breturn\b", BSLanguageDef.ACTION_ID_FLOW, "return"),
                    (r"\btimes\b", BSLanguageDef.ACTION_ID_FLOW, "times"),
                    (r"\bin\b", BSLanguageDef.ACTION_ID_FLOW, "in"),
                    (r"\bas\b", BSLanguageDef.ACTION_ID_FLOW, "as"),

                    (r"\b{0}\b".format(r'\b|\b'.join(['ON','OFF'])), BSLanguageDef.CONSTANT_ID_SETONOFF, ['ON','OFF']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['PIXEL','PERCENTAGE','MM','INCH'])), BSLanguageDef.CONSTANT_ID_SETUNITCOORD, ['PIXEL','PERCENTAGE','MM','INCH']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['RADIAN','DEGREE'])), BSLanguageDef.CONSTANT_ID_SETUNITROT, ['RADIAN','DEGREE']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['SOLID','DASH','DOT','DASHDOT','NONE'])), BSLanguageDef.CONSTANT_ID_SETPENSTYLE, ['SOLID','DASH','DOT','DASHDOT','NONE']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['SQUARE','FLAT','ROUND'])), BSLanguageDef.CONSTANT_ID_SETPENCAP, ['SQUARE','FLAT','ROUND']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['BEVEL','MITTER','ROUND'])), BSLanguageDef.CONSTANT_ID_SETPENJOIN, ['BEVEL','MITTER','ROUND']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['EVEN','PLAIN'])), BSLanguageDef.CONSTANT_ID_SETFILLRULE, ['EVEN','PLAIN']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['LEFT','CENTER','RIGHT'])), BSLanguageDef.CONSTANT_ID_SETTXTHALIGN, ['LEFT','CENTER','RIGHT']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['TOP','MIDDLE','BOTTOM'])), BSLanguageDef.CONSTANT_ID_SETTXTVALIGN, ['TOP','MIDDLE','BOTTOM']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['NORMAL','SOURCE_OVER',
                                                      'DESTINATION_OVER','CLEAR',
                                                      'SOURCE_IN','SOURCE_OUT',
                                                      'DESTINATION_IN','DESTINATION_OUT',
                                                      'SOURCE_ATOP','DESTINATION_ATOP','XOR',
                                                      'PLUS','MULTIPLY','SCREEN','OVERLAY','DARKEN',
                                                      'LIGHTEN','COLORDODGE','COLORBURN',
                                                      'HARD_LIGHT','SOFT_LIGHT',
                                                      'DIFFERENCE','EXCLUSION'])), BSLanguageDef.CONSTANT_ID_SETPAPERBLEND,
                                                     ['NORMAL','SOURCE_OVER',
                                                      'DESTINATION_OVER','CLEAR',
                                                      'SOURCE_IN','SOURCE_OUT',
                                                      'DESTINATION_IN','DESTINATION_OUT',
                                                      'SOURCE_ATOP','DESTINATION_ATOP','XOR',
                                                      'PLUS','MULTIPLY','SCREEN','OVERLAY','DARKEN',
                                                      'LIGHTEN','COLORDODGE','COLORBURN',
                                                      'HARD_LIGHT','SOFT_LIGHT',
                                                      'DIFFERENCE','EXCLUSION']),
                    (r"\b{0}\b".format(r'\b|\b'.join(['REPLACE','ADD','SUBSTRACT'])), BSLanguageDef.CONSTANT_ID_SETSELECTMODE, ['REPLACE','ADD','SUBSTRACT']),

                    (r"^\s*\bdialog\s+message\b", BSLanguageDef.ACTION_ID_DIALOG, "dialog message"),
                    (r"^\s*\bdialog\s+question\b", BSLanguageDef.ACTION_ID_DIALOG, "dialog question"),
                    (r"^\s*\bdialog\s+input\b", BSLanguageDef.ACTION_ID_DIALOG, "dialog input"),
                    (r"^\s*\bdialog\b", BSLanguageDef.ACTION_ID_UNCOMPLETE, None),
                    (r"^\s*\bprint\b", BSLanguageDef.ACTION_ID_CONSOLE, "print"),
                    (r"^\s*\binput\b", BSLanguageDef.ACTION_ID_CONSOLE, "input"),

                    (r":\bposition\.x\b", BSLanguageDef.VARIABLE_ID_INTERNAL, ':position.x'),
                    (r":\bposition\.y\b", BSLanguageDef.VARIABLE_ID_INTERNAL, ":position.y"),
                    (r":\bangle\b", BSLanguageDef.VARIABLE_ID_INTERNAL, ":angle"),
                    (r":\bunit\.(?:rotation|coordinates)\b", BSLanguageDef.VARIABLE_ID_INTERNAL, [':unit.rotation', ':unit.coordinates']),
                    (r":\bpen\.(?:color|width|style|cap|join|brush|opacity|status)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':pen.color',
                                                     ':pen.width',
                                                     ':pen.style',
                                                     ':pen.cap',
                                                     ':pen.join',
                                                     ':pen.brush',
                                                     ':pen.opacity',
                                                     ':pen.status'
                                                    ]),
                    (r":\bfill\.(?:color|brush|rule|status)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':fill.color',
                                                     ':fill.brush',
                                                     ':fill.rule',
                                                     ':fill.status'
                                                    ]),
                    (r":\btext\.(?:font|size|bold|italic|outline|letter_spacing|stretch|color|align|position)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':text.font',
                                                     ':text.size',
                                                     ':text.bold',
                                                     ':text.italic',
                                                     ':text.outline',
                                                     ':text.letter_spacing',
                                                     ':text.stretch',
                                                     ':text.color',
                                                     ':text.align',
                                                     ':text.position'
                                                    ]),
                    (r":\bcanvas\.grid\.(?:status|color|width|style)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':canvas.grid.color',
                                                     ':canvas.grid.width',
                                                     ':canvas.grid.style',
                                                     ':canvas.grid.status'
                                                    ]),
                    (r":\bcanvas\.origin\.(?:status|color|width|style)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':canvas.origin.color',
                                                     ':canvas.origin.width',
                                                     ':canvas.origin.style',
                                                     ':canvas.origin.status'
                                                    ]),
                    (r":\bcanvas\.position\.(?:status|color|size)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':canvas.position.color',
                                                     ':canvas.position.size',
                                                     ':canvas.position.status'
                                                    ]),
                    (r":\brepeat\.(?:current|total|incAngle|currentAngle)\b", BSLanguageDef.VARIABLE_ID_INTERNAL,
                                                    [':repeat.current',
                                                     ':repeat.total',
                                                     ':repeat.incAngle',
                                                     ':repeat.currentAngle'
                                                    ]),
                    (r":\b[a-z][a-z0-9\-\._]*\b", BSLanguageDef.VARIABLE_ID, None),

                    (r"\bmath\.(?:cosinus|sinus|tangent|ceil|floor|round|square_root|random)\b", BSLanguageDef.FUNCTION_ID_MATH,
                                                    ['math.cosinus',
                                                     'math.sinus',
                                                     'math.tangent',
                                                     'math.ceil',
                                                     'math.floor',
                                                     'math.round',
                                                     'math.square_root',
                                                     'math.random'
                                                    ]),
                    (r"\bmath\.", BSLanguageDef.FUNCTION_ID_UNCOMPLETE, None),

                    (r"\bstring\.(?:length|upper|lower)\b", BSLanguageDef.FUNCTION_ID_STR,
                                                    ['string.length',
                                                     'string.upper',
                                                     'string.lower'
                                                    ]),
                    (r"\bstring\.", BSLanguageDef.FUNCTION_ID_UNCOMPLETE, None),

                    (r"\bcolor\.(?:rgba|rgb)\b", BSLanguageDef.FUNCTION_ID_COLOR,
                                                    ['color.rgb',
                                                     'color.rgba'
                                                    ]),
                    (r"\bcolor\.", BSLanguageDef.FUNCTION_ID_UNCOMPLETE, None),

                    (r"\+|-|\*|//|/|%|<=|<|>=|>|!=|==|=", BSLanguageDef.OPERATORS_ID),
                    (r",", BSLanguageDef.SEPARATOR_ID),
                    (r"\(", BSLanguageDef.BRACES_ID_PARENTHESIS_OPEN),
                    (r"\)", BSLanguageDef.BRACES_ID_PARENTHESIS_CLOSE),

                    (r"\s+", BSLanguageDef.SPACE_WC),
                    (r"[^\s]+", BSLanguageDef.UNKNOWN)
                ]

        regEx=[]
        for rule in rules:
            regEx.append(rule[0])
            self.__rules.append(BSLanguageRule(self, *rule))

        # main regular expression use for lexer
        self.__regEx=QRegularExpression('|'.join(regEx), QRegularExpression.CaseInsensitiveOption|QRegularExpression.MultilineOption)


    def __initialiseStyles(self):
        """Set language styles (text format for token)"""
        self.__tokenFamillies={
                BSLanguageDef.COMMENT: BSLanguageDef.TOKEN_COMMENT,
                BSLanguageDef.TYPE_STRING: BSLanguageDef.TOKEN_STRING,
                BSLanguageDef.TYPE_NUMBER: BSLanguageDef.TOKEN_NUMBER,
                BSLanguageDef.TYPE_COLOR: BSLanguageDef.TOKEN_COLOR,
                BSLanguageDef.CONSTANT_ID_SETONOFF: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETUNITCOORD: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETUNITROT: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENSTYLE: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENCAP: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENJOIN: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETFILLRULE: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETTXTHALIGN: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETTXTVALIGN: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPAPERBLEND: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETSELECTMODE: BSLanguageDef.TOKEN_CONSTANT,
                BSLanguageDef.VARIABLE_ID: BSLanguageDef.TOKEN_VARIABLE_USERDEFINED,
                BSLanguageDef.VARIABLE_ID_INTERNAL: BSLanguageDef.TOKEN_VARIABLE_INTERNAL,
                BSLanguageDef.OPERATORS_ID: BSLanguageDef.TOKEN_OPERATOR,
                BSLanguageDef.BRACES_ID_PARENTHESIS_OPEN: BSLanguageDef.TOKEN_BRACES,
                BSLanguageDef.BRACES_ID_PARENTHESIS_CLOSE: BSLanguageDef.TOKEN_BRACES,
                BSLanguageDef.SEPARATOR_ID: BSLanguageDef.TOKEN_OPERATOR,
                BSLanguageDef.SPACE_NL: BSLanguageDef.TOKEN_SPACE_NL,
                BSLanguageDef.SPACE_WC: BSLanguageDef.TOKEN_SPACE_WC,

                BSLanguageDef.ACTION_ID_UNCOMPLETE: BSLanguageDef.TOKEN_UNCOMPLETE,
                BSLanguageDef.ACTION_ID_SET: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_UNIT: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_PEN: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_FILL: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_TEXT: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_PAPER: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_CANVAS: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_LAYER: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_SELECTION: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_EXECUTION: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DRAW: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FILL: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_PEN: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_MOVE: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_TURN: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_POP: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_PUSH: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FILTER: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_CANVAS: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DOCUMENT: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_LAYER: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SELECTION: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_CONSOLE: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DIALOG: BSLanguageDef.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FLOW: BSLanguageDef.TOKEN_FLOW,
                BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW: BSLanguageDef.TOKEN_UNCOMPLETEFLOW,

                BSLanguageDef.FUNCTION_ID_MATH: BSLanguageDef.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_STR: BSLanguageDef.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_COLOR: BSLanguageDef.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_UNCOMPLETE: BSLanguageDef.TOKEN_UNCOMPLETEFUNCTION,

                BSLanguageDef.UNKNOWN: BSLanguageDef.TOKEN_UNKNOWN
            }

        self.__tokenStyles = {}

        styles = {
                BSLanguageDef.STYLE_DARK: [
                        (BSLanguageDef.TOKEN_STRING, '#9ac07c', False, False),
                        (BSLanguageDef.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COLOR, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSLanguageDef.TOKEN_ACTION, '#FFFF00', True, False),
                        (BSLanguageDef.TOKEN_FLOW, '#c278da', True, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True, None, i18n('Flow instruction is not complete')),
                        (BSLanguageDef.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFUNCTION, '#6aafec', False, True),
                        (BSLanguageDef.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSLanguageDef.TOKEN_BRACES, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETE, '#FFFF88', False, True, '#ffb770', i18n('Action instruction is not complete')),
                        (BSLanguageDef.TOKEN_UNKNOWN, '#880000', True, True, '#d29090'),
                        (BSLanguageDef.TOKEN_SPACE_WC, None, False, False),
                        (BSLanguageDef.TOKEN_SPACE_NL, None, False, False)
                    ],
                BSLanguageDef.STYLE_LIGHT: [
                        (BSLanguageDef.TOKEN_STRING, '#9ac07c', False, False),
                        (BSLanguageDef.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COLOR, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSLanguageDef.TOKEN_ACTION, '#FFFF00', True, False),
                        (BSLanguageDef.TOKEN_FLOW, '#c278da', True, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True),
                        (BSLanguageDef.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFUNCTION, '#6aafec', False, True),
                        (BSLanguageDef.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSLanguageDef.TOKEN_BRACES, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETE, '#FFFF88', False, True, '#ffb770'),
                        (BSLanguageDef.TOKEN_UNKNOWN, '#880000', True, True, '#d29090'),
                        (BSLanguageDef.TOKEN_SPACE_WC, None, False, False),
                        (BSLanguageDef.TOKEN_SPACE_NL, None, False, False)
                    ]
            }

        for style in styles:
            for definition in styles[style]:
                self.setStyle(style, *definition)


    def style(self, type):
        """Return style to apply for a token type or a token familly"""
        if isinstance(type, int):
            if type in self.__tokenStyles[self.__currentStyleId]:
                return self.__tokenStyles[self.__currentStyleId][type]
        elif isinstance(type, str):
            if self.__tokenFamillies[type] in self.__tokenStyles[self.__currentStyleId]:
                return self.__tokenStyles[self.__currentStyleId][self.__tokenFamillies[type]]
        # in all other case, token style is not known...
        return self.__tokenStyles[self.__currentStyleId][BSLanguageDef.TOKEN_UNKNOWN]


    def setStyle(self, themeId, tokenFamilly, fgColor, bold, italic, bgColor=None, tooltip=None):
        """Define style for a token familly"""
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

        self.__tokenStyles[themeId][tokenFamilly]=textFmt


    def theme(self):
        """Return current defined theme"""
        return self.__currentStyleId


    def setTheme(self, themeId):
        """Set current theme

        If theme doesn't exist, current theme is not changed"""
        if themeId in self.__currentStyleId:
            self.__currentStyleId=themeId


    def familly(self, type):
        """Return token familly for given token type"""
        if type in self.__tokenFamillies:
            return self.__tokenFamillies[type]
        return BSLanguageDef.TOKEN_UNKNOWN


    def rules(self):
        """Return all language rules as a list of BSLanguageRule"""
        return self.__rules


    def tokenized(self, text):
        """Return tokenized text as BSList

        Each list item is BSLanguageToken object
        """
        matchIterator = self.__regEx.globalMatch(text)

        BSLanguageToken.resetTokenizer()

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
                            token = BSLanguageToken(match.captured(textIndex), rule,
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


    def getTextProposal(self, text):
        """Return a list of possible values for given text"""
        if not isinstance(text, str):
            raise EInvalidType('Given `text` must be str')

        rePattern=re.compile(re.escape(re.sub('\s+', '\x01', text)).replace('\x01', r'\s+'))
        returned=[]
        for rule in self.__rules:
            values=rule.matchText(rePattern)
            if len(values)>0:
                returned+=values
        return returned


    def vocabulary(self):
        """..."""
        returned=[]
        for rule in self.__rules:
            returned+=rule.asText()
        return returned


    def regEx(self):
        """Return current built regular expression used for lexer"""
        return self.__regEx