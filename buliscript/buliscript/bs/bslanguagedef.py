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

class BSLanguageRule:
    """Define a rule for language"""
    def __init__(self, regEx, type, language):
        if isinstance(regEx, str):
            regEx = QRegularExpression(regEx, QRegularExpression.CaseInsensitiveOption)
        if not regEx.isValid():
            print("invalid regex", regEx.pattern(), type)
        self.__regEx = regEx
        self.__type = type
        self.__language = language

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
        return self.__language.familly(self.__type)

    def style(self):
        """Return style for rule"""
        return self.__language.style(self.__type)


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
    TOKEN_CONSTANT = 12
    TOKEN_UNKNOWN = 13
    TOKEN_SPACE_NL = 14

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

    OPERATORS_ID = 'operator'
    SEPARATOR_ID = 'separator'
    BRACES_ID_PARENTHESIS_OPEN = 'bracesParenthesisO'
    BRACES_ID_PARENTHESIS_CLOSE = 'bracesParenthesisC'

    TYPE_STRING = 'typeStr'
    TYPE_NUMBER = 'typeNum'

    SPACE_NL = 'spNl'

    COMMENT = 'comment'

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
        rules = [   (r'"[^"\\]*(?:\\.[^"\\]*)*"', BSLanguageDef.TYPE_STRING),
                    (r"'[^'\\]*(?:\\.[^'\\]*)*'", BSLanguageDef.TYPE_STRING),

                    (r"\n", BSLanguageDef.SPACE_NL),

                    (r'#[^\n]*', BSLanguageDef.COMMENT),

                    (r"-?(?:\d+\.\d*|\.\d+|\d+)", BSLanguageDef.TYPE_NUMBER),

                    (r"^\s*\bset\s+unit\s+coordinates\b", BSLanguageDef.ACTION_ID_SET_UNIT),
                    (r"^\s*\bset\s+unit\s+rotation\b", BSLanguageDef.ACTION_ID_SET_UNIT),
                    (r"^\s*\bset\s+unit\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+pen\s+color\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+width\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+style\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+cap\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+join\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+brush\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\s+opacity\b", BSLanguageDef.ACTION_ID_SET_PEN),
                    (r"^\s*\bset\s+pen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+fill\s+color\b", BSLanguageDef.ACTION_ID_SET_FILL),
                    (r"^\s*\bset\s+fill\s+brush\b", BSLanguageDef.ACTION_ID_SET_FILL),
                    (r"^\s*\bset\s+fill\s+rule\b", BSLanguageDef.ACTION_ID_SET_FILL),
                    (r"^\s*\bset\s+fill\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+text\s+font\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+size\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+bold\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+italic\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+letter\s+spacing\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+letter\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+text\s+stretch\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+color\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+align\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\s+position\b", BSLanguageDef.ACTION_ID_SET_TEXT),
                    (r"^\s*\bset\s+text\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+paper\s+antialiasing\b", BSLanguageDef.ACTION_ID_SET_PAPER),
                    (r"^\s*\bset\s+paper\s+blending\b", BSLanguageDef.ACTION_ID_SET_PAPER),
                    (r"^\s*\bset\s+paper\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+canvas\s+grid\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+grid\s+width\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+grid\s+style\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+canvas\s+origin\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+origin\s+width\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+origin\s+style\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+canvas\s+position\s+color\b", BSLanguageDef.ACTION_ID_SET_CANVAS),
                    (r"^\s*\bset\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+layer\s+opacity\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+name\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+visible\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+lock\s+alpha\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+lock\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+layer\s+inherit\s+alpha\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+inherit\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+layer\s+blending\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+color\s+label\b", BSLanguageDef.ACTION_ID_SET_LAYER),
                    (r"^\s*\bset\s+layer\s+color\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bset\s+layer\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+select\s+mode\b", BSLanguageDef.ACTION_ID_SET_SELECTION),
                    (r"^\s*\bset\s+select\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\s+execution\s+verbose\b", BSLanguageDef.ACTION_ID_SET_EXECUTION),
                    (r"^\s*\bset\s+execution\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bset\b", BSLanguageDef.ACTION_ID_SET),


                    (r"^\s*\bdraw\s+square\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+round\s+square\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+rect\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+round\s+rect\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+circle\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+ellipse\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+dot\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+pixel\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+scaled\s+image\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+image\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+text\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+star\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bdraw\s+arc\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bdraw\s+bezier\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bdraw\s+spline\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bdraw\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bclear\b", BSLanguageDef.ACTION_ID_DRAW),
                    (r"^\s*\bapply\b", BSLanguageDef.ACTION_ID_DRAW),

                    (r"^\s*\bfill\s+activate\b", BSLanguageDef.ACTION_ID_FILL),
                    (r"^\s*\bfill\s+deactivate\b", BSLanguageDef.ACTION_ID_FILL),
                    (r"^\s*\bfill\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bpen\s+up\b", BSLanguageDef.ACTION_ID_PEN),
                    (r"^\s*\bpen\s+down\b", BSLanguageDef.ACTION_ID_PEN),
                    (r"^\s*\bpen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bmove\s+home\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\s+forward\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\s+backward\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\s+left\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\s+right\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\s+to\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bmove\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bturn\s+left\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bturn\s+right\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bturn\s+absolute\b", BSLanguageDef.ACTION_ID_MOVE),
                    (r"^\s*\bturn\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bpush\s+state\b", BSLanguageDef.ACTION_ID_PUSH),
                    (r"^\s*\bpush\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bpop\s+state\b", BSLanguageDef.ACTION_ID_POP),
                    (r"^\s*\bpop\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bfilter\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),


                    (r"^\s*\bshow\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bshow\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bshow\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bshow\s+canvas\s+background\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bshow\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bshow\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bhide\s+canvas\s+grid\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bhide\s+canvas\s+origin\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bhide\s+canvas\s+position\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bhide\s+canvas\s+background\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bhide\s+canvas\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bhide\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bopen\s+document\b", BSLanguageDef.ACTION_ID_DOCUMENT),
                    (r"^\s*\bopen\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bsave\s+document\s+as\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bsave\s+document\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bsave\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bcrop\s+document\b", BSLanguageDef.ACTION_ID_CANVAS),
                    (r"^\s*\bcrop\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\badd\s+paint\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\badd\s+paint\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\badd\s+group\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\badd\s+group\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\badd\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\buse\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\buse\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bdelete\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\bdelete\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bmerge\s+layer\s+down\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\bmerge\s+layer\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bmerge\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\brotate\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\brotate\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bshear\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\bshear\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\btranslate\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\btranslate\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bscale\s+layer\b", BSLanguageDef.ACTION_ID_LAYER),
                    (r"^\s*\bscale\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bselect\s+all\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\s+none\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\s+invert\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\s+alpha\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\s+region\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\s+area\b", BSLanguageDef.ACTION_ID_SELECTION),
                    (r"^\s*\bselect\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),

                    (r"^\s*\bstop\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bimport\s+macro\sfrom\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bimport\s+macro\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bimport\s+image\sfrom\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bimport\s+image\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bimport\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\brepeat\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bfor\s+each\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bfor\b", BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW),
                    (r"^\s*\bcall\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bdefine\s+macro\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"^\s*\bdefine\b", BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW),
                    (r"^\s*\breturn\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"\btimes\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"\bin\b", BSLanguageDef.ACTION_ID_FLOW),
                    (r"\bas\b", BSLanguageDef.ACTION_ID_FLOW),

                    (r"\b{0}\b".format(r'\b|\b'.join(['ON','OFF'])), BSLanguageDef.CONSTANT_ID_SETONOFF),
                    (r"\b{0}\b".format(r'\b|\b'.join(['PIXEL','PERCENTAGE','MM','INCH'])), BSLanguageDef.CONSTANT_ID_SETUNITCOORD),
                    (r"\b{0}\b".format(r'\b|\b'.join(['RADIAN','DEGREE'])), BSLanguageDef.CONSTANT_ID_SETUNITROT),
                    (r"\b{0}\b".format(r'\b|\b'.join(['SOLID','DASH','DOT','DASHDOT','NONE'])), BSLanguageDef.CONSTANT_ID_SETPENSTYLE),
                    (r"\b{0}\b".format(r'\b|\b'.join(['SQUARE','FLAT','ROUND'])), BSLanguageDef.CONSTANT_ID_SETPENCAP),
                    (r"\b{0}\b".format(r'\b|\b'.join(['BEVEL','MITTER','ROUND'])), BSLanguageDef.CONSTANT_ID_SETPENJOIN),
                    (r"\b{0}\b".format(r'\b|\b'.join(['EVEN','PLAIN'])), BSLanguageDef.CONSTANT_ID_SETFILLRULE),
                    (r"\b{0}\b".format(r'\b|\b'.join(['LEFT','CENTER','RIGHT'])), BSLanguageDef.CONSTANT_ID_SETTXTHALIGN),
                    (r"\b{0}\b".format(r'\b|\b'.join(['TOP','MIDDLE','BOTTOM'])), BSLanguageDef.CONSTANT_ID_SETTXTVALIGN),
                    (r"\b{0}\b".format(r'\b|\b'.join(['NORMAL','SOURCE_OVER','DESTINATION_OVER','CLEAR','SOURCE_IN','SOURCE_OUT','DESTINATION_IN','DESTINATION_OUT','SOURCE_ATOP','DESTINATION_ATOP','XOR','PLUS','MULTIPLY','SCREEN','OVERLAY','DARKEN','LIGHTEN','COLORDODGE','COLORBURN','HARD_LIGHT','SOFT_LIGHT','DIFFERENCE','EXCLUSION'])), BSLanguageDef.CONSTANT_ID_SETPAPERBLEND),
                    (r"\b{0}\b".format(r'\b|\b'.join(['REPLACE','ADD','SUBSTRACT'])), BSLanguageDef.CONSTANT_ID_SETSELECTMODE),

                    (r"^\s*\bdialog\s+message\b", BSLanguageDef.ACTION_ID_DIALOG),
                    (r"^\s*\bdialog\s+question\b", BSLanguageDef.ACTION_ID_DIALOG),
                    (r"^\s*\bdialog\s+input\b", BSLanguageDef.ACTION_ID_DIALOG),
                    (r"^\s*\bdialog\b", BSLanguageDef.ACTION_ID_UNCOMPLETE),
                    (r"^\s*\bprint\b", BSLanguageDef.ACTION_ID_CONSOLE),
                    (r"^\s*\binput\b", BSLanguageDef.ACTION_ID_CONSOLE),

                    (r":\bposition\.x\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bposition\.y\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bangle\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bunit\.(?:rotation|coordinates)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bpen\.(?:color|width|style|cap|join|brush|opacity|status)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bfill\.(?:color|brush|rule|status)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\btext\.(?:font|size|bold|italic|outline|letter\s+spacing|stretch|color|align|position)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bcanvas\.grid\.(?:status|color|width|style)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bcanvas\.origin\.(?:status|color|width|style)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\bcanvas\.position\.(?:status|color|size)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\brepeat\.(?:current|total|incAngle|currentAngle)\b", BSLanguageDef.VARIABLE_ID_INTERNAL),
                    (r":\b[a-z][a-z0-9_]*\b", BSLanguageDef.VARIABLE_ID),

                    (r"\bmath\.(?:cosinus|sinus|tangent|ceil|floor|round|square_root|random)\b", BSLanguageDef.FUNCTION_ID_MATH),
                    (r"\bstring\.(?:length|upper|lower)\b", BSLanguageDef.FUNCTION_ID_STR),
                    (r"\bcolor\.(?:rgba|rgb)\b", BSLanguageDef.FUNCTION_ID_COLOR),

                    (r"\+|-|\*|//|/|%|<=|<|>=|>|!=|==|=", BSLanguageDef.OPERATORS_ID),
                    (r",|\.", BSLanguageDef.SEPARATOR_ID),
                    (r"\(", BSLanguageDef.BRACES_ID_PARENTHESIS_OPEN),
                    (r"\)", BSLanguageDef.BRACES_ID_PARENTHESIS_CLOSE)
                ]

        regEx=[]
        for rule in rules:
            regEx.append(rule[0])
            self.__rules.append(BSLanguageRule(rule[0], rule[1], self))

        # main regular expression use for lexer
        self.__regEx=QRegularExpression('|'.join(regEx), QRegularExpression.CaseInsensitiveOption|QRegularExpression.MultilineOption)


    def __initialiseStyles(self):
        """Set language styles (text format for token)"""
        self.__tokenFamillies={
                BSLanguageDef.COMMENT: BSLanguageDef.TOKEN_COMMENT,
                BSLanguageDef.TYPE_STRING: BSLanguageDef.TOKEN_STRING,
                BSLanguageDef.TYPE_NUMBER: BSLanguageDef.TOKEN_NUMBER,
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
                BSLanguageDef.FUNCTION_ID_COLOR: BSLanguageDef.TOKEN_FUNCTION
            }

        self.__tokenStyles = {}

        styles = {
                BSLanguageDef.STYLE_DARK: [
                        (BSLanguageDef.TOKEN_STRING, '#9ac07c', False, False),
                        (BSLanguageDef.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSLanguageDef.TOKEN_ACTION, '#FFFF00', True, False),
                        (BSLanguageDef.TOKEN_FLOW, '#c278da', True, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True, None, i18n('Flow instruction is not complete')),
                        (BSLanguageDef.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSLanguageDef.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSLanguageDef.TOKEN_BRACES, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETE, '#FFFF88', False, True, '#ffb770', i18n('Action instruction is not complete')),
                        (BSLanguageDef.TOKEN_UNKNOWN, '#880000', True, True, '#d29090'),
                        (BSLanguageDef.TOKEN_SPACE_NL, None, False, True)
                    ],
                BSLanguageDef.STYLE_LIGHT: [
                        (BSLanguageDef.TOKEN_STRING, '#9ac07c', False, False),
                        (BSLanguageDef.TOKEN_NUMBER, '#c9986a', False, False),
                        (BSLanguageDef.TOKEN_COMMENT, '#5d636f', False, True),
                        (BSLanguageDef.TOKEN_ACTION, '#FFFF00', True, False),
                        (BSLanguageDef.TOKEN_FLOW, '#c278da', True, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETEFLOW, '#c278da', True, True),
                        (BSLanguageDef.TOKEN_FUNCTION, '#6aafec', False, False),
                        (BSLanguageDef.TOKEN_OPERATOR, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_INTERNAL, '#e18890', False, False),
                        (BSLanguageDef.TOKEN_VARIABLE_USERDEFINED, '#d96d77', False, False),
                        (BSLanguageDef.TOKEN_BRACES, '#c278da', False, False),
                        (BSLanguageDef.TOKEN_CONSTANT, '#62b6c1', False, False),
                        (BSLanguageDef.TOKEN_UNCOMPLETE, '#FFFF88', False, True, '#ffb770'),
                        (BSLanguageDef.TOKEN_UNKNOWN, '#880000', True, True, '#d29090'),
                        (BSLanguageDef.TOKEN_SPACE_NL, None, False, True)
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
                            returned.append(BSLanguageToken(match.captured(textIndex), rule,
                                                            match.capturedStart(textIndex),
                                                            match.capturedEnd(textIndex),
                                                            match.capturedLength(textIndex)))
                            # do not need to continue to check for another token type
                            break
        return BSList(returned)

    def regEx(self):
        return self.__regEx