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

import re

from .bstheme import BSTheme
from .bstokenizer import (
            BSToken,
            BSTokenFamily,
            BSTokenFamilyStyle,
            BSTokenizer,
            BSTokenizerRule
        )

class BSLanguageDef:
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


    def __init__(self):
        """Initialise language & styles"""
        # styles => relation between a TOKEN type and TOKEN family
        self.__tokenFamilies = {}

        self.__tokenizer = BSTokenizer()
        self.__tokenStyle = BSTokenFamilyStyle()

        self.__initialiseFamilies()
        self.__initialiseRules()


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

        for rule in rules:
            self.__tokenizer.add(BSTokenizerRule(self, rule[0], rule[1], self.family(rule[1]), *rule[2:] ))


    def __initialiseFamilies(self):
        """Set language styles (text format for token)"""
        self.__tokenFamilies={
                BSLanguageDef.COMMENT: BSTokenFamily.TOKEN_COMMENT,
                BSLanguageDef.TYPE_STRING: BSTokenFamily.TOKEN_STRING,
                BSLanguageDef.TYPE_NUMBER: BSTokenFamily.TOKEN_NUMBER,
                BSLanguageDef.TYPE_COLOR: BSTokenFamily.TOKEN_COLOR,
                BSLanguageDef.CONSTANT_ID_SETONOFF: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETUNITCOORD: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETUNITROT: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENSTYLE: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENCAP: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPENJOIN: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETFILLRULE: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETTXTHALIGN: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETTXTVALIGN: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETPAPERBLEND: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.CONSTANT_ID_SETSELECTMODE: BSTokenFamily.TOKEN_CONSTANT,
                BSLanguageDef.VARIABLE_ID: BSTokenFamily.TOKEN_VARIABLE_USERDEFINED,
                BSLanguageDef.VARIABLE_ID_INTERNAL: BSTokenFamily.TOKEN_VARIABLE_INTERNAL,
                BSLanguageDef.OPERATORS_ID: BSTokenFamily.TOKEN_OPERATOR,
                BSLanguageDef.BRACES_ID_PARENTHESIS_OPEN: BSTokenFamily.TOKEN_BRACES,
                BSLanguageDef.BRACES_ID_PARENTHESIS_CLOSE: BSTokenFamily.TOKEN_BRACES,
                BSLanguageDef.SEPARATOR_ID: BSTokenFamily.TOKEN_OPERATOR,
                BSLanguageDef.SPACE_NL: BSTokenFamily.TOKEN_SPACE_NL,
                BSLanguageDef.SPACE_WC: BSTokenFamily.TOKEN_SPACE_WC,

                BSLanguageDef.ACTION_ID_UNCOMPLETE: BSTokenFamily.TOKEN_UNCOMPLETE,
                BSLanguageDef.ACTION_ID_SET: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_UNIT: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_PEN: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_FILL: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_TEXT: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_PAPER: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_CANVAS: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_LAYER: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_SELECTION: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SET_EXECUTION: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DRAW: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FILL: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_PEN: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_MOVE: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_TURN: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_POP: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_PUSH: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FILTER: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_CANVAS: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DOCUMENT: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_LAYER: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_SELECTION: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_CONSOLE: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_DIALOG: BSTokenFamily.TOKEN_ACTION,
                BSLanguageDef.ACTION_ID_FLOW: BSTokenFamily.TOKEN_FLOW,
                BSLanguageDef.ACTION_ID_UNCOMPLETEFLOW: BSTokenFamily.TOKEN_UNCOMPLETEFLOW,

                BSLanguageDef.FUNCTION_ID_MATH: BSTokenFamily.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_STR: BSTokenFamily.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_COLOR: BSTokenFamily.TOKEN_FUNCTION,
                BSLanguageDef.FUNCTION_ID_UNCOMPLETE: BSTokenFamily.TOKEN_UNCOMPLETEFUNCTION,

                BSLanguageDef.UNKNOWN: BSTokenFamily.TOKEN_UNKNOWN
            }


    def family(self, type):
        """Return token family for given token type"""
        if type in self.__tokenFamilies:
            return self.__tokenFamilies[type]
        return BSTokenFamily.TOKEN_UNKNOWN


    def tokenizer(self):
        """Return tokenizer for language"""
        return self.__tokenizer


    def style(self, item):
        """Return style for given token and/or rule"""
        return self.__tokenStyle.style(item.family())


    def getTextProposal(self, text):
        """Return a list of possible values for given text"""
        if not isinstance(text, str):
            raise EInvalidType('Given `text` must be str')

        rePattern=re.compile(re.escape(re.sub('\s+', '\x01', text)).replace('\x01', r'\s+'))
        returned=[]
        for rule in self.__tokenizer.rules():
            values=rule.matchText(rePattern)
            if len(values)>0:
                returned+=values
        return returned


    def vocabulary(self):
        """Return vocabulary list for language"""
        returned=[]
        for rule in self.__tokenizer.rules():
            returned+=rule.readableTextList()
        return returned


