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

from enum import Enum
import re

from buliscript.pktk.modules.uitheme import UITheme
from buliscript.pktk.modules.languagedef import LanguageDef
from buliscript.pktk.modules.parser import (
        GrammarRules,
        GrammarRule,
        GROne,
        GROptional,
        GRNoneOrMore,
        GROneOrMore,
        GRToken,
        GRRule,
        GROperatorPrecedence,
        ASTItem
    )

from buliscript.pktk.modules.tokenizer import (
        Token,
        Tokenizer,
        TokenizerRule,
        TokenType
    )

class BSLanguageDef(LanguageDef):
    # define token types

    class ITokenType(TokenType, Enum):
        STRING = ('String', 'A STRING value')
        NUMBER = ('Number', 'A NUMBER (integer, decimal) value')
        COLOR_CODE = ('Color code', 'A #RRGGBB or #AARRGGBB color code')

        ACTION_SET_UNIT = ('setUnit', 'A <SET UNIT> action')
        ACTION_SET_PEN = ('setPen', 'A <SET PEN> action')
        ACTION_SET_FILL = ('setFill', 'A <SET FILL> action')
        ACTION_SET_TEXT = ('setText', 'A <SET TEXT> action')
        ACTION_SET_DRAW = ('setDraw', 'A <SET DRAW> action')
        ACTION_SET_CANVAS_GRID = ('setCanvasGrid', 'A <SET CANVAS GRID> action')
        ACTION_SET_CANVAS_RULERS = ('setCanvasRuler', 'A <SET CANVAS RULER> action')
        ACTION_SET_CANVAS_ORIGIN = ('setCanvasOrigin', 'A <SET CANVAS ORIGIN> action')
        ACTION_SET_CANVAS_POSITION = ('setCanvasPosition', 'A <SET CANVAS POSITION> action')
        ACTION_SET_CANVAS_BACKGROUND = ('setCanvasBackground', 'A <SET CANVAS POSITION> action')
        ACTION_SET_LAYER = ('setLayer', 'A <SET LAYER> action')
        ACTION_SET_SELECTION = ('setSelection', 'A <SET SELECTION> action')
        ACTION_SET_SCRIPT = ('setExecution', 'A <SET EXECUTION> action')

        ACTION_DRAW_SHAPE = ('drawShape', 'A <DRAW shape> action')
        ACTION_DRAW_MISC = ('drawMisc', 'A draw <misc> action')
        ACTION_DRAW_FILL = ('drawFill', 'A <FILL> action')
        ACTION_DRAW_PEN = ('drawPen', 'A <PEN> action')
        ACTION_DRAW_MOVE = ('drawMove', 'A <MOVE> action')
        ACTION_DRAW_TURN = ('drawTurn', 'A <TURN> action')

        ACTION_CANVAS = ('canvas', 'A <CANVAS> action')

        ACTION_STATE = ('state', 'A <STATE> action')

        ACTION_UICONSOLE = ('uiConsole', 'A <CONSOLE> action')
        ACTION_UIDIALOG = ('uiDialog', 'A <DIALOG> action')
        ACTION_UIDIALOG_OPTION = ('uiDialogOpt', 'A <DIALOG> option action')


        ACTION_UNCOMPLETE = ('uncompleteAct', 'An uncomplete action definition')

        FLOW_EXEC = ('flowExec', 'A <FLOW> flow')
        FLOW_IMPORT = ('flowImport', 'A <IMPORT> flow')
        FLOW_REPEAT = ('flowRepeat', 'A <REPEAT> flow')
        FLOW_TIMES = ('flowTimes', 'A <TIMES> flow')
        FLOW_AND_STORE_RESULT = ('flowStoreResult', 'A <AS> flow')
        FLOW_WITH_PARAMETERS = ('flowWithParameters', 'A <WITH PARAMETER> flow')
        FLOW_DO = ('flowDo', 'A <DO> flow')
        FLOW_AS = ('flowAs', 'A <AS> flow')
        FLOW_FOREACH = ('flowForEach', 'A <FOREACH> flow')
        FLOW_CALL = ('flowCall', 'A <CALL> flow')
        FLOW_DEFMACRO = ('flowDefMacro', 'A <DEFINE MACRO> flow')
        FLOW_RETURN = ('flowReturn', 'A <RETURN> flow')
        FLOW_SET_VARIABLE = ('flowSetVariable', 'A <SET VARIABLE> flow')
        FLOW_IF = ('flowIf', 'A <IF> flow')
        FLOW_ELIF = ('flowElIf', 'A <ELSE IF> flow')
        FLOW_ELSE = ('flowElIf', 'A <ELSE> flow')
        FLOW_THEN = ('flowThen', 'A <THEN> flow')

        FLOW_UNCOMPLETE = ('uncompleteFlow', 'An uncomplete flow definition')

        FUNCTION_NUMBER = ('fctNumber', 'A function returning a number')
        FUNCTION_STRING = ('fctString', 'A function returning a string')
        FUNCTION_COLOR = ('fctColor', 'A function returning a color')
        FUNCTION_LIST = ('fctList', 'A function returning a list')
        FUNCTION_BOOLEAN = ('fctBool', 'A function returning a boolean')
        FUNCTION_VARIANT = ('fctVariant', 'A function returning any type')

        FUNCTION_UNCOMPLETE = ('uncompleteFct', 'An uncomplete function definition')

        BINARY_OPERATOR = ('binary operators', 'Operators like plus, minus, divide, ...')
        UNARY_OPERATOR = ('unary operators', 'Operators like not, ...')
        DUAL_OPERATOR = ('dual operators', 'Operators like "-" can be unary or unary operator ')
        SEPARATOR = ('operators', 'Separator like comma')
        PARENTHESIS_OPEN = ('parO', 'Parenthesis (open)')
        PARENTHESIS_CLOSE = ('parC', 'Parenthesis (close)')
        BRACKET_OPEN = ('brackO', 'Bracket (open)')
        BRACKET_CLOSE = ('brackC', 'Bracket (close)')

        VARIABLE_USER = ('uvar', 'A user defined variable')
        VARIABLE_RESERVED = ('rvar', 'A reserved variable')

        CONSTANT_NONE = ('constNone', 'A NONE value')
        CONSTANT_ONOFF = ('constSwitch', 'A constant On/Off')
        CONSTANT_UNITS_M = ('constUnitsM', 'A measure unit constant')
        CONSTANT_UNITS_M_RPCT = ('constUnitsMRpct', 'A measure unit constant')
        CONSTANT_UNITS_R = ('constUnitsR', 'A rotation unit constant')
        CONSTANT_PENSTYLE = ('constPenStyle', 'A pen style constant')
        CONSTANT_PENCAP = ('constPenCap', 'A pen cap constant')
        CONSTANT_PENJOIN = ('constPenJoin', 'A pen join constant')
        CONSTANT_FILLRULE = ('constFillRule', 'A fill rule constant')
        CONSTANT_POSHALIGN = ('constTextHAlign', 'A horizontal text align constant')
        CONSTANT_POSVALIGN = ('constTextVAlign', 'A vertical text align constant')
        CONSTANT_BLENDINGMODE = ('constBlendingMode', 'A blending mode')
        CONSTANT_SELECTIONMODE = ('constSelectMode', 'A selection mode')
        CONSTANT_COLORLABEL = ('constColorlabel', 'A color label value')

        TEXT=('default text', 'a default text')


    def __init__(self):
        """Initialise language & styles"""
        super(BSLanguageDef, self).__init__([
            TokenizerRule(BSLanguageDef.ITokenType.STRING, r'''`[^`\\]*(?:\\.[^`\\]*)*`|'[^'\\]*(?:\\.[^'\\]*)*'|"[^"\\]*(?:\\.[^"\\]*)*"''',
                                                           onInitValue=self.__initTokenString,
                                                           ignoreIndent=True),
            #TokenizerRule(BSLanguageDef.ITokenType.STRING, r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            #TokenizerRule(BSLanguageDef.ITokenType.STRING, r"'[^'\\]*(?:\\.[^'\\]*)*'"),


            TokenizerRule(BSLanguageDef.ITokenType.COLOR_CODE,  r'#(?:\b[a-f0-9]{6}\b|[a-f0-9]{8}\b)',
                                                                onInitValue=self.__initTokenColor),

            #TokenizerRule(BSLanguageDef.ITokenType.COMMENT,  r"(?s)#>>.*#<<[^\n]*$"),
            TokenizerRule(BSLanguageDef.ITokenType.COMMENT,  r'#[^\n]*', ignoreIndent=True),

            TokenizerRule(BSLanguageDef.ITokenType.NEWLINE,  r"(?:^\s*\n|\n?\s*\n)+"),


            TokenizerRule(BSLanguageDef.ITokenType.NUMBER,  r"\b(?:\d+\.\d*|\.\d+|\d+)\b", onInitValue=self.__initTokenNumber),


            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_UNIT, r"^\x20*\bset\s+unit\s+(?:canvas|rotation)\b",
                                                                    'Settings/Units',
                                                                    [('set unit canvas \x01<UNIT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define default coordinates & measures unit on canvas]',
                                                                                # description
                                                                                'Set unit used to define coordinates & measures (distances, sizes) on canvas\n\n'
                                                                                'Given *<UNIT>* can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set unit canvas PX`**\n\n'
                                                                                'Will define all default distance/size unit as *pixels* for all actions')),
                                                                     ('set unit rotation \x01<UNIT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define default rotation angle unit]',
                                                                                # description
                                                                                'Set unit used to define rotation values\n\n'
                                                                                'Given *<UNIT>* can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)\n\n'
                                                                                'A positive angle is applied with counterclockwise direction',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set unit rotation DEGREE`**\n\n'
                                                                                'Will define default rotation unit as *degrees* for all actions'))
                                                                    ],
                                                                    'A'),

            # todo: add |brush
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_PEN, r"^\x20*\bset\s+pen\s+(?:color|size|style|cap|join|opacity)\b",
                                                                    'Settings/Pen',
                                                                    [('set pen color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen color]',
                                                                                # description
                                                                                'Set stroke color used for pen\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`set pen color #ffff00`**\n'
                                                                                '**`set pen color color.rgb(255, 255, 0)`**\n\n'
                                                                                'Will all define pen color as yellow, 100% opacity\n\n'
                                                                                'Following instructions:\n'
                                                                                '**`set pen color #80ffff00`**\n'
                                                                                '**`set pen color color.rgba(255, 255, 0, 128)`**\n\n'
                                                                                'Will all define pen color as yellow, 50% opacity')),
                                                                     ('set pen size \x01<SIZE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen size]',
                                                                                # description
                                                                                'Set stroke width for pen\n\n'
                                                                                'Given *<SIZE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set pen size 4`**\n\n'
                                                                                'Will define a pen size of 4 pixels if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`set pen size 4 MM`**\n\n'
                                                                                'Will define a pen size of 4 millimeters whatever is default canvas unit')),
                                                                     ('set pen style \x01<STYLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen style]',
                                                                                # description
                                                                                'Set stroke style for pen\n\n'
                                                                                'Given *<STYLE>* can be:\n'
                                                                                ' - **`SOLID`**\n'
                                                                                ' - **`DASH`**\n'
                                                                                ' - **`DOT`**\n'
                                                                                ' - **`DASHDOT`**\n'
                                                                                ' - **`NONE`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set pen style DOT`**\n\n'
                                                                                'Will define a pen for which strokes will be dots')),
                                                                     ('set pen cap \x01<CAP>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen cap]',
                                                                                # description
                                                                                'Set stroke cap for pen\n\n'
                                                                                'Given *<CAP>* can be:\n'
                                                                                ' - **`SQUARE`**\n'
                                                                                ' - **`FLAT`**\n'
                                                                                ' - **`ROUNDCAP`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set pen cap ROUNDCAP`**\n\n'
                                                                                'Will define a rounded pen cap')),
                                                                     ('set pen join \x01<JOIN>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen join]',
                                                                                # description
                                                                                'Set stroke join for pen\n\n'
                                                                                'Given *<JOIN>* can be:\n'
                                                                                ' - **`BEVEL`**\n'
                                                                                ' - **`MITTER`**\n'
                                                                                ' - **`ROUNDJOIN`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set pen join ROUNDJOIN`**\n\n'
                                                                                'Will define a rounded pen join')),
                                                                     ('set pen opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define pen color opacity]',
                                                                                # description
                                                                                'Set pen color opacity without changing color property\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set pen color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set pen opacity 128`**\n'
                                                                                '**`set pen opacity 0.5`**\n\n'
                                                                                'Will both define a pen opacity of 50%')),
                                                                    ],
                                                                    'A'),

            # todo: add |brush
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_FILL, r"^\x20*\bset\s+fill\s+(?:color|rule|opacity)\b",
                                                                    'Settings/Fill',
                                                                    [('set fill color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define fill color]',
                                                                                # description
                                                                                'Set color used to fill areas\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set fill color #ffff00`**\n'
                                                                                '**`set fill color color.rgb(255, 255, 0)`**\n\n'
                                                                                'Will all define fill color as yellow, 100% opacity\n\n'
                                                                                'Following instructions:\n'
                                                                                '**`set fill color #80ffff00`**\n'
                                                                                '**`set fill color color.rgba(255, 255, 0, 128)`**\n\n'
                                                                                'Will all define fill color as yellow, 50% opacity')),
                                                                     ('set fill rule \x01<RULE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define fill rule]',
                                                                                # description
                                                                                'Set fill rule\n\n'
                                                                                'Given *<RULE>* can be:\n'
                                                                                ' - **`EVEN`**: region is filled using the odd even fill rule\n'
                                                                                ' - **`WINDING`**: region is filled using the non zero winding rule\n\n'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set fill rule WINDING`**\n'
                                                                                'Will define rule to fulfill area')),
                                                                     ('set fill opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define fill opacity]',
                                                                                # description
                                                                                'Set fill opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set fill color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set fill opacity 128`**\n'
                                                                                '**`set fill opacity 0.5`**\n\n'
                                                                                'Will both define a fill opacity of 50%')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_TEXT, r"^\x20*\bset\s+text\s+(?:color|opacity|font|size|bold|italic|outline|letter\s+spacing|stretch|horizontal\s+alignment|vertical\s+alignment|position)\b",
                                                                    'Settings/Text',
                                                                    [('set text color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text color]',
                                                                                # description
                                                                                'Set color used print text\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text color #ffff00`**\n'
                                                                                '**`set text color color.rgb(255, 255, 0)`**\n\n'
                                                                                'Will all define text color as yellow, 100% opacity\n\n'
                                                                                'Following instructions:\n'
                                                                                '**`set text color #80ffff00`**\n'
                                                                                '**`set text color color.rgba(255, 255, 0, 128)`**\n\n'
                                                                                'Will all define text color as yellow, 50% opacity')),
                                                                     ('set text opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text opacity]',
                                                                                # description
                                                                                'Set text opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set text color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text opacity 128`**\n'
                                                                                '**`set text opacity 0.5`**\n\n'
                                                                                'Will both define a text opacity of 50%')),
                                                                     ('set text font \x01<FONT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text font]',
                                                                                # description
                                                                                'Set font for text\n\n'
                                                                                'Given *<FONT>* is a string with font name\n\n'
                                                                                'If no font is found for given name, action is ignored',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text font "DejaVu Sans"`**\n\n'
                                                                                'Will define *DejaVu Sans* as text font')),
                                                                     ('set text size \x01<SIZE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text size]',
                                                                                # description
                                                                                'Set size for text\n\n'
                                                                                'Given *<SIZE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text width 40`**\n\n'
                                                                                'Will define a text size of 40 pixels if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`set text size 4 MM`**\n\n'
                                                                                'Will define a text size of 4 millimeters whatever is default canvas unit')),
                                                                     ('set text bold \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text style: bold]',
                                                                                # description
                                                                                'Set text weight\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: enable bold text\n'
                                                                                ' - **`OFF`**: disable bold text',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text bold ON`**\n\n'
                                                                                'Will define text as bold')),
                                                                     ('set text italic \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text style: italic]',
                                                                                # description
                                                                                'Set text style italic\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: enable italic text\n'
                                                                                ' - **`OFF`**: disable italic text',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text italic ON`**\n\n'
                                                                                'Will define text as italic')),
                                                                     ('set text outline \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text style: outline]',
                                                                                # description
                                                                                'Set text style outline\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: enable outline text\n'
                                                                                ' - **`OFF`**: disable outline text',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text outline ON`**\n\n'
                                                                                'Will define text as outline')),
                                                                     ('set text letter spacing \x01<SPACING> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text letter spacing]',
                                                                                # description
                                                                                'Set space between text letters\n\n'
                                                                                'Given *<SPACING>* is a number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of base letter spacing\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text letter spacing 8`**\n\n'
                                                                                'Will define a letter spacing for text of 40 pixels if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`set text letter spacing 150 PCT`**\n\n'
                                                                                'Will define a letter spacing for text of 150% of base letter spacing')),
                                                                     ('set text stretch \x01<STRETCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text stretch]',
                                                                                # description
                                                                                'Set text stretching\n\n'
                                                                                'Given *<STRETCH>* is a positive number that define stretch factor:\n'
                                                                                ' - **`int`**: a number; integer value define no stretch to 100 (100%)\n'
                                                                                ' - **`dec`**: a number; decimal value define no stretch to 1.0 (100%)',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`set text stretch 150`**\n\n'
                                                                                '**`set text stretch 1.5`**\n\n'
                                                                                'Will both define stretch value of 150%')),
                                                                     ('set text horizontal alignment \x01<H-ALIGNMENT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text alignment (horizontal)]',
                                                                                # description
                                                                                'Set horizontal alignment for text\n\n'
                                                                                'Given *<H-ALIGNMENT>* can be:\n'
                                                                                ' - **`LEFT`**: text is left aligned relative to current position\n'
                                                                                ' - **`CENTER`**: text is center aligned relative to current position\n'
                                                                                ' - **`RIGHT`**: text is right aligned relative to current position',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text align CENTER`**\n\n'
                                                                                'Will define text as centered')),
                                                                     ('set text vertical alignment \x01<V-ALIGNMENT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define text alignment (vertical)]',
                                                                                # description
                                                                                'Set vertical alignment for text\n\n'
                                                                                'Given *<V-ALIGNMENT>* can be:\n'
                                                                                ' - **`TOP`**: text is vertically aligned to top, relative to current position\n'
                                                                                ' - **`MIDDLE`**: text is vertically aligned to middle, relative to current position\n'
                                                                                ' - **`BOTTOM`**: text is vertically aligned to bottom, relative to current position',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text position MIDDLE`**\n\n'
                                                                                'Will define text as vertically centered'))
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_DRAW, r"^\x20*\bset\s+draw\s+(?:antialiasing|blending\s+mode)\b",
                                                                    'Settings/Draw',
                                                                    [('set draw antialiasing \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define antialiasing mode]',
                                                                                # description
                                                                                'Set antialiasing mode\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: enable antialiasing\n'
                                                                                ' - **`OFF`**: disable antialiasing',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set draw antialiasing ON`**\n\n'
                                                                                'Will enable antialiasing')),
                                                                     ('set draw blending mode \x01<BLENDING-MODE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define blending mode]',
                                                                                # description
                                                                                'Set blending mode applied to draw\n\n'
                                                                                'Given *<BLENDING-MODE>* can be:\n'
                                                                                ' - **`NORMAL`**\n'
                                                                                ' - **`SOURCE_OVER`**\n'
                                                                                ' - **`DESTINATION_OVER`**\n'
                                                                                ' - **`DESTINATION_CLEAR`**\n'
                                                                                ' - **`SOURCE_IN`**\n'
                                                                                ' - **`SOURCE_OUT`**\n'
                                                                                ' - **`DESTINATION_IN`**\n'
                                                                                ' - **`DESTINATION_OUT`**\n'
                                                                                ' - **`SOURCE_ATOP`**\n'
                                                                                ' - **`DESTINATION_ATOP`**\n'
                                                                                ' - **`EXCLUSIVE_OR`**\n'
                                                                                ' - **`PLUS`**\n'
                                                                                ' - **`MULTIPLY`**\n'
                                                                                ' - **`SCREEN`**\n'
                                                                                ' - **`OVERLAY`**\n'
                                                                                ' - **`DARKEN`**\n'
                                                                                ' - **`LIGHTEN`**\n'
                                                                                ' - **`COLORDODGE`**\n'
                                                                                ' - **`COLORBURN`**\n'
                                                                                ' - **`HARD_LIGHT`**\n'
                                                                                ' - **`SOFT_LIGHT`**\n'
                                                                                ' - **`DIFFERENCE`**\n'
                                                                                ' - **`EXCLUSION`**\n'
                                                                                ' - **`BITWISE_S_OR_D`**\n'
                                                                                ' - **`BITWISE_S_AND_D`**\n'
                                                                                ' - **`BITWISE_S_XOR_D`**\n'
                                                                                ' - **`BITWISE_S_NOR_D`**\n'
                                                                                ' - **`BITWISE_S_NAND_D`**\n'
                                                                                ' - **`BITWISE_NS_XOR_D`**\n'
                                                                                ' - **`BITWISE_S_NOT`**\n'
                                                                                ' - **`BITWISE_NS_AND_D`**\n'
                                                                                ' - **`BITWISE_S_AND_ND`**\n'
                                                                                ' - **`BITWISE_NS_OR_D`**\n'
                                                                                ' - **`BITWISE_CLEAR`**\n'
                                                                                ' - **`BITWISE_SET`**\n'
                                                                                ' - **`BITWISE_NOT_D`**\n'
                                                                                ' - **`BITWISE_S_OR_ND`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set draw blending MULTIPLY`**\n\n'
                                                                                'Will define blending mode as MULTIPLY'))
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, r"^\x20*\bset\s+canvas\s+grid\s+(?:color|style|opacity|size)\b",
                                                                    'Settings/Canvas/Grid',
                                                                    [('set canvas grid color \x01<COLOR> [<BGCOLOR>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas grid colors]',
                                                                                # description
                                                                                '*Canvas grid is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set color for canvas grid\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color\n'
                                                                                'The *<BGCOLOR>* define background color outside drawing area and if provided, can be a color code **`#RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid color #880000FF`**\n\n'
                                                                                'Will set a blue grid with 50% opacity')),
                                                                     ('set canvas grid style \x01<STYLE-MAIN> [<STYLE-SECONDARY>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas grid style]',
                                                                                # description
                                                                                '*Canvas grid is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set stroke style for canvas grid\n\n'
                                                                                'Given *<STYLE-MAIN>* and *<STYLE-SECONDARY>* can be:\n'
                                                                                ' - **`SOLID`**\n'
                                                                                ' - **`DASH`**\n'
                                                                                ' - **`DOT`**\n'
                                                                                ' - **`DASHDOT`**\n'
                                                                                ' - **`NONE`**\n\n'
                                                                                'When *<STYLE-SECONDARY>* is omitted, given *<STYLE-MAIN>* is applied to both grid lines',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid style DOT`**\n\n'
                                                                                'Will set a dotted line style to render canvas grid')),
                                                                     ('set canvas grid opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas grid opacity]',
                                                                                # description
                                                                                '*Canvas grid is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas grid opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set canvas grid color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid opacity 128`**\n'
                                                                                '**`set canvas grid opacity 0.5`**\n\n'
                                                                                'Will both define a canvas grid opacity of 50%')),
                                                                     ('set canvas grid size \x01<WIDTH> [<MAIN>] [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas grid size]',
                                                                                # description
                                                                                '*Canvas grid is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas grid size\n\n'
                                                                                'Given *<WIDTH>* is a positive number that define grid size, expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<MAIN>*, if provided, is a positive integer greater than zero that define frequency of main grid line\n\n'
                                                                                'Given *<UNIT>* if provided is applied to <WIDTH> and can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid size 50 PX`**\n\n'
                                                                                'Will define a grid for which line is drawn every 50 pixels\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid size 10 5 MM`**\n\n'
                                                                                'Will define a main grid for which line is drawn every 10 millimeters and a main grid line drawn every 5 grid line')),
                                                                    ],
                                                                    'A'),
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_RULERS, r"^\x20*\bset\s+canvas\s+rulers\s+(?:color)\b",
                                                                    'Settings/Canvas/Rulers',
                                                                    [('set canvas rulers color \x01<COLOR> [<BGCOLOR>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas rulers colors]',
                                                                                # description
                                                                                '*Canvas rulers is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set color for canvas rulers\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color\n'
                                                                                'The *<BGCOLOR>* define background color and if provided, can be a color code **`#RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas rulers color #0000FF #FFFFFF`**\n\n'
                                                                                'Will set a blue ruler on white background'))
                                                                    ],
                                                                    'A'),
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, r"^\x20*\bset\s+canvas\s+origin\s+(?:color|style|opacity|size|position)\b",
                                                                    'Settings/Canvas/Origin',
                                                                    [('set canvas origin color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas origin color]',
                                                                                # description
                                                                                '*Canvas origin is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set color for canvas grid\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid color #880000FF`**\n\n'
                                                                                'Will set a blue origin with 50% opacity')),
                                                                     ('set canvas origin style \x01<STYLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas origin style]',
                                                                                # description
                                                                                '*Canvas origin is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set stroke style for canvas origin\n\n'
                                                                                'Given *<STYLE>* can be:\n'
                                                                                ' - **`SOLID`**\n'
                                                                                ' - **`DASH`**\n'
                                                                                ' - **`DOT`**\n'
                                                                                ' - **`DASHDOT`**\n'
                                                                                ' - **`NONE`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas origin style SOLID`**\n\n'
                                                                                'Will set a solid line style to render canvas origin')),
                                                                     ('set canvas origin opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas origin opacity]',
                                                                                # description
                                                                                '*Canvas origin is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas origin opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set canvas origin color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid opacity 128`**\n'
                                                                                '**`set canvas grid opacity 0.5`**\n\n'
                                                                                'Will both define a canvas grid opacity of 50%')),
                                                                     ('set canvas origin size \x01<SIZE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas origin size]',
                                                                                # description
                                                                                '*Canvas origin is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas origin size\n\n'
                                                                                'Given *<SIZE>* is a positive number that define origin line size, expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas origin size 40 PX`**\n\n'
                                                                                'Will define an origin size of 40 pixels')),
                                                                     ('set canvas origin position \x01<ABSISSA> <ORDINATE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas origin position]',
                                                                                # description
                                                                                'Set canvas origin position (ie: where to (0,0) coordinates is)\n\n'
                                                                                'Given *<ABSISSA>* can be:\n'
                                                                                ' - **`LEFT`**: use left canvas side for absissa origin\n'
                                                                                ' - **`CENTER`**: use center canvas for absissa origin\n'
                                                                                ' - **`RIGHT`**: use right canvas side for absissa origin\n\n'
                                                                                'Given *<ORDINATE>* can be:\n'
                                                                                ' - **`TOP`**: use top canvas side for ordinate origin\n'
                                                                                ' - **`MIDDLE`**: use center canvas for ordinate origin\n'
                                                                                ' - **`BOTTOM`**: use bottom canvas side for ordinate origin',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas origin size 40 PX`**\n\n'
                                                                                'Will define an origin size of 40 pixels')),
                                                                    ],
                                                                    'A'),
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, r"^\x20*\bset\s+canvas\s+position\s+(?:color|opacity|size|fulfilled)\b",
                                                                    'Settings/Canvas/Position',
                                                                    [('set canvas position color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas position color]',
                                                                                # description
                                                                                '*Canvas position is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set color for canvas position\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas grid color #880000FF`**\n\n'
                                                                                'Will set a blue position with 50% opacity')),
                                                                     ('set canvas position opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas position opacity]',
                                                                                # description
                                                                                '*Canvas position is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas position opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n'
                                                                                'Opacity can also be set from **`set canvas position color`** action',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas position opacity 128`**\n'
                                                                                '**`set canvas position opacity 0.5`**\n\n'
                                                                                'Will both define a canvas position opacity of 50%')),
                                                                     ('set canvas position size \x01<SIZE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas position size]',
                                                                                # description
                                                                                '*Canvas position is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas position size\n\n'
                                                                                'Given *<SIZE>* is a positive number that define origin line size, expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas position size 20 PX`**\n\n'
                                                                                'Will define an position size of 20 pixels')),
                                                                     ('set canvas position fulfilled \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas position fulfill]',
                                                                                # description
                                                                                '*Canvas position is dynamically drawn over canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas position empty or fulfill\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: draw position as fulfilled shape\n'
                                                                                ' - **`OFF`**: draw position as empty shape',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas position size 20 PX`**\n\n'
                                                                                'Will define an position size of 20 pixels')),
                                                                    ],
                                                                    'A'),
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, r"^\x20*\bset\s+canvas\s+background\s+(?:opacity|from\s+(?:document|color|layer\s+(?:name|active|id)))\b",
                                                                    'Settings/Canvas/Background',
                                                                    [('set canvas background opacity \x01<OPACITY>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background opacity]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background opacity\n\n'
                                                                                'Given *<OPACITY>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 255\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0\n\n',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background opacity 128`**\n'
                                                                                '**`set canvas background opacity 0.5`**\n\n'
                                                                                'Will both define a canvas background opacity of 50%')),
                                                                     ('set canvas background from color \x01<COLOR>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background content from color]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background from a given color\n\n'
                                                                                'Given *<COLOR>* can be a color code **`#[AA]RRGGBB`** or an expression returning a color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background from color #FFFFFF`**\n\n'
                                                                                'Will define a white canvas background')),
                                                                     ('set canvas background from document',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background content from document]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background from current document projection',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background from document`**\n\n'
                                                                                'Will define current document projection as canvas background')),
                                                                     ('set canvas background from layer active',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background content from active layer]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background from current layer',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background from layer active`**\n\n'
                                                                                'Will define current layer content as canvas background')),
                                                                     ('set canvas background from layer name \x01<NAME>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background content from defined layer]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background from layer designed by given name\n\n'
                                                                                'Given *<NAME>* can be a **`string`** or an expression returning a **`string`**\n'
                                                                                'The first layer for which name match given reference is used; if no layer is found, active layer will be used',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background from layer name "test"`**\n\n'
                                                                                'Will define layer `"test"` content as canvas background')),
                                                                     ('set canvas background from layer id \x01<ID>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define canvas background content from defined layer]',
                                                                                # description
                                                                                '*Canvas background is dynamically drawn under canvas, and is not rendered on final document*\n\n'
                                                                                'Set canvas background from layer designed by given ID\n\n'
                                                                                'Given *<ID>* can be a **`string`** or an expression returning a **`string`**\n'
                                                                                'If no layer is found, active layer will be used',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set canvas background from layer id "{4aa143f9-b8ae-42ee-9d39-9d71c51fa3cb}"`**\n\n'
                                                                                'Will define layer `{4aa143f9-b8ae-42ee-9d39-9d71c51fa3cb}` content as canvas background')),

                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_LAYER, r"^\x20*\bset\s+layer\s+(?:opacity|name|visible|inherit\s+alpha|alpha\s+lock|blending\s+mode|color\s+label)\b",
                                                                    'Settings/Layer',
                                                                    [('set layer opacity \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: opacity]',
                                                                                # description
                                                                                'Set current layer opacity\n\n'
                                                                                'Given *<VALUE>* can be:\n'
                                                                                ' - **`int`**: a number; integer values from 0 to 100\n'
                                                                                ' - **`dec`**: a number; decimal values from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer opacity 50`**\n'
                                                                                '**`set layer opacity 0.5`**\n\n'
                                                                                'Will both define current layer opacity of 50%')),
                                                                     ('set layer name \x01<TEXT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: name]',
                                                                                # description
                                                                                'Set current layer name\n\n'
                                                                                'Given *<TEXT>* is a string that will define layer name',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer name "Testing layer"`**\n\n'
                                                                                'Will define current layer name as *"Testing layer"*')),
                                                                     ('set layer visible \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: visibility]',
                                                                                # description
                                                                                'Set current layer visibility\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: layer is visible\n'
                                                                                ' - **`OFF`**: layer is not visible',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer visibility OFF`**\n\n'
                                                                                'Will define current layer as not visible')),
                                                                     ('set layer alpha lock \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: alpha lock]',
                                                                                # description
                                                                                'Set alpha lock for current layer\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: alpha is locked\n'
                                                                                ' - **`OFF`**: alpha is not locked',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer alpha lock ON`**\n\n'
                                                                                'Will define alpha lock active for current layer')),
                                                                     ('set layer inherit alpha \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: inherit alpha]',
                                                                                # description
                                                                                'Set inherit alpha for current layer\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: inherit alpha is active\n'
                                                                                ' - **`OFF`**: inherit alpha is not active',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer inherit alpha ON`**\n\n'
                                                                                'Will define inherit alpha active for current layer')),
                                                                     ('set layer blending mode \x01<BLENDING_MODE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: blending mode]',
                                                                                # description
                                                                                'Set inherit alpha for current layer\n\n'
                                                                                'Given *<BLENDING_MODE>* can be:\n'
                                                                                ' - ',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer blending mode XXXXX`**\n\n'
                                                                                'Will define blending mode XXXXX for current layer')),
                                                                     ('set layer color label \x01<COLOR_LABEL>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s layer property: color label]',
                                                                                # description
                                                                                'Set inherit alpha for current layer\n\n'
                                                                                'Given *<COLOR_LABEL>* can be:\n'
                                                                                ' - **`NONE`**\n'
                                                                                ' - **`BLUE`**\n'
                                                                                ' - **`GREEN`**\n'
                                                                                ' - **`YELLOW`**\n'
                                                                                ' - **`ORANGE`**\n'
                                                                                ' - **`BROWN`**\n'
                                                                                ' - **`RED`**\n'
                                                                                ' - **`PURPLE`**\n'
                                                                                ' - **`GREY`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set layer color label GREEN`**\n\n'
                                                                                'Will define a green color label for current layer')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_SELECTION, r"^\x20*\bset\s+selection\s+(?:mode)\b",
                                                                    'Settings/Selection',
                                                                    [('set selection mode \x01<MODE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define *Krita*\'s selection mode]',
                                                                                # description
                                                                                'Set selection mode\n\n'
                                                                                'Given *<MODE>* can be:\n'
                                                                                ' - **`REPLACE`**: replace current selection with new one\n'
                                                                                ' - **`ADD`**: add new selection to current selection\n'
                                                                                ' - **`SUBSTRACT`**: substract selection from current selection',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set selection mode ADD`**\n\n'
                                                                                'Will define current selection mode to add new selections to current selection')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_SET_SCRIPT, r"^\x20*\bset\s+script\s+(?:execution\s+(?:verbose)|randomize\s+(?:seed))\b",
                                                                    'Settings/Script',
                                                                    [('set script execution verbose \x01<SWITCH>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define execution verbose state]',
                                                                                # description
                                                                                'Set if script execution is verbose or not\n'
                                                                                'When execution is verbose mode, each executed action print information in console;'
                                                                                'this mode can allows to better understand result (what is executed) but execution will be slower\n\n'
                                                                                'Given *<SWITCH>* can be:\n'
                                                                                ' - **`ON`**: enable execution to be verbose\n'
                                                                                ' - **`OFF`**: do not enable execution to be verbose',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set text italic ON`**\n\n'
                                                                                'Will define text as italic')),
                                                                    ('set script randomize seed \x01<SEED>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define execution randomize seed for random numbers]',
                                                                                # description
                                                                                'Set seed used to generate randomized numbers\n'
                                                                                'Given *<SEED>* can be:\n'
                                                                                ' - **`int`**: any integer number; if negative, a random number will be used as seed\n'
                                                                                ' - **`string`**: any string value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set script randomize seed 999`**\n\n'
                                                                                'Will define value `999` as seed used to generate random numbers')),
                                                                    ],
                                                                    'A'),

            # todo: add |left arc|right arc|bezier|spline
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, r"^\x20*\bdraw\s+(?:line|round\s+square|square|round\s+rect|rect|circle|ellipse|dot|pixel|scaled\s+image|image|text|star)\b",
                                                                    'Drawing/Shapes',
                                                                    [('draw line \x01<LENGTH> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a line]',
                                                                                # description
                                                                                'Draw a line from current point\n'
                                                                                'Given *<LENGTH>* define line lenght and is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw line 40`**\n\n'
                                                                                'Draw a line of 40 pixels length if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw line 40 MM`**\n\n'
                                                                                'Draw a line of 40 millimeters length whatever is default canvas unit')),
                                                                     ('draw square \x01<WIDTH> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a square]',
                                                                                # description
                                                                                'Draw a square for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Sides width are defined by given *<WIDTH>*\n\n'
                                                                                'Given *<WIDTH>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw square 40`**\n\n'
                                                                                'Draw a square of 40 pixels side width if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw square 40 MM`**\n\n'
                                                                                'Draw a square of 40 millimeters side width whatever is default canvas unit')),
                                                                    ('draw round square \x01<WIDTH> [<W-UNIT>] <RADIUS> [<R-UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a rounded square]',
                                                                                # description
                                                                                'Draw a square with rounded corners for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Sides width are defined by given *<WIDTH>*\n'
                                                                                ' - Corners radius are defined by given *<RADIUS>*\n\n'
                                                                                'Given *<WIDTH>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<W-UNIT>`** is omited\n'
                                                                                ' - With given **`<W-UNIT>`** if provided\n\n'
                                                                                'Given *<W-UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches\n\n'
                                                                                'Given *<RADIUS>* is a zero or positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<R-UNIT>`** is omited\n'
                                                                                ' - With given **`<R-UNIT>`** if provided\n\n'
                                                                                'Given *<R-UNIT>* define unit to apply for radius; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`RPCT`**: use percentage relative to square size\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw round square 40 5`**\n\n'
                                                                                'Draw a square of 40 pixels side width with corners radius of 5 pixels if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw square 40 MM 5 PX`**\n\n'
                                                                                'Draw a square of 40 millimeters side width with corners radius of 5 pixels whatever is default canvas unit')),
                                                                    ('draw rect \x01<WIDTH> <HEIGHT> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a rectangle]',
                                                                                # description
                                                                                'Draw a rectangle for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Width is defined by given *<WIDTH>*\n'
                                                                                ' - Height is defined by given *<HEIGHT>*\n\n'
                                                                                'Given *<WIDTH>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<HEIGHT>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw rect 40 20`**\n\n'
                                                                                'Draw a rectangle of 40 pixels width and 20 pixels height if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw rect 40 20 MM`**\n\n'
                                                                                'Draw a square of 40 millimeters and 20 millimeters height whatever is default canvas unit')),
                                                                    ('draw round rect \x01<WIDTH> <HEIGHT> [<S-UNIT>] <RADIUS> [<R-UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a rounded rectangle]',
                                                                                # description
                                                                                'Draw a rectangle with rounded corners for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Width is defined by given *<WIDTH>*\n'
                                                                                ' - Height is defined by given *<HEIGHT>*\n'
                                                                                ' - Corners radius are defined by given *<RADIUS>*\n\n'
                                                                                'Given *<WIDTH>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<S-UNIT>`** is omited\n'
                                                                                ' - With given **`<W-UNIT>`** if provided\n\n'
                                                                                'Given *<HEIGHT>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<S-UNIT>`** is omited\n'
                                                                                ' - With given **`<S-UNIT>`** if provided\n\n'
                                                                                'Given *<S-UNIT>* define unit to apply for width/height; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches\n\n'
                                                                                'Given *<RADIUS>* is a zero or positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<R-UNIT>`** is omited\n'
                                                                                ' - With given **`<R-UNIT>`** if provided\n\n'
                                                                                'Given *<R-UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`RPCT`**: use percentage relative to rectangle size\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw round rect 40 20 5`**\n\n'
                                                                                'Draw a rectangle of 40 pixels width and 20 pixels height with corners radius of 5 pixels if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw round rect 40 20 MM 5 PX`**\n\n'
                                                                                'Draw a square of 40 millimeters and 20 millimeters height with corners radius of 5 pixels whatever is default canvas unit')),
                                                                    ('draw circle \x01<RADIUS> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a circle]',
                                                                                # description
                                                                                'Draw a circle for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Radius is defined by given *<RADIUS>*\n\n'
                                                                                'Given *<RADIUS>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw circle 40`**\n\n'
                                                                                'Draw a circle of 40 pixels radius if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw circle 40 MM`**\n\n'
                                                                                'Draw a circle of 40 millimeters radius whatever is default canvas unit')),
                                                                    ('draw ellipse \x01<H-RADIUS> <V-RADIUS> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw an ellipse]',
                                                                                # description
                                                                                'Draw an ellipse for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Horizontal radius is defined by given *<H-RADIUS>*\n'
                                                                                ' - Vertical radius is defined by given *<V-RADIUS>*\n\n'
                                                                                'Given *<H-RADIUS>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<V-RADIUS>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw ellipse 40 20`**\n\n'
                                                                                'Draw an ellipse of 40 pixels horizontal radius and 20 pixels vertical radius if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw ellipse 40 20 MM`**\n\n'
                                                                                'Draw an ellipse of 40 millimeters horizontal radius and 20 millimeters vertical radius whatever is default canvas unit')),
                                                                    ('draw dot',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a dot]',
                                                                                # description
                                                                                'Draw a dot for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Radius & stroke use current pen definition',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw dot`**\n\n'
                                                                                'Draw dot using current pen color/size definition**')),
                                                                    ('draw pixel',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a pixel]',
                                                                                # description
                                                                                'Draw a single pixel:\n'
                                                                                ' - At current position\n'
                                                                                ' - Use current pen color',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw dot`**\n\n'
                                                                                'Draw dot using current pen color/size definition**')),
                                                                    ('draw image \x01<IMAGE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw an image (using native dimension)]',
                                                                                # description
                                                                                'Draw an image for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Dimension is original image dimension\n'
                                                                                ' - Content is defined by given reference <IMAGE>\n\n'
                                                                                'Given *<IMAGE>* is a string reference to an image:\n'
                                                                                ' - Can be full path/file name to a PNG/JPEG image\n'
                                                                                ' - Can be a reference to a pre-loaded image',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw image "~/Images/test.png"`**\n\n'
                                                                                'Draw image file "~/Images/test.png" to current position**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw image "testing image"`**\n\n'
                                                                                'Draw pre-loaded image referenced by  id "testing image" to current position**')),
                                                                    ('draw scaled image \x01<IMAGE> <WIDTH> <HEIGHT> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw an image (using given dimensions)]',
                                                                                # description
                                                                                'Draw an image for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Dimension is scaled to given <WIDTH> and <HEIGHT>\n'
                                                                                ' - Content is defined by given reference <IMAGE>\n\n'
                                                                                'Given *<IMAGE>* is a string reference to an image:\n'
                                                                                ' - Can be full path/file name to a PNG/JPEG image\n'
                                                                                ' - Can be a reference to a pre-loaded image'
                                                                                'Given *<WIDTH>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<HEIGHT>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`UNIT`** is omited\n'
                                                                                ' - With given **`UNIT`** if provided\n\n'
                                                                                'Given *<UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`RPCT`**: use percentage relative to original image size\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw scaled image "~/Images/test.png" 50 50 RPCT`**\n\n'
                                                                                'Draw image file "~/Images/test.png" to current position, scaled at 50% of original width and height**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw image "testing image" 100 150 PX`**\n\n'
                                                                                'Draw pre-loaded image referenced by  id "testing image" to current position, scaled at 100 pixels width and 150 pixels height**')),
                                                                    ('draw text \x01<TEXT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a text]',
                                                                                # description
                                                                                'Draw a text for which:\n'
                                                                                ' - Position is relative to current position according to text alignment rules\n'
                                                                                ' - Text size, color, style is defined by current text definition\n'
                                                                                ' - Content is defined by given <TEXT>\n\n'
                                                                                'Given *<TEXT>* is a string that define text to draw\n'
                                                                                ' - Use `\\n` text sequence for a carriage return\n\n',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw text "Hello!"`**\n\n'
                                                                                'Draw text "Hello!" to current position using current font definition**')),
                                                                    ('draw star \x01<BRANCHES> <O-RADIUS> [<OR-UNIT>] <I-RADIUS> [<IR-UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Draw a star]',
                                                                                # description
                                                                                'Draw a star for which:\n'
                                                                                ' - Center is current position\n'
                                                                                ' - Border use current pen definition\n'
                                                                                ' - Area use current fill definition\n'
                                                                                ' - Number of branches is defined by given *<BRANCHES>*\n'
                                                                                ' - Outer radius is defined by given *<O-RADIUS>*\n'
                                                                                ' - Inner radius is defined by given *<I-RADIUS>*\n\n'
                                                                                'Given *<BRANCHES>* is an integer number that define number of branches for star; must be greater or equal to **`3`**\n\n'
                                                                                'Given *<O-RADIUS>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<OR-UNIT>`** is omited\n'
                                                                                ' - With given **`<OR-UNIT>`** if provided\n\n'
                                                                                'Given *<OR-UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches\n\n'
                                                                                'Given *<I-RADIUS>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<IR-UNIT>`** is omited\n'
                                                                                ' - With given **`<IR-UNIT>`** if provided\n\n'
                                                                                'Given *<IR-UNIT>*, if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`RPCT`**: use percentage relative to outer radius\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`draw star 5 40 20`**\n\n'
                                                                                'Draw a 5 branches star of 40 pixels outer width radius and 20 pixels inner width radius if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`draw star 8 40 MM 50 RPCT`**\n\n'
                                                                                'Draw a 8 branches star of 40 millimeters outer width radius and 50% (of 40 MM) inner width whatever is default canvas unit')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_MISC, r"^\x20*\b(?:clear\s+canvas|apply\s+to\s+layer)\b",
                                                                    'Drawing/Miscellaneous',
                                                                    [('clear canvas',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Clear canvas content]',
                                                                                # description
                                                                                'Clear current canvas',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`clear canvas`**\n\n'
                                                                                'Will clear all content already drawn on canvas')),
                                                                    ('apply to layer',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Apply result to *Krita*\'s layer]',
                                                                                # description
                                                                                'Apply current canvas content to current *Krita*\'s layer (current layer content is replaced by canvas content)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`apply to layer`**\n\n'
                                                                                'All content drawn on canvas is applied to current layer')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, r"^\x20*\b(?:start|stop)\s+to\s+draw\s+shape\b",
                                                                    'Drawing/Shapes',
                                                                    [('start to draw shape',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Start to draw a shape]',
                                                                                # description
                                                                                'Enter in drawing *shape* mode\n\n'
                                                                                'By default when using **`move`** instructions, drawn lines are not connected.\n'
                                                                                'Entering in *shape* mode will connect all drawn segments in a single shape: this allows in particular to fill area made by drawn segments.\n'
                                                                                'Use action **`stop to draw shape`** to close current shape; in this case if fill mode is active, closed shape area will be filled.'
                                                                                'Action is ignored if *shape* mode is already active',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`start to draw shape`**\n\n'
                                                                                'All following **`move`** actions will be taken in account to define a single shape')),
                                                                    ('stop to draw shape',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Stop to draw a shape]',
                                                                                # description
                                                                                'Leave drawing *shape* mode\n\n'
                                                                                'Leaving *shape* mode will close current shape started with **`start to draw shape`**; in this case if fill mode is active, closed shape area will be filled.'
                                                                                'Action is ignored if *shape* mode is not active',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`stop to draw shape`**\n\n'
                                                                                'All following **`move`** action will close current shape')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_FILL, r"^\x20*\b(?:activate|deactivate)\s+fill\b",
                                                                    'Drawing/Fill',
                                                                    [('activate fill',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Activate fill tool]',
                                                                                # description
                                                                                'Activate fill tool, drawn shapes will be filled out.\n\n'
                                                                                'Use **`deactivate fill`** to stop to fill shapes\n\n'
                                                                                'Action is ignored if fill tool is already activated',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`activate fill`**\n\n'
                                                                                'All drawn shapes will be filled out')),
                                                                    ('deactivate fill',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Deactivate fill tool]',
                                                                                # description
                                                                                'Deactivate fill tool, drawn shapes will be empty.\n\n'
                                                                                'Use **`activate fill`** to start to fill shapes\n\n'
                                                                                'Action is ignored if fill tool is already deactivated',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`deactivate fill`**\n\n'
                                                                                'All drawn shapes will be empty')),
                                                                    ],
                                                                    'A'),

            # todo: |select
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_PEN, r"^\x20*\bpen\s+(?:up|down)\b",
                                                                    'Drawing/Pen',
                                                                    [('pen up',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Deactivate pen stroke]',
                                                                                # description
                                                                                'Deactivate all pen strokes\n\n'
                                                                                'Use `pen down` to start to draw strokes\n\n'
                                                                                'Action is pen is already up',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`pen up`**\n\n'
                                                                                'All `draw` and `move` action won\'t generate srokes')),
                                                                    ('pen down',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Activate pen stroke]',
                                                                                # description
                                                                                'Activate all pen strokes\n\n'
                                                                                'Use `pen up` to stop to draw strokes\n\n'
                                                                                'Action is pen is already up',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`pen down`**\n\n'
                                                                                'All `draw` and `move` action will generate srokes')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, r"^\x20*\bmove\s+(?:home|forward|backward|left|right|to)\b",
                                                                    'Drawing/Move',
                                                                    [('move home',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen to home (origin)]',
                                                                                # description
                                                                                'Move to home coordinates (canvas origin)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move home`**\n\n'
                                                                                'Set current position to origin of canvas')),
                                                                    ('move forward \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen forward]',
                                                                                # description
                                                                                'Move pen in forward direction:\n'
                                                                                ' - Stroke (if active) use current pen definition\n'
                                                                                ' - Distance is defined by given *<VALUE>*\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move forward 40`**\n\n'
                                                                                'Will move of 40px in forward direction if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`move forward 40 MM`**\n\n'
                                                                                'Will move of 40 millimeters in forward direction whatever is default canvas unit')),
                                                                    ('move backward \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen backward]',
                                                                                # description
                                                                                'Move pen in backward direction:\n'
                                                                                ' - Stroke (if active) use current pen definition\n'
                                                                                ' - Distance is defined by given *<VALUE>*\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move backward 40`**\n\n'
                                                                                'Will move of 40px in backward direction if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`move backward 40 MM`**\n\n'
                                                                                'Will move of 40 millimeters in backward direction whatever is default canvas unit')),
                                                                    ('move left \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen to left]',
                                                                                # description
                                                                                'Move pen to left (perpendicularly to current direction):\n'
                                                                                ' - Stroke (if active) use current pen definition\n'
                                                                                ' - Distance is defined by given *<VALUE>*\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move left 40`**\n\n'
                                                                                'Will move of 40px to left perpendicularly to current direction if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`move left 40 MM`**\n\n'
                                                                                'Will move of 40 millimeters to left perpendicularly to current direction whatever is default canvas unit')),
                                                                    ('move right \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen to right]',
                                                                                # description
                                                                                'Move pen to right (perpendicularly to current direction):\n'
                                                                                ' - Stroke (if active) use current pen definition\n'
                                                                                ' - Distance is defined by given *<VALUE>*\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move right 40`**\n\n'
                                                                                'Will move of 40px to right perpendicularly to current direction if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`move right 40 MM`**\n\n'
                                                                                'Will move of 40 millimeters to right perpendicularly to current direction whatever is default canvas unit')),
                                                                    ('move to \x01<X> <Y> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Move pen to absolute position]',
                                                                                # description
                                                                                'Move pen to given absolute position (direction stay unchanged):\n'
                                                                                ' - Stroke (if active) use current pen definition\n'
                                                                                ' - Coordinates are defined by given *<X>* and *<Y>*'
                                                                                'Please note that position (0, 0) is defined by center of canvas\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default canvas unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`PX`**: use pixels\n'
                                                                                ' - **`PCT`**: use percentage of document width/height\n'
                                                                                ' - **`MM`**: use millimeters\n'
                                                                                ' - **`INCH`**: use inches',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`move to 40 -60`**\n\n'
                                                                                'Will move to position (40px, -60px) if default canvas unit is **`PX`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`move to 40 -60 MM`**\n\n'
                                                                                'Will move to position (40 millimeters, -60 millimeters) whatever is default canvas unit')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_DRAW_TURN, r"^\x20*\bturn\s+(?:left|right|to)\b",
                                                                    'Drawing/Turn',
                                                                    [('turn left \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Turn to left direction]',
                                                                                # description
                                                                                'Turn pen in left direction:\n'
                                                                                ' - Rotation angle is defined by given *<VALUE>*'
                                                                                ' - Rotation angle is relative to current direction\n\n'
                                                                                'Given *<VALUE>* is a positive number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`turn left 90`**\n\n'
                                                                                'Will turn to left direction of 90 degrees if default rotation unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`turn left 1.57 RADIAN`**\n\n'
                                                                                'Will turn to left direction of 1.57 radians whatever is default rotation unit')),
                                                                    ('turn right \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Turn to right direction]',
                                                                                # description
                                                                                'Turn pen in right direction:\n'
                                                                                ' - Rotation angle is defined by given *<VALUE>*'
                                                                                ' - Rotation angle is relative to current direction\n\n'
                                                                                'Given *<VALUE>* is a number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`turn right 90`**\n\n'
                                                                                'Will turn to right direction of 90 degrees if default rotation unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`turn right 1.57 RADIAN`**\n\n'
                                                                                'Will turn to right direction of 1.57 radians whatever is default rotation unit')),
                                                                    ('turn to \x01<VALUE> [<UNIT>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Turn direction to given absolute rotation value]',
                                                                                # description
                                                                                'Turn pen in absolute direction:\n'
                                                                                ' - Rotation angle is defined by given *<VALUE>*'
                                                                                ' - Rotation angle is absolute: 0 is UP direction\n\n'
                                                                                'Given *<VALUE>* is a number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`turn to 0`**\n\n'
                                                                                'Will set direction to 0 degrees if default rotation unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`turn to 3.14 RADIAN`**\n\n'
                                                                                'Will set direction to 3.14 radians whatever is default rotation unit')),
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_STATE, r"^\x20*\b(?:push|pop)\s+state\b",
                                                                    'State',
                                                                    [('push state',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Push current state in stack (save current properties)]',
                                                                                # description
                                                                                'Push current state in stack'
                                                                                'All current properties (unit, pen, fill, font, ...) are saved; restore values with **`pop state`**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`push state`**\n\n'
                                                                                'Will keep all current properties values in stack')),
                                                                    ('pop state',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Pop current state from stack (restore previous properties)]',
                                                                                # description
                                                                                'pop current state from stack'
                                                                                'All saved properties (unit, pen, fill, font, ...) are restored; save values with **`push state`**\n\n'
                                                                                'If stack is empty, action is ignored',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`pop state`**\n\n'
                                                                                'Will restore all saved properties values from stack')),
                                                                    ],
                                                                    'A'),

            # todo: actions filters, document, layer, selection



            TokenizerRule(BSLanguageDef.ITokenType.ACTION_CANVAS, r"^\x20*\b(?:show|hide)\s+canvas\s+(?:grid|origin|position|background|rulers)\b",
                                                                    'Canvas',
                                                                    [('show canvas grid',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas grid visible]',
                                                                                # description
                                                                                'Render grid over canvas\n'
                                                                                'Grid is drawn over canvas and is not rendered on final drawing')),
                                                                    ('show canvas origin',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas origin visible]',
                                                                                # description
                                                                                'Render origin over canvas\n'
                                                                                'Origin is drawn over canvas and is not rendered on final drawing')),
                                                                    ('show canvas position',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set pen position/direction visible]',
                                                                                # description
                                                                                'Render pen position over canvas\n'
                                                                                'Pen position/direction is drawn over canvas and is not rendered on final drawing')),
                                                                    ('show canvas background',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set background visible]',
                                                                                # description
                                                                                'Render background under canvas\n'
                                                                                'Background (made from current document projection) is drawn under canvas and is not rendered on final drawing')),
                                                                    ('show canvas rulers',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas rulers visible]',
                                                                                # description
                                                                                'Render rulers over canvas\n'
                                                                                'Rulers are drawn over canvas and are not rendered on final drawing')),
                                                                    ('hide canvas grid',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas grid invisible]',
                                                                                # description
                                                                                'Do not render grid')),
                                                                    ('hide canvas origin',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas origin invisible]',
                                                                                # description
                                                                                'Do not render origin')),
                                                                    ('hide canvas position',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set pen position/direction invisible]',
                                                                                # description
                                                                                'Do not render position/direction')),
                                                                    ('hide canvas background',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set background invisible]',
                                                                                # description
                                                                                'Do not render background')),
                                                                    ('hide canvas rulers',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set canvas rulers invisible]',
                                                                                # description
                                                                                'Do not render rulers'))
                                                                    ],
                                                                    'A'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_UIDIALOG, r"^\x20*\bopen\s+dialog\s+for\s+(?:string|integer|decimal|color|boolean|single\s+choice|multiple\s+choice)\s+input\b", #|(?:single|multiple)\s+choice
                                                                    'User interface/Window',
                                                                    [('open dialog for string input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog string]',
                                                                                # description
                                                                                'Ask user for input a string value\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with default value`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for string input :value`**\n\n'
                                                                                'Will open a dialog box to ask user for a string value and store result into variable `:value`')),
                                                                    ('open dialog for integer input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog integer]',
                                                                                # description
                                                                                'Ask user for input an integer value\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with default value`\n'
                                                                                '- `with minimum value`\n'
                                                                                '- `with maximum value`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for integer input :value`**\n\n'
                                                                                'Will open a dialog box to ask user for an integer value and store result into variable `:value`')),
                                                                    ('open dialog for decimal input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog decimal]',
                                                                                # description
                                                                                'Ask user for input an decimal value\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with default value`\n'
                                                                                '- `with minimum value`\n'
                                                                                '- `with maximum value`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for decimal input :value`**\n\n'
                                                                                'Will open a dialog box to ask user for a decimal value and store result into variable `:value`')),
                                                                    ('open dialog for color input \x01<:variable>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog color]',
                                                                                # description
                                                                                'Ask user for input a color value\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with default value`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for color input :value`**\n\n'
                                                                                'Will open a dialog box to ask user for a color value and store result into variable `:value`')),
                                                                    ('open dialog for boolean input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog boolean]',
                                                                                # description
                                                                                'Ask user to provide a YES or NO answer\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for boolean input :value`**\n\n'
                                                                                'Will open a dialog box to ask user to click on YES or NO button and store result into variable `:value`')),
                                                                    ('open dialog for single choice input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog with different possibles value]',
                                                                                # description
                                                                                'Ask user to select on value in possible provided values\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored (and index value, starting from 1)\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with combobox choices`\n'
                                                                                '- `with radio button choices`\n'
                                                                                '- `with default index`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for choice input :value`**\n'
                                                                                '**`     with combobox choices ["Red", "Green", "Blue"]`**\n\n'
                                                                                'Will open a dialog box to ask user to select one value from provided choices, and store index of selected choice into `:value`')),
                                                                    ('open dialog for multiple choice input \x01<:USER-VARIABLE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display an input dialog with different possibles value]',
                                                                                # description
                                                                                'Ask user to select on value in possible provided values\n\n'
                                                                                'Given *<:USER-VARIABLE>* define variable in which input data is stored (a list of index values)\n\n'
                                                                                'Following options can be set:\n'
                                                                                '- `with title`\n'
                                                                                '- `with message`\n'
                                                                                '- `with choices`\n'
                                                                                '- `with default index`\n'
                                                                                '- `with minimum choices`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for choice input :value`**\n'
                                                                                '**`     with combobox choices ["Red", "Green", "Blue"]`**\n\n'
                                                                                'Will open a dialog box to ask user to select one value from provided choices, and store index of selected choice into `:value`')),
                                                                    ],
                                                                    'A'),
            TokenizerRule(BSLanguageDef.ITokenType.ACTION_UIDIALOG, r"^\x20*\bopen\s+dialog\s+for\s+message\b",
                                                                    'User interface/Window',
                                                                    [('open dialog for message',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Display a message dialog]',
                                                                                # description
                                                                                'Open a dialog box to display a message\n\n'
                                                                                'Use options to define dialog box title and message',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for message`**\n'
                                                                                '**`     with title "Important information"`**\n\n'
                                                                                '**`     with message "This is an important message!"`**\n\n'
                                                                                'Will open a dialog box to display message `This is an important message!`')),
                                                                    ],
                                                                    'A'),


            TokenizerRule(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, r"\x20*\bwith\s+(?:title|message|minimum\s+(?:value|choices)|maximum\s+value|default\s+(?:value|index)|(?:combobox\s+|radio\s+button\s+)?choices)\b",
                                                                    'User interface/Window/Options',
                                                                    [('with title \x01<TEXT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: title]',
                                                                                # description
                                                                                'Define title for input dialog\n\n'
                                                                                'Given *<TEXT>* is a string',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for string input :value`**\n'
                                                                                '**`     with title "Need user information"`**\n\n'
                                                                                'Will open a dialog box for which title is `Need user information`')),
                                                                    ('with message \x01<TEXT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: message]',
                                                                                # description
                                                                                'Define message for input dialog\n\n'
                                                                                'Given *<TEXT>* is a string',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for string input :value`**\n'
                                                                                '**`     with message "Please provide user name"`**\n\n'
                                                                                'Will open a dialog box for which message is `Please provide user name`')),
                                                                    ('with minimum value \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: minimum value]',
                                                                                # description
                                                                                'Define minimum value for input dialog\n\n'
                                                                                'Given *<VALUE>* is:\n'
                                                                                '- **`int`**: for integer input dialog\n'
                                                                                '- **`dec`**: for decimal input dialog\n\n'
                                                                                '*Option is not allowed for input dialog box other than **integer** and **decimal**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for integer input :value`**\n'
                                                                                '**`     with minimum value 0`**\n\n'
                                                                                'Will open a dialog box for which minimum integer value is 0')),
                                                                    ('with maximum value \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: maximum value]',
                                                                                # description
                                                                                'Define maximum value for input dialog\n\n'
                                                                                'Given *<VALUE>* is:\n'
                                                                                '- **`int`**: for integer input dialog\n'
                                                                                '- **`dec`**: for decimal input dialog\n\n'
                                                                                '*Option is not allowed for input dialog box other than **integer** and **decimal**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for decimal input :value`**\n'
                                                                                '**`     with maximum value 100.0`**\n\n'
                                                                                'Will open a dialog box for which maximum decimal value is 100.00')),
                                                                    ('with default value \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: default value]',
                                                                                # description
                                                                                'Define default value for input dialog\n\n'
                                                                                'Given *<VALUE>* is:\n'
                                                                                '- **`string`**: for string input dialog\n'
                                                                                '- **`int`**: for integer input dialog\n'
                                                                                '- **`dec`**: for decimal input dialog\n'
                                                                                '- **`color`**: for color input dialog\n\n'
                                                                                '*Option is not allowed for input dialog box other than **string**, **integer**, **decimal** and **color**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for integer input :value`**\n'
                                                                                '**`     with default value 25`**\n\n'
                                                                                'Will open a dialog box for which default value is 25')),
                                                                    ('with combobox choices \x01<LIST>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: list of choice values, provided in a combobox list]',
                                                                                # description
                                                                                'Define list of values for input dialog, provided as a combobox list\n\n'
                                                                                'Given *<LIST>* is a list of string\n\n'
                                                                                '*Option is not allowed for input dialog box other than **single choice**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for single choice input :value`**\n'
                                                                                '**`     with combobox choices ["Item A", "Item B", "Item C"]`**\n\n'
                                                                                'Will open a dialog box for which a combobox list will provide 3 possible values')),
                                                                    ('with radio button choices \x01<LIST>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: list of choice values, provided as radio button items]',
                                                                                # description
                                                                                'Define list of values for input dialog, provided as radio button items\n\n'
                                                                                'Given *<LIST>* is a list of string\n\n'
                                                                                '*Option is not allowed for input dialog box other than **single choice**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for single choice input :value`**\n'
                                                                                '**`     with radio button choices ["Item A", "Item B", "Item C"]`**\n\n'
                                                                                'Will open a dialog box for which radio buttons will provide 3 possible values')),
                                                                    ('with choices \x01<LIST>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: list of choice values, provided as checkbox items]',
                                                                                # description
                                                                                'Define list of values for input dialog, provided as checkbox items\n\n'
                                                                                'Given *<LIST>* is a list of string\n\n'
                                                                                '*Option is not allowed for input dialog box other than **multiple choice**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for multiple choice input :value`**\n'
                                                                                '**`     with choices ["Item A", "Item B", "Item C"]`**\n\n'
                                                                                'Will open a dialog box for which 3 checkbox are provided')),
                                                                    ('with default index \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: default value(s) for choices dialog box]',
                                                                                # description
                                                                                'Define default selected index for choices input dialog\n\n'
                                                                                'Given *<VALUE>* can be:\n'
                                                                                '- An **`int`** value, to define a selected index in choices (**`single choice`** and **`multiple choice`**)\n'
                                                                                '- A list of **`int`** value, to define all selected indexes in choices (**`multiple choice`**)\n'
                                                                                '*Option is not allowed for input dialog box other than **single choice** and **multilpe choice**\n\n'
                                                                                'Index value in list start from 1',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for multiple choice input :value`**\n'
                                                                                '**`     with choices ["Item A", "Item B", "Item C"]`**\n'
                                                                                '**`     with defaul index [1, 3]`**\n\n'
                                                                                'Will open a dialog box for which a multiple choice list is provided, with values `Item A` and `Item C` already selected')),
                                                                    ('with minimum choices \x01<VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Set dialog option: minimum number of values that must be selected for multiple choice dialog box]',
                                                                                # description
                                                                                'Define minimum number of selected indexes expected in a multiple choices input dialog\n\n'
                                                                                'Given *<VALUE>* can be:\n'
                                                                                '- An **`int`** value, to define a selected index in choices (**`single choice`** and **`multiple choice`**)\n'
                                                                                '- A list of **`int`** value, to define all selected indexes in choices (**`multiple choice`**)\n'
                                                                                '*Option is not allowed for input dialog box other than **multilpe choice**',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`open dialog for multiple choice input :value`**\n'
                                                                                '**`     with choices ["Item A", "Item B", "Item C"]`**\n'
                                                                                '**`     with minimum choices 2`**\n\n'
                                                                                'Will open a dialog box for which a multiple choice list is provided, and user must check at least 2 of 3 items')),
                                                                    ],
                                                                    'A',
                                                                    ignoreIndent=True),


            TokenizerRule(BSLanguageDef.ITokenType.ACTION_UICONSOLE, r"^\x20*\bprint\b",
                                                                    'User interface/Console',
                                                                    [('print \x01<INFO>[, <INFO>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Print information to console]',
                                                                                # description
                                                                                'Print given *<INFO>* to console\n\n'
                                                                                'Given *<INFO>* can be of any type, and any number of <INFO> can be provided',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`print "hello!"`**\n\n'
                                                                                'Will print text `hello!` to console')),
                                                                    ],
                                                                    'A'),


            TokenizerRule(BSLanguageDef.ITokenType.FLOW_EXEC, r"^\x20*\bstop\s+script\b",
                                                                    'Flow/Execution',
                                                                    [('stop script',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Stop script execution]',
                                                                                # description
                                                                                'Stop script execution')),
                                                                    ],
                                                                    'F'),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_CALL, r"^\x20*\bcall\s+macro\b",
                                                                    'Flow/Execution',
                                                                    [('call macro "\x01<MACRO>\x01"\x01 [<ARG1>[ <ARGN>]]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Call/Execute a macro]',
                                                                                # description
                                                                                'Call and execute macro <MACRO> with provided arguments\n\n'
                                                                                'Given *<MACRO>* is a user defined macro; if macro is not defined, script will stop\n'
                                                                                'Optional arguments are passed to macro',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`call macro "shape" 45`**\n\n'
                                                                                'Will call and execute macro `shape` with value `45` for argument')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_DEFMACRO, r"^\x20*\bdefine\s+macro\b",
                                                                    'Flow/Declarations',
                                                                    [('define macro "\x01<NAME>\x01"\x01 [\x01with parameters\x01 <ARG1> [<ARGN>]]\x01 as',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Define a macro]',
                                                                                # description
                                                                                'Define a macro\n\n'
                                                                                'Given *<MACRO>* is a user defined macro; if macro is not defined, script will stop\n'
                                                                                'Arguments, if any, are defined as variables\n\n'
                                                                                'Note that action `push state` and `pop state` are automatically applied when entering/leaving a macro',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`define macro "square" :size`**\n'
                                                                                '**`    pen down`**\n'
                                                                                '**`    repeat 4 times`**\n'
                                                                                '**`        move forward :size`**\n'
                                                                                '**`        turn left 90`**\n\n'
                                                                                'Will define a macro named `"square"` that will draw a square for which each side is 45 units')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_RETURN, r"^\x20*\breturn\b",
                                                                    'Flow/Execution',
                                                                    [('return \x01[<VALUE>]',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Exit macro]',
                                                                                # description
                                                                                'Exit a macro and return optional givne <VALUE>',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`define macro "twice" :value`**\n'
                                                                                '**`    return (2 * :value)`**\n'
                                                                                'Will define a macro named `"twice"` that will return given `:value` multiplied by 2')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_IMPORT, r"^\x20*\bimport\s+(?:macro|image)\s+from\b",
                                                                    'Flow/Declarations',
                                                                    [('import macro from \x01<TEXT>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Import macro defined from an another script document]',
                                                                                # description
                                                                                'Import macro from defined path\n'
                                                                                'When imported, only defined macro are taken in account\n'
                                                                                'If imported script contain execution flow, they\'re ignored\n\n'
                                                                                'Given *<TEXT>* is a string that define a BuliScript file name; can be:\n'
                                                                                '- A full path/file name\n'
                                                                                '- A file name: in this case, consider that file is in the same directory than executed script',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`import macro from "my_filename.bs"`**\n\n'
                                                                                'Will import all macro defined in file `my_filename.bs`')),
                                                                    ('import image from \x01<TEXT> \x01as \x01<RESNAME>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Import an image]',
                                                                                # description
                                                                                'Import image from defined path <TEXT> and store it as <RESNAME>\n'
                                                                                'When imported, image is loaded once and stored in memory and can be used with action that need image as parameter\n'
                                                                                'This can avoid for action that use image to execute load on each call (especially in loops)\n\n'
                                                                                'Given *<TEXT>* is a string that define a PNG/JPEG file name; can be:\n'
                                                                                '- A full path/file name\n'
                                                                                '- A file name: in this case, consider that file is in the same directory than executed script',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`import image from "test_brush.png" as "test brush"`**\n\n'
                                                                                'Will load image `test_brush.png` and store it in memory with `test brush` for identifier')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_REPEAT, r"^\x20*\brepeat\b",
                                                                    'Flow/Loops',
                                                                    [('repeat \x01<COUNT>\x01 times',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Repeat a statement a number of times]',
                                                                                # description
                                                                                'Repeat following statement <COUNT> times',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`repeat 4 times`**\n'
                                                                                '**`    move forward 10`**\n'
                                                                                '**`    turn left 90`**\n\n'
                                                                                'Will repeat 4 times the action to move forward and turn left 90 degrees (draw square)')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_FOREACH, r"^\x20*\bfor\s+each\s+item\s+from\b",
                                                                    'Flow/Loops',
                                                                    [('for each item from \x01<LIST>\x01 as \x01:variable\x01 do',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Loop over items in a list]',
                                                                                # description
                                                                                'Iterate over given <LIST>\n'
                                                                                'On each iteration *`:variable` is defined with value from <LIST>\n\n'
                                                                                'Given *<LIST>* can be:\n'
                                                                                ' - **`list`**: iterate over all item in list\n',
                                                                                ' - **`string`**: a string is in this case considered as a list of characters'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`for each item from "test" as :character do`**\n'
                                                                                '**`    draw text :character`**\n'
                                                                                '**`    move forward 40`**\n\n'
                                                                                'Will iterate over all characters in string "test", draw character and move forward from 40 pixels')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_TIMES, r"\x20*\btimes\b",
                                                                    None,
                                                                    ['times'],
                                                                    'F',
                                                                    ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_AS, r"\x20*\bas\b",
                                                                    None,
                                                                    ['as'],
                                                                    'F',
                                                                    ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_DO, r"\x20*\bdo\b",
                                                                    None,
                                                                    ['do'],
                                                                    'F',
                                                                    ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_THEN, r"\x20*\bthen\b",
                                                                    None,
                                                                    ['then'],
                                                                    'F',
                                                                    ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_AND_STORE_RESULT, r"\x20*\band\s+store\s+result\s+into\s+variable\b",
                                                                    None,
                                                                    ['and store result into variable \x01:variable'],
                                                                    'F',
                                                                    ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_WITH_PARAMETERS, r"\x20*\bwith\s+parameters\b",
                                                                    None,
                                                                    ['with parameters'],
                                                                    'F',
                                                                    ignoreIndent=True),


            TokenizerRule(BSLanguageDef.ITokenType.FLOW_SET_VARIABLE, r"^\x20*\bset(?:\s+global)?\s+variable\b",
                                                                    'Flow/Variables',
                                                                    [('set variable \x01:variable = <VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Set value for a variable]',
                                                                                # description
                                                                                'Set value <VALUE> for given user defined `:variable`',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set variable :test = 100`**\n\n'
                                                                                'Will define user defined variable `:test` with integer value `100`')),
                                                                    ('set global variable \x01:variable = <VALUE>',
                                                                            TokenizerRule.formatDescription(
                                                                                'Flow [Set value for a global variable]',
                                                                                # description
                                                                                'Set value <VALUE> for given user defined `:variable`, defined as a global variable: when used in a macro, variable will be available outside macro scope',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`set global variable :test = 100`**\n\n'
                                                                                'Will define user defined global variable `:test` with integer value `100`')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_ELIF, r"^\x20*\belse\s+if\b",
                                                                    'Flow/Conditional statements',
                                                                    [('else if \x01<CONDITION>\x01 then',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define a conditional statement *`else if`*]',
                                                                                # description
                                                                                'Execute statement if previous statement wasn\'t executed, and if given condition is true')),
                                                                    ],
                                                                    'F'),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_ELSE, r"^\x20*\belse\b",
                                                                    'Flow/Conditional statements',
                                                                    [('else',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define a conditional statement *`else`*]',
                                                                                # description
                                                                                'Execute statement if previous statement wasn\'t executed')),
                                                                    ],
                                                                    'F'),
            TokenizerRule(BSLanguageDef.ITokenType.FLOW_IF, r"^\x20*\bif\b",
                                                                    'Flow/Conditional statements',
                                                                    [('if \x01<CONDITION>\x01 then',
                                                                            TokenizerRule.formatDescription(
                                                                                'Action [Define a conditional statements *`if`*]',
                                                                                # description
                                                                                'Execute statement if given condition is true')),
                                                                    ],
                                                                    'F'),

            TokenizerRule(BSLanguageDef.ITokenType.ACTION_UNCOMPLETE, r"^\x20*\b(?:"
                                                                       r"(?:set(?:\s+(?:unit|pen|fill|text\s+letter|text\s+horizontal|text\s+vertical|text|draw|script\s+execution|script\s+randomize|script|canvas\s+background\s+from\s+layer|canvas\s+background\s+from|canvas\s+background)))"
                                                                       r"|(?:draw(:?\s+(?:round|scaled))?)"
                                                                       r"|(?:(?:start|stop)(?:\s+to(\s+draw)?)?)"
                                                                       r"|(?:clear|apply(?:\s+to)?)"
                                                                       r"|(?:pen|move|turn|push|pop|activate|deactivate)"
                                                                       r"|(?:(?:show|hide)(?:\s+(?:canvas))?)"
                                                                       r"|(?:open(?:\s+dialog(?:\s+for(?:\s+(?:string|integer|decimal|color|boolean|(?:single|multiple)(?:\s+choice)?))?)?)?)"
                                                                       r"|(?:with(?:\s+(?:minimum|maximum|default|(?:combobox|radio(\s+button)?)))?)"
                                                                       r")\b"
                                                                       ),
                                                                       # (?:single|multiple) (?:\s+(?:choice)?)?
                                                                       # (?:combobox|radio)(?:\s+(?:button)?)?

            TokenizerRule(BSLanguageDef.ITokenType.FLOW_UNCOMPLETE, r"^\x20*\b(?:"
                                                                       r"|(?:stop|call|define|for(?:\s+(?:each(?:\s+(?:item))?))?)"
                                                                       r"|(?:import(?:\s+(?:macro|image))?)"
                                                                       r"|(?:set\s+global)"
                                                                       r"|(?:and\s+store(?:\s+(?:result(?:\s+(?:into))?))?)"
                                                                       r")\b"
                                                                       ),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:random)\b",
                                                                    'Functions/Math/Random numbers',
                                                                    [('math.random()',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a *random* value]',
                                                                                # description
                                                                                'Return a random value between 0.0 and 1.0\n'
                                                                                'Returns a decimal value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.random()`**\n\n'
                                                                                'Will return a value a random value')),
                                                                    ('math.random(\x01<MIN>, <MAX>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a *bounded random* value]',
                                                                                # description
                                                                                'Return a random value between <MIN> and <MAX>\n'
                                                                                'Returns an integer value if both minimum and maximum values are integer, otherwise returns a decimal value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.random(-10, 10)`**\n\n'
                                                                                'Will return an integer random value between -10 and 10\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.random(-10.0, 10.0)`**\n\n'
                                                                                'Will return a decimal random value between -10.0 and 10.0')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:absolute|even|odd|sign)\b",
                                                                    'Functions/Math/Numbers',
                                                                    [('math.absolute(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *absolute* value for a given number]',
                                                                                # description
                                                                                'Calculate absolute value for given <VALUE>\n'
                                                                                'Returns an integer or decimal value (according to <VALUE> type)\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.absolute(-4)`**\n\n'
                                                                                'Will return value **`4`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.absolute(-4.0)`**\n\n'
                                                                                'Will return value **`4.0`**')),
                                                                    ('math.sign(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *sign* value for a given number]',
                                                                                # description
                                                                                'Return -1, 0, 1 (or -1.0, 0.0, 1.0) according to given <VALUE> sign\n'
                                                                                'Returns an integer or decimal value (according to <VALUE> type)\n'
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.sign(-4)`**\n\n'
                                                                                'Will return value **`-1`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.sign(4.0)`**\n\n'
                                                                                'Will return value **`1.0`**')),
                                                                    ('math.even(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return if given number is an *even* number]',
                                                                                # description
                                                                                'Return ON if given <VALUE> is an even number otherwise return OFF\n'
                                                                                'Returns a boolean',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.even(4)`**\n\n'
                                                                                'Will return `ON`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.even(5)`**\n\n'
                                                                                'Will return a`OFF`')),
                                                                    ('math.odd(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return if given number is an *odd* number]',
                                                                                # description
                                                                                'Return ON if given <VALUE> is an odd number otherwise return OFF\n'
                                                                                'Returns a boolean',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.odd(4)`**\n\n'
                                                                                'Will return `OFF`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.even(4)`**\n\n'
                                                                                'Will return a`ON`')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:exp|logn?|power|squareRoot)\b",
                                                                    'Functions/Math/Power and Logarithmic',
                                                                    [('math.exp(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *exponential* value for a given number]',
                                                                                # description
                                                                                'Calculate exponential value for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.exp(2)`**\n\n'
                                                                                'Will return value *`e`* to the power of `4` (2.718281828459045^4)')),
                                                                    ('math.power(\x01<VALUE>, <POWER>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *power* for a given number]',
                                                                                # description
                                                                                'Calculate given <VALUE> raised to the power of <POWER>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* and *<POWER>* are a numbers',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.power(4, 2)`**\n\n'
                                                                                'Will return value *`4`* to the power of `2` (4^2)')),
                                                                    ('math.squareRoot(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *square root* value for a given number]',
                                                                                # description
                                                                                'Calculate square root for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.squareRoot(4)`**\n\n'
                                                                                'Will return value **`2.00`**')),
                                                                    ('math.logn(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *natural logarithm* for a given number]',
                                                                                # description
                                                                                'Calculate natural logarithm for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a number')),
                                                                    ('math.log(\x01<VALUE>[, <BASE>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *logarithm* for a given number]',
                                                                                # description
                                                                                'Calculate logarithm for given <VALUE> using given <BASE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a number\n'
                                                                                'Given *<BASE>* is a number; if not provided default value is 10 (base 10 logarithm)')),

                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:convert)\b",
                                                                    'Functions/Math/Convert',
                                                                    [('math.convert(\x01<VALUE>, <F-UNIT>, <T-UNIT>[, <PCT-REF>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Convert a value from a unit to another one]',
                                                                                # description
                                                                                'Convert  given <VALUE> from unit <F-UNIT> to unit <T-UNIT>\n'
                                                                                'If a conversion unit is given in PCT, by default conversion is made from layer width; use <PCT-REF> to provide WIDTH or HEIGHT reference to use for conversion.\n'
                                                                                'Returns a decimal value\n',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.convert(18, MM, PX)`**\n\n'
                                                                                'Will convert value of 18 millimeters in pixels')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:minimum|maximum|average|sum|product)\b",
                                                                    'Functions/Math/List',
                                                                    [('math.minimum(\x01<VALUE1>[, <VALUEN>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return the *minimum* value from a list and/or from given arguments]',
                                                                                # description
                                                                                'Return the minimum value from given <VALUEx> arguments',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.minimum(10, 5, 25, -4)`**\n'
                                                                                '**`math.minimum([10, 5, 25, -4])`**\n'
                                                                                '**`math.minimum([10, 5], [25, -4])`**\n\n'
                                                                                'Will return minimum value `-4`')),
                                                                    ('math.maximum(\x01<VALUE1>[, <VALUEN>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [MReturn the *maximum* value from a list and/or from given arguments]',
                                                                                # description
                                                                                'Return the maximum value from given <VALUEx> arguments',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.maximum(10, 5, 25, -4)`**\n'
                                                                                '**`math.maximum([10, 5, 25, -4])`**\n'
                                                                                '**`math.maximum([10, 5], [25, -4])`**\n\n'
                                                                                'Will return maximum value `25`')),
                                                                    ('math.average(\x01<VALUE1>[, <VALUEN>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return the *average* value from a list and/or from given arguments]',
                                                                                # description
                                                                                'Return the average value from given <VALUEx> arguments',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.average(10, 5, 25, -4)`**\n'
                                                                                '**`math.average([10, 5, 25, -4])`**\n'
                                                                                '**`math.average([10, 5], [25, -4])`**\n\n'
                                                                                'Will return average value `9.0`')),
                                                                    ('math.sum(\x01<VALUE1>[, <VALUEN>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return the *sum* of values from a list and/or from given arguments]',
                                                                                # description
                                                                                'Return the sum value from given <VALUEx> arguments',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.sum(10, 5, 25, -4)`**\n'
                                                                                '**`math.sum([10, 5, 25, -4])`**\n'
                                                                                '**`math.sum([10, 5], [25, -4])`**\n\n'
                                                                                'Will return sum value `36`')),
                                                                    ('math.product(\x01<VALUE1>[, <VALUEN>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return the *product* of values from a list and/or from given arguments]',
                                                                                # description
                                                                                'Return the product value from given <VALUEx> arguments',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.product(10, 5, 25, -4)`**\n'
                                                                                '**`math.product([10, 5, 25, -4])`**\n'
                                                                                '**`math.product([10, 5], [25, -4])`**\n\n'
                                                                                'Will return product value `-5000`')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:ceil|floor|round)\b",
                                                                    'Functions/Math/Rounding',
                                                                    [('math.ceil(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *ceil* value for a given number]',
                                                                                # description
                                                                                'Calculate ceil for given <VALUE>\n'
                                                                                'Returns an integer value\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`math.ceil(1.11)`**\n'
                                                                                '**`math.ceil(1.99)`**\n\n'
                                                                                'Will both return value **`2`**')),
                                                                    ('math.floor(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *floor* value for a given number]',
                                                                                # description
                                                                                'Calculate floor for given <VALUE>\n'
                                                                                'Returns an integer value\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`math.floor(1.11)`**\n'
                                                                                '**`math.floor(1.99)`**\n\n'
                                                                                'Will both return value **`1`**')),
                                                                    ('math.round(\x01<VALUE>[, <DECIMALS>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *round* value for a given number]',
                                                                                # description
                                                                                'Calculate round for given <VALUE>\n'
                                                                                'Returns an integer value if decimals is 0, otherwise returns a decimal value\n'
                                                                                'Given *<VALUE>* is a number',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.round(1.495, 2)`**\n\n'
                                                                                'Will return value **`1.50`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.round(1.494, 2)`**\n\n'
                                                                                'Will return value **`1.49`**')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:a?cos|a?sin|a?tan)\b",
                                                                    'Functions/Math/Trigonometric',
                                                                    [('math.cos(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *cosine* for a given number]',
                                                                                # description
                                                                                'Calculate cosine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.cos(45)`**\n\n'
                                                                                'Will calculate value of cosine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.cos(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of cosine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.sin(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *sine* for a given number]',
                                                                                # description
                                                                                'Calculate sine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.sin(45)`**\n\n'
                                                                                'Will calculate value of sine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.sin(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of sine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.tan(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *tangent* for a given number]',
                                                                                # description
                                                                                'Calculate tangent for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.tan(45)`**\n\n'
                                                                                'Will calculate value of tangent of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.tan(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of tangent of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.acos(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *arc cosine* for a given number]',
                                                                                # description
                                                                                'Calculate arc cosine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.acos(45)`**\n\n'
                                                                                'Will calculate value of arc cosine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.acos(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of arc cosine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.asin(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *arc sine* for a given number]',
                                                                                # description
                                                                                'Calculate arc sine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.asin(45)`**\n\n'
                                                                                'Will calculate value of arc sine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.asin(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of arc sine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.atan(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *arc tangent* for a given number]',
                                                                                # description
                                                                                'Calculate arc tangent for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.atan(45)`**\n\n'
                                                                                'Will calculate value of arc tangent of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.atan(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of arc tangent of 0.78 radians whatever is default rotation unit')),

                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bmath\.(?:a?cosh|a?sinh|a?tanh)\b",
                                                                    'Functions/Math/Hyperbolic',
                                                                    [('math.cosh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *hyperbolic cosine* for a given number]',
                                                                                # description
                                                                                'Calculate hyperbolic cosine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.cosh(45)`**\n\n'
                                                                                'Will calculate value of hyperbolic cosine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.cosh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of hyperbolic cosine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.sinh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *hyperbolic sine* for a given number]',
                                                                                # description
                                                                                'Calculate hyperbolic sine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.sinh(45)`**\n\n'
                                                                                'Will calculate value of hyperbolic  sine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.sinh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of hyperbolic sine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.tanh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *hyperbolic tangent* for a given number]',
                                                                                # description
                                                                                'Calculate hyperbolic tangent for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.tanh(45)`**\n\n'
                                                                                'Will calculate value of hyperbolic tangent of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.tanh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of hyperbolic tangent of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.acosh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *inverse hyperbolic cosine* for a given number]',
                                                                                # description
                                                                                'Calculate inverse hyperbolic cosine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.acosh(45)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic cosine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.acosh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic cosine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.asinh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *inverse hyperbolic sine* for a given number]',
                                                                                # description
                                                                                'Calculate inverse hyperbolic sine for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.asinh(45)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic sine of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.asinh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic sine of 0.78 radians whatever is default rotation unit')),
                                                                    ('math.atanh(\x01<VALUE> [, <UNIT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *inverse hyperbolic tangent* for a given number]',
                                                                                # description
                                                                                'Calculate inverse hyperbolic tangent for given <VALUE>\n'
                                                                                'Returns a decimal value\n'
                                                                                'Given *<VALUE>* is a decimal number expressed:\n'
                                                                                ' - With default rotation unit, if **`<UNIT>`** is omited\n'
                                                                                ' - With given **`<UNIT>`** if provided\n\n'
                                                                                'Given *<UNIT>* define unit to apply for width; if provided can be:\n'
                                                                                ' - **`RADIAN`**: use radians (0 to pi)\n'
                                                                                ' - **`DEGREE`**: use degrees (0 to 360)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`math.atanh(45)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic tangent of 45 degree if default canvas unit is **`DEGREE`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`math.atanh(0.75 RADIAN)`**\n\n'
                                                                                'Will calculate value of inverse hyperbolic tangent of 0.78 radians whatever is default rotation unit')),

                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            # TODO: |format|parseInt|parseFloat|parseColor
            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\bstring\.(?:length)\b",
                                                                    'Functions/String',
                                                                    [('string.length(\x01<TEXT>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *length* for a given string]',
                                                                                # description
                                                                                'Calculate string length (number of characters) for given <TEXT>\n'
                                                                                'Returns an integer value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`string.length("Hello!")`**\n\n'
                                                                                'Will return value **`6`**')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_STRING, r"\bstring\.(?:upper|lower|substring|format)\b",
                                                                    'Functions/String',
                                                                    [('string.upper(\x01<TEXT>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *uppercase* version for a given string]',
                                                                                # description
                                                                                'Change string to uppercase for given <TEXT>\n'
                                                                                'Returns a string value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`string.uppercase("hello!")`**\n\n'
                                                                                'Will return value **`HELLO!`**')),
                                                                    ('string.lower(\x01<TEXT>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *lowercase* version for a given string]',
                                                                                # description
                                                                                'Change string to lowercase for given <TEXT>\n'
                                                                                'Returns a string value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`string.uppercase("HELLO!")`**\n\n'
                                                                                'Will return value **`hello!`**')),
                                                                    ('string.substring(\x01<TEXT>, <INDEX>[, <COUNT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a character from a given string]',
                                                                                # description
                                                                                'Return one character from given <TEXT>, at position <INDEX>\n\n'
                                                                                'Given *<INDEX>* is an integer number:\n'
                                                                                ' - First character index is *`1`*\n'
                                                                                ' - Negative index value returns character from end of string*\n'
                                                                                ' - If given index is not valid, function returns empty string)\n\n'
                                                                                'Given *<COUNT>*, if provided, is a positive integer number and define number of characters to return:\n'
                                                                                ' - If not provided, default value is *`1`*\n'
                                                                                ' - If given index is not valid, function returns all possible characters)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`string.character("HELLO!", 1)`**\n\n'
                                                                                'Will return value **`H`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`string.character("HELLO!", -1)`**\n\n'
                                                                                'Will return value **`!`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`string.character("HELLO!", 1, 5)`**\n\n'
                                                                                'Will return value **`HELLO`**\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`string.character("HELLO!", -3, 2)`**\n\n'
                                                                                'Will return value **`LO`**\n\n'
                                                                                'Following instructions:\n'
                                                                                '**`string.character("HELLO!", 4, 15)`**\n'
                                                                                '**`string.character("HELLO!", -3, 15)`**\n\n'
                                                                                'Will return value **`LLO!`**')),
                                                                    ('string.format(\x01<FORMAT>[, <VALUE>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return formatted string using given format for provided]',
                                                                                # description
                                                                                'Format provided <VALUE> (from 0 to N) in a string using given <FORMAT>\n'
                                                                                'The format specification follows the Python *(format specification mini language)[https://docs.python.org/3/library/string.html#format-specification-mini-language]*\n',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`string.uppercase("Hi {0}, this is an example!", :name)`**\n\n'
                                                                                'Will return (if **`:name`** is defined as `"John"`) value **`Hi John, this is an example!`**')),

                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_COLOR, r"\bcolor\.(?:rgba?|hsla?|hsva?|cmyka?|red|green|blue|hue|saturation|value|lightness|cyan|magenta|yellow|black|opacity)\b",
                                                                    'Functions/Color',
                                                                    [('color.rgb(\x01<R-VALUE>, <G-VALUE>, <B-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Red, Green, Blue]',
                                                                                # description
                                                                                'Calculate a color for given <R-VALUE>, <G-VALUE>, <B-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<R-VALUE>* for Red, *<G-VALUE> for Green, *<B-VALUE>* for Blue can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.rbg(255, 255, 0)`**\n'
                                                                                '**`color.rbg(1.0, 1.0, 0.0)`**\n\n'
                                                                                'Will both return a yellow color, with 100% opacity')),
                                                                    ('color.rgba(\x01<R-VALUE>, <G-VALUE>, <B-VALUE>, <O-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Red, Green, Blue, Opacity]',
                                                                                # description
                                                                                'Calculate a color for given <R-VALUE>, <G-VALUE>, <B-VALUE>, <O-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<R-VALUE>* for Red, *<G-VALUE>* for Green, *<B-VALUE>* for Blue, *<O-VALUE>* for Opacity can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.rbg(255, 255, 0, 128)`**\n'
                                                                                '**`color.rbg(1.0, 1.0, 0.0, 0.5)`**\n\n'
                                                                                'Will both return a yellow color, with 50% opacity')),
                                                                    ('color.hsl(\x01<H-VALUE>, <S-VALUE>, <L-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Hue, Saturation, Lightness]',
                                                                                # description
                                                                                'Calculate a color for given <H-VALUE>, <S-VALUE>, <L-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<H-VALUE>* for Hue is an integer value from 0 to 359 or a decimal value from 0.0 to 1.0\n\n'
                                                                                'Given *<S-VALUE>* for Saturation, *<L-VALUE>* for Lightness can be can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.hsl(120, 255, 64)`**\n'
                                                                                '**`color.hsl(120, 1.0, 0.25)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,128,0), with 100% opacity')),
                                                                    ('color.hsla(\x01<H-VALUE>, <S-VALUE>, <L-VALUE>, <O-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Hue, Saturation, Lightness, Opacity]',
                                                                                # description
                                                                                'Calculate a color for given <H-VALUE>, <S-VALUE>, <L-VALUE>, <O-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<H-VALUE>* for Hue is an integer value from 0 to 359 or a decimal value from 0.0 to 1.0\n\n'
                                                                                'Given *<S-VALUE>* for Saturation, *<L-VALUE>* for Lightness, *<O-VALUE>* for Opacity can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.hsla(120, 255, 64, 127)`**\n'
                                                                                '**`color.hsla(120, 1.0, 0.25, 0.5)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,128,0), with 50% opacity')),
                                                                    ('color.hsv(\x01<H-VALUE>, <S-VALUE>, <V-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Hue, Saturation, Value]',
                                                                                # description
                                                                                'Calculate a color for given <H-VALUE>, <S-VALUE>, <V-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<H-VALUE>* for Hue is an integer value from 0 to 359 or a decimal value from 0.0 to 1.0\n\n'
                                                                                'Given *<S-VALUE>* for Saturation, *<V-VALUE>* for Value can be can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.hsv(120, 255, 64)`**\n'
                                                                                '**`color.hsv(120, 1.0, 0.25)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,64,0), with 100% opacity')),
                                                                    ('color.hsva(\x01<H-VALUE>, <S-VALUE>, <L-VALUE>, <O-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Hue, Saturation, Value, Opacity]',
                                                                                # description
                                                                                'Calculate a color for given <H-VALUE>, <S-VALUE>, <V-VALUE>, <O-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<H-VALUE>* for Hue is an integer value from 0 to 359 or a decimal value from 0.0 to 1.0\n\n'
                                                                                'Given *<S-VALUE>* for Saturation, *<V-VALUE>* for Value, *<O-VALUE>* for Opacity can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.hsva(120, 255, 64, 127)`**\n'
                                                                                '**`color.hsva(120, 1.0, 0.25, 0.5)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,64,0), with 50% opacity')),
                                                                    ('color.cmyk(\x01<C-VALUE>, <M-VALUE>, <Y-VALUE>, <K-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Cyan, Magenta, Yellow, Black]',
                                                                                # description
                                                                                'Calculate a color for given <C-VALUE>, <M-VALUE>, <Y-VALUE>, <K-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<C-VALUE>* for Cyan, *<M-VALUE>* for Magenta, *<Y-VALUE>* for Yellow, *<K-VALUE>* for Black can be can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.cmyk(255, 0, 255, 191)`**\n'
                                                                                '**`color.hsv(1.0, 0.0, 1.0, 0.75)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,64,0), with 100% opacity')),
                                                                    ('color.cmyka(\x01<C-VALUE>, <M-VALUE>, <Y-VALUE>, <K-VALUE>, <O-VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *color* from given Hue, Saturation, Value, Opacity]',
                                                                                # description
                                                                                'Calculate a color for given <C-VALUE>, <M-VALUE>, <Y-VALUE>, <K-VALUE>, <O-VALUE>\n'
                                                                                'Returns a color value\n\n'
                                                                                'Given *<C-VALUE>* for Cyan, *<M-VALUE>* for Magenta, *<Y-VALUE>* for Yellow, *<K-VALUE>* for Black, *<O-VALUE>* for Opacity can be can be:\n'
                                                                                ' - **`int`**: an integer value from 0 to 255\n'
                                                                                ' - **`dec`**: a decimal value from 0.0 to 1.0',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.cmyk(255, 0, 255, 191, 127)`**\n'
                                                                                '**`color.hsv(1.0, 0.0, 1.0, 0.75, 0.5)`**\n\n'
                                                                                'Will both return a green color equivalent to rgb(0,64,0), with 50% opacity')),
                                                                    ('color.red(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *red* value for given color]',
                                                                                # description
                                                                                'Return red value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.red(#55364347)`**\n\n'
                                                                                'Will return value 54')),
                                                                    ('color.green(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *green* value for given color]',
                                                                                # description
                                                                                'Return green value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.green(#55364347)`**\n\n'
                                                                                'Will return value 67')),
                                                                    ('color.blue(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *blue* value for given color]',
                                                                                # description
                                                                                'Return blue value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.blue(#55364347)`**\n\n'
                                                                                'Will return value 71')),
                                                                    ('color.cyan(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *cyan* value for given color]',
                                                                                # description
                                                                                'Return cyan value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.cyan(#55364347)`**\n\n'
                                                                                'Will return value 61')),
                                                                    ('color.magenta(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *magenta* value for given color]',
                                                                                # description
                                                                                'Return magenta value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.magenta(#55364347)`**\n\n'
                                                                                'Will return value 14')),
                                                                    ('color.black(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *black* value for given color]',
                                                                                # description
                                                                                'Return black value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.black(#55364347)`**\n\n'
                                                                                'Will return value 184')),
                                                                    ('color.yellow(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *yellow* value for given color]',
                                                                                # description
                                                                                'Return yellow value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.yellow(#55364347)`**\n\n'
                                                                                'Will return value 0')),
                                                                    ('color.hue(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *hue* value for given color]',
                                                                                # description
                                                                                'Return hue value (0-360) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.hue(#55364347)`**\n\n'
                                                                                'Will return value 194')),
                                                                    ('color.saturation(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *saturation* value for given color]',
                                                                                # description
                                                                                'Return saturation value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.saturation(#55364347)`**\n\n'
                                                                                'Will return value 61')),
                                                                    ('color.value(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *value* value for given color]',
                                                                                # description
                                                                                'Return value value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.value(#55364347)`**\n\n'
                                                                                'Will return value 71')),
                                                                    ('color.lightness(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *lightness* value for given color]',
                                                                                # description
                                                                                'Return lightness value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.lightness(#55364347)`**\n\n'
                                                                                'Will return value 62')),
                                                                    ('color.opacity(\x01<COLOR>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *opacity* value for given color]',
                                                                                # description
                                                                                'Return opacity value (0-255) from given color <COLOR> \n\n',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`color.opacity(#55364347)`**\n\n'
                                                                                'Will return value 85')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),


            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_NUMBER, r"\blist\.(?:length)\b",
                                                                    'Functions/List',
                                                                    [('list.length(\x01<LIST>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return *length* for a given list]',
                                                                                # description
                                                                                'Calculate list length (number of items) for given <LIST>\n'
                                                                                'Returns an integer value',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.length([2,4,6])`**\n\n'
                                                                                'Will return value **`3`**')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_STRING, r"\blist\.(?:join)\b",
                                                                    'Functions/List',
                                                                    [('list.join(\x01<LIST>[, <SEPARATOR>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a string made of *joined* item from a given list]',
                                                                                # description
                                                                                'Join items from given <LIST> into a string, using given <SEPARATOR>\n'
                                                                                'Returns a string value\n\n'
                                                                                'Given *<LIST>* is a list\n\n'
                                                                                'Given *<SEPARATOR>*, if provided, is a string (default value if not provided is a comma `,`)',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.join(["a", "b", "c"], ";")n\n'
                                                                                'Will return value **`a;b;c`**')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),




            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_LIST, r"\bstring\.(?:split)\b",
                                                                    'Functions/String',
                                                                    [('string.split(\x01<TEXT> [, <SEPARATOR>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list from a *splitted* given string]',
                                                                                # description
                                                                                'Split given <TEXT> into list, using given <SEPARATOR>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<TEXT>* is a string\n\n'
                                                                                'Given *<SEPARATOR>* if provided, is a text (default separator is comma `,`)',
                                                                                # example
                                                                                'Following instructions:\n'
                                                                                '**`string.split("aa,bb,cc")`**\n'
                                                                                '**`string.splir("aa;bb;cc", ";")`**\n\n'
                                                                                'Will both return a list `["aa", "bb", "cc"]`')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),


            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_LIST, r"\blist\.(?:rotate|sort|unique|shuffle|revert)\b",
                                                                    'Functions/List',
                                                                    [('list.rotate(\x01<LIST>[, <VALUE>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list for which items have been *rotated*]',
                                                                                # description
                                                                                'Rotate items from given <LIST> of given count <VALUE>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<LIST>* is a list\n\n'
                                                                                'Given *<VALUE>* is an integer:\n'
                                                                                '- Positive value will rotate to right\n'
                                                                                '- Negative value will rotate to left',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.rotate([1,2,3,4,5], 2)`**\n\n'
                                                                                'Will return list `[4,5,1,2,3]`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`list.rotate([1,2,3,4,5], -1)`**\n\n'
                                                                                'Will return list `[2,3,4,5,1]`')),
                                                                    ('list.sort(\x01<LIST>[, <ASCENDING>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list for which items have been *sorted*]',
                                                                                # description
                                                                                'Sort items from given <LIST>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<LIST>* is a list\n\n'
                                                                                'Given *<ASCENDING>*, if provided, is a boolean:\n'
                                                                                '- **`ON`**: sort ascending\n'
                                                                                '- **`OFF`**: sort descending',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.sort([1,3,5,4,2])`**\n\n'
                                                                                'Will return list `[1,2,3,4,5]`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`list.sort([1,3,5,4,2], OFF)`**\n\n'
                                                                                'Will return list `[5,4,3,2,1]`')),
                                                                    ('list.unique(\x01<LIST>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list for which duplicate items have been *removed*]',
                                                                                # description
                                                                                'Remove duplicates items from given <LIST>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<LIST>* is a list',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.sort([1,2,2,3,4])`**\n\n'
                                                                                'Will return list `[1,2,3,4]`')),
                                                                    ('list.shuffle(\x01<LIST>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list for which items have been *shuffled*]',
                                                                                # description
                                                                                'Shuffle items from given <LIST>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<LIST>* is a list',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.shuffle([1,2,3,4])`**\n\n'
                                                                                'Will return *(for example)* list `[4,1,3,2]`')),
                                                                    ('list.revert(\x01<LIST>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return a list for which items order have been *reverted*]',
                                                                                # description
                                                                                'Revert items order from given <LIST>\n'
                                                                                'Returns a list value\n\n'
                                                                                'Given *<LIST>* is a list',
                                                                                # example
                                                                                'Following instruction:\n'
                                                                                '**`list.revert([1,2,3,4])`**\n\n'
                                                                                'Will return list `[4,3,2,1]`')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_VARIANT, r"\blist\.(?:index)\b",
                                                                    'Functions/List',
                                                                    [('list.index(\x01<LIST>, <INDEX>[, <DEFAULT>]\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Return value for given index from a given list]',
                                                                                # description
                                                                                'Return item designed by <INDEX> from given <LIST>\n\n'
                                                                                'Given *<LIST>* is a list\n\n'
                                                                                'Given *<INDEX>*, if provided, is an integer:\n'
                                                                                ' - A positive value will return value from start (first index in list=1)\n'
                                                                                ' - A negative value will return value from end\n'
                                                                                ' - Any invalid index value will return <DEFAULT>\n\n'
                                                                                'Given optional *<DEFAULT>* can be of any type, and is returned if an invalid index been given; if not provided, value is `0`',
                                                                                # example
                                                                                'Assumining variable `:myList` is a list `[1,2,3,4,5]`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`list.index(:myList, 1)`**\n'
                                                                                'Will return `1`\n\n'
                                                                                'Following instruction:\n'
                                                                                '**`list.index(:myList, -2)`**\n'
                                                                                'Will return `4`\n\n'
                                                                                '**`list.index(:myList, 25, 0)`**\n'
                                                                                'Will return `0`')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_BOOLEAN, r"\bboolean\.(?:isString|isNumber|isInteger|isDecimal|isBoolean|isColor|isList)\b",
                                                                    'Functions/Boolean',
                                                                    [('boolean.isString(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *string*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a string\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isNumber(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *number*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a number (integer or decimal)\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isInteger(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is an *integer*]',
                                                                                # description
                                                                                'Check if given <VALUE> is an integer\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isDecimal(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *decimal*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a decimal\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isBoolean(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *boolean*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a boolean\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isColor(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *color*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a color\n'
                                                                                'Returns a boolean value')),
                                                                    ('boolean.isList(\x01<VALUE>\x01)',
                                                                            TokenizerRule.formatDescription(
                                                                                'Function [Check if value is a *list*]',
                                                                                # description
                                                                                'Check if given <VALUE> is a list\n'
                                                                                'Returns a boolean value')),
                                                                    ],
                                                                    'f',
                                                                    onInitValue=self.__initTokenLower),


            TokenizerRule(BSLanguageDef.ITokenType.FUNCTION_UNCOMPLETE, r"^\x20*\b"
                                                                       r"(?:math|string|color|list|boolean)\."
                                                                       r"\b"
                                                                       ),


            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_NONE, r"\bNONE\b",
                                                                    'Constants/Layer/Color label|Constants/Pen/Style|Constants/Canvas/Grid/Style|Constants/Canvas/Origin/Style',
                                                                    [('NONE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [None value]',
                                                                                # description
                                                                                'Define an undefined value'))],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),

            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_ONOFF, r"\b(?:ON|OFF)\b",
                                                                    'Constants/Switch',
                                                                    [('ON',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Boolean/Switch value]',
                                                                                # description
                                                                                'Define a True/Active state')),
                                                                    ('OFF',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Boolean/Switch value]',
                                                                                # description
                                                                                'Define a False/Inactive state'))],
                                                                    'c',
                                                                    onInitValue=self.__initTokenBoolean
                                                                    ),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_UNITS_M, r"\b(?:PX|PCT|MM|INCH)\b",
                                                                    'Constants/Units/Measure',
                                                                    [('PX',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Unit: pixels]',
                                                                                # description
                                                                                'Unit in pixels')),
                                                                    ('PCT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Unit: percentage]',
                                                                                # description
                                                                                'Unit in percentage')),
                                                                    ('MM',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Unit: millimeters]',
                                                                                # description
                                                                                'Unit in millimeters')),
                                                                    ('INCH',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Unit: inch]',
                                                                                # description
                                                                                'Unit in inches')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_UNITS_M_RPCT, r"\b(?:RPCT)\b",
                                                                    'Constants/Units/Measure',
                                                                    [('RPCT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Unit: relative percentage]',
                                                                                # description
                                                                                'Unit in relative percentage\n'
                                                                                'Relative percentage can only be used for some actions')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_UNITS_R, r"\b(?:RADIAN|DEGREE)\b",
                                                                    'Constants/Units/Angle',
                                                                    [('RADIAN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Angle: radians]',
                                                                                # description
                                                                                'Angle in radians')),
                                                                    ('DEGREE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Angle: degree]',
                                                                                # description
                                                                                'Unit in degrees')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),

            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_PENSTYLE, r"\b(?:SOLID|DASHDOT|DASH|DOT)\b",
                                                                    'Constants/Pen/Style|Constants/Canvas/Grid/Style|Constants/Canvas/Origin/Style',
                                                                    [('SOLID',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Style: solid stroke]',
                                                                                # description
                                                                                'Solid stroke')),
                                                                    ('DASH',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Style: dash stroke]',
                                                                                # description
                                                                                'Dash stroke')),
                                                                    ('DOT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Style: dot stroke]',
                                                                                # description
                                                                                'Dot stroke')),
                                                                    ('DASHDOT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Style: dash dot stroke]',
                                                                                # description
                                                                                'Dash-Dot stroke')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_PENCAP, r"\b(?:SQUARE|FLAT|ROUNDCAP)\b",
                                                                    'Constants/Pen/Cap',
                                                                    [('SQUARE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Cap: square stroke]',
                                                                                # description
                                                                                'Square pen stroke cap')),
                                                                    ('FLAT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Cap: flat stroke]',
                                                                                # description
                                                                                'Flat pen stroke cap')),
                                                                    ('ROUNDCAP',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Cap: round stroke]',
                                                                                # description
                                                                                'Round pen stroke cap')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_PENJOIN, r"\b(?:BEVEL|MITTER|ROUNDJOIN)\b",
                                                                    'Constants/Pen/Join',
                                                                    [('BEVEL',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Join: bevel stroke]',
                                                                                # description
                                                                                'Square pen stroke join')),
                                                                    ('MITTER',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Join: mitter stroke]',
                                                                                # description
                                                                                'Flat pen stroke join')),
                                                                    ('ROUNDJOIN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Join: round stroke]',
                                                                                # description
                                                                                'Round pen stroke join')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_FILLRULE, r"\b(?:EVEN|WINDING)\b",
                                                                    'Constants/Fill',
                                                                    [('EVEN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Rule: even fill]',
                                                                                # description
                                                                                'Fill rule even')),
                                                                    ('WINDING',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Rule: winding fill]',
                                                                                # description
                                                                                'Fill rule winding')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_POSHALIGN, r"\b(?:LEFT|CENTER|RIGHT)\b",
                                                                    'Constants/Text/Alignment/Horizontal',
                                                                    [('LEFT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Horizontal alignment: left align]',
                                                                                # description
                                                                                'Left horizontal text alignment')),
                                                                    ('CENTER',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Horizontal alignment: center align]',
                                                                                # description
                                                                                'Center horizontal text alignment')),
                                                                    ('RIGHT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Horizontal alignment: right align]',
                                                                                # description
                                                                                'Right horizontal text alignment')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_POSVALIGN, r"\b(?:TOP|MIDDLE|BOTTOM)\b",
                                                                    'Constants/Text/Alignment/Vertical',
                                                                    [('TOP',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Vertical alignment: top align]',
                                                                                # description
                                                                                'Top vertical text alignment')),
                                                                    ('MIDDLE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Vertical alignment: center align]',
                                                                                # description
                                                                                'Middle vertical text alignment')),
                                                                    ('BOTTOM',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Vertical alignment: bottom align]',
                                                                                # description
                                                                                'Bottom vertical text alignment')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_BLENDINGMODE, r"\b(?:NORMAL|SOURCE_OVER|DESTINATION_OVER|DESTINATION_CLEAR|SOURCE_IN|SOURCE_OUT|DESTINATION_IN|DESTINATION_OUT|SOURCE_ATOP|DESTINATION_ATOP|EXCLUSIVE_OR|PLUS|MULTIPLY|SCREEN|OVERLAY|DARKEN|LIGHTEN|COLORDODGE|COLORBURN|HARD_LIGHT|SOFT_LIGHT|DIFFERENCE|EXCLUSION)\b",
                                                                    'Constants/Draw/Blending modes/Pixels',
                                                                    [('NORMAL',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: normal]',
                                                                                # description
                                                                                'This is the default mode and it\'s the same than *`SOURCE_OVER`*\n'
                                                                                'The alpha of the source is used to blend the pixel on top of the destination')),
                                                                    ('SOURCE_OVER',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: source over]',
                                                                                # description
                                                                                'The alpha of the source is used to blend the pixel on top of the destination')),
                                                                    ('DESTINATION_OVER',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: destination over]',
                                                                                # description
                                                                                'The alpha of the destination is used to blend it on top of the source pixels\n'
                                                                                'This mode is the inverse of *`SOURCE_OVER`*')),
                                                                    ('DESTINATION_CLEAR',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: clear]',
                                                                                # description
                                                                                'The pixels in the destination are cleared (set to fully transparent) independent of the source')),
                                                                    ('SOURCE_IN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: source in]',
                                                                                # description
                                                                                'The output is the source, where the alpha is reduced by that of the destination')),
                                                                    ('SOURCE_OUT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: source out]',
                                                                                # description
                                                                                'The output is the source, where the alpha is reduced by the inverse of destination')),
                                                                    ('DESTINATION_IN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: destination in]',
                                                                                # description
                                                                                'The output is the destination, where the alpha is reduced by that of the source\n'
                                                                                'This mode is the inverse of *`SOURCE_IN`*')),
                                                                    ('DESTINATION_OUT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: destination out]',
                                                                                # description
                                                                                'The output is the destination, where the alpha is reduced by the inverse of the source\n'
                                                                                'This mode is the inverse of *`SOURCE_OUT`*')),
                                                                    ('SOURCE_ATOP',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: source a top]',
                                                                                # description
                                                                                'The source pixel is blended on top of the destination, with the alpha of the source pixel reduced by the alpha of the destination pixel')),
                                                                    ('DESTINATION_ATOP',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: destination a top]',
                                                                                # description
                                                                                'The destination pixel is blended on top of the source, with the alpha of the destination pixel is reduced by the alpha of the destination pixel\n'
                                                                                'This mode is the inverse of *`SOURCE_ATOP`*')),
                                                                    ('EXCLUSIVE_OR',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: exclusive or]',
                                                                                # description
                                                                                'The source, whose alpha is reduced with the inverse of the destination alpha, is merged with the destination, whose alpha is reduced by the inverse of the source alpha\n'
                                                                                'The *`EXCLUSIVE_OR`* is not the same as the *`BITWISE_XOR`*')),
                                                                    ('PLUS',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: plus]',
                                                                                # description
                                                                                'Both the alpha and color of the source and destination pixels are added together')),
                                                                    ('MULTIPLY',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: multiply]',
                                                                                # description
                                                                                'The output is the source color multiplied by the destination\n'
                                                                                'Multiplying a color with white leaves the color unchanged, while multiplying a color with black produces black')),
                                                                    ('SCREEN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: screen]',
                                                                                # description
                                                                                'The source and destination colors are inverted and then multiplied\n'
                                                                                'Screening a color with white produces white, whereas screening a color with black leaves the color unchanged')),
                                                                    ('OVERLAY',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: overlay]',
                                                                                # description
                                                                                'Multiplies or screens the colors depending on the destination color\n'
                                                                                'The destination color is mixed with the source color to reflect the lightness or darkness of the destination')),
                                                                    ('DARKEN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: darken]',
                                                                                # description
                                                                                'The darker of the source and destination colors is selected')),
                                                                    ('LIGHTEN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: lighten]',
                                                                                # description
                                                                                'The lighter of the source and destination colors is selected')),
                                                                    ('COLORDODGE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: color dodge]',
                                                                                # description
                                                                                'The destination color is brightened to reflect the source color\n'
                                                                                'A black source color leaves the destination color unchanged')),
                                                                    ('COLORBURN',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: color burn]',
                                                                                # description
                                                                                'The destination color is darkened to reflect the source color\n'
                                                                                'A white source color leaves the destination color unchanged')),
                                                                    ('HARD_LIGHT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: hard light]',
                                                                                # description
                                                                                'Multiplies or screens the colors depending on the source color\n'
                                                                                'A light source color will lighten the destination color, whereas a dark source color will darken the destination color')),
                                                                    ('SOFT_LIGHT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: soft light]',
                                                                                # description
                                                                                'Darkens or lightens the colors depending on the source color\n'
                                                                                'Similar to *HARD_LIGHT*')),
                                                                    ('DIFFERENCE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: difference]',
                                                                                # description
                                                                                'Subtracts the darker of the colors from the lighter\n'
                                                                                'Painting with white inverts the destination color, whereas painting with black leaves the destination color unchanged')),
                                                                    ('EXCLUSION',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: normal]',
                                                                                # description
                                                                                'Similar to CompositionMode_Difference, but with a lower contrast\n'
                                                                                'Painting with white inverts the destination color, whereas painting with black leaves the destination color unchanged')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),
            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_BLENDINGMODE, r"\b(?:BITWISE_S_OR_D|BITWISE_S_AND_D|BITWISE_S_XOR_D|BITWISE_S_NOR_D|BITWISE_S_NAND_D|BITWISE_NS_XOR_D|BITWISE_S_NOT|BITWISE_NS_AND_D|BITWISE_S_AND_ND|BITWISE_NS_OR_D|BITWISE_CLEAR|BITWISE_SET|BITWISE_NOT_D|BITWISE_S_OR_ND)\b",
                                                                    'Constants/Draw/Blending modes/Bits level',
                                                                    [('BITWISE_S_OR_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise OR]',
                                                                                # description
                                                                                'Does a bitwise OR operation on the Source and Destination pixels')),
                                                                    ('BITWISE_S_AND_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise AND]',
                                                                                # description
                                                                                'Does a bitwise AND operation on the Source and Destination pixels')),
                                                                    ('BITWISE_S_XOR_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise XOR]',
                                                                                # description
                                                                                'Does a bitwise XOR operation on the Source and Destination pixels')),
                                                                    ('BITWISE_S_NOR_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NOR]',
                                                                                # description
                                                                                'Does a bitwise NOR operation on the Source and Destination pixels')),
                                                                    ('BITWISE_S_NAND_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NAND]',
                                                                                # description
                                                                                'Does a bitwise NAND operation on the Source and Destination pixels')),
                                                                    ('BITWISE_NS_XOR_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NOT XOR]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source pixels are inverted and then applied a XOR operation with the Destination')),
                                                                    ('BITWISE_S_NOT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NOT source]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source pixels are inverted')),
                                                                    ('BITWISE_NS_AND_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NOT AND]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source is inverted and then AND operation with the Destination ')),
                                                                    ('BITWISE_S_AND_ND',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise AND NOT]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source is AND with the inverted Destination pixels')),
                                                                    ('BITWISE_NS_OR_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise NOT OR]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source is inverted and then OR operation with the Destination')),
                                                                    ('BITWISE_CLEAR',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise CLEAR]',
                                                                                # description
                                                                                'The pixels in the destination are cleared (set to 0) independent of the source')),
                                                                    ('BITWISE_SET',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise SET]',
                                                                                # description
                                                                                'The pixels in the destination are set (set to 1) independent of the source')),
                                                                    ('BITWISE_NOT_D',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: NOT destination]',
                                                                                # description
                                                                                'Does a bitwise operation where the Destination pixels are inverted')),
                                                                    ('BITWISE_S_OR_ND',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Blending mode: bitwise OR NOT]',
                                                                                # description
                                                                                'Does a bitwise operation where the Source is OR operation with the inverted Destination pixels')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),

            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_SELECTIONMODE, r"\b(?:ADD|SUBSTRACT|REPLACE)\b",
                                                                    'Constants/Selection/Mode',
                                                                    [('ADD',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Selection mode: add]',
                                                                                # description
                                                                                'Add selection to current selection')),
                                                                    ('SUBSTRACT',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Selection mode: substract]',
                                                                                # description
                                                                                'Substract selection to current selection')),
                                                                    ('REPLACE',
                                                                            TokenizerRule.formatDescription(
                                                                                'Constant [Selection mode: replace]',
                                                                                # description
                                                                                'Replace current selection')),
                                                                    ],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),

            TokenizerRule(BSLanguageDef.ITokenType.CONSTANT_COLORLABEL, r"\b(?:BLUE|GREEN|YELLOW|ORANGE|BROWN|RED|PURPLE|GREY)\b",
                                                                    'Constants/Layer/Color label',['BLUE','GREEN','YELLOW','ORANGE','BROWN','RED','PURPLE','GREY'],
                                                                    'c',
                                                                    onInitValue=self.__initTokenUpper),


            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bmath\.(?:pi|e|phi)\b",
                                                                    'Variables/Math',
                                                                    [(':math.pi',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Mathematical constant: Pi]',
                                                                                # description
                                                                                'The mathematical constant *π*=3.141592…\n'
                                                                                'See (Pi)[https://en.wikipedia.org/wiki/Pi]')),
                                                                    (':math.e',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Mathematical constant: e]',
                                                                                # description
                                                                                'The mathematical constant *e*=2.718281…\n'
                                                                                'See (Euler\'s number)[https://en.wikipedia.org/wiki/E_(mathematical_constant)]')),
                                                                    (':math.phi',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Mathematical constant: Phi]',
                                                                                # description
                                                                                'The mathematical constant *phi*=1.618033…\n'
                                                                                'See (Euler\'s number)[https://en.wikipedia.org/wiki/E_(mathematical_constant)]')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bposition\.(?:x|y)\b",
                                                                    'Variables/Position',
                                                                    [(':position.x',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen position: absissa]',
                                                                                # description
                                                                                'Current position absissa, from origin, in current canvas unit\n'
                                                                                'Returned as decimal value')),
                                                                    (':position.y',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen position: ordinate]',
                                                                                # description
                                                                                'Current position ordinate, from origin, in current canvas unit\n'
                                                                                'Returned as decimal value')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bangle\b",
                                                                    'Variables/Rotation',
                                                                    [(':angle',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen direction/rotation: angle]',
                                                                                # description
                                                                                'Current rotation, in current rotation unit\n'
                                                                                'Returned as decimal value')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bunit\.(?:rotation|canvas)\b",
                                                                    'Variables/Units',
                                                                    [(':unit.rotation',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current used rotation unit]',
                                                                                # description
                                                                                'Current rotation unit\n'
                                                                                'Returned as string value')),
                                                                     (':unit.canvas',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current used coordinates & measures unit]',
                                                                                # description
                                                                                'Current canvas unit\n'
                                                                                'Returned as string value')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            # todo: add |brush
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bpen\.(?:color|size|style|cap|join|status)\b",
                                                                    'Variables/Pen',
                                                                    [(':pen.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen color]',
                                                                                # description
                                                                                'Current pen color\n'
                                                                                'Returned as color value')),
                                                                     (':pen.size',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen size]',
                                                                                # description
                                                                                'Current pen size in current canvas unit\n'
                                                                                'Returned as decimal value')),
                                                                     (':pen.style',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen style]',
                                                                                # description
                                                                                'Current pen style\n'
                                                                                'Returned as string value')),
                                                                     (':pen.cap',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen cap]',
                                                                                # description
                                                                                'Current pen cap\n'
                                                                                'Returned as string value')),
                                                                     (':pen.join',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen join]',
                                                                                # description
                                                                                'Current pen join\n'
                                                                                'Returned as string value')),
                                                                     (':pen.status',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current pen status]',
                                                                                # description
                                                                                'Current pen status\n'
                                                                                'Returned as string value (UP=OFF, DOWN=ON)')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            # todo: add |brush
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bfill\.(?:color|rule|status)\b",
                                                                    'Variables/Fill',
                                                                    [(':fill.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current fill color]',
                                                                                # description
                                                                                'Current fill color\n'
                                                                                'Returned as color value')),
                                                                     (':fill.rule',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current fill rule]',
                                                                                # description
                                                                                'Current fill rule\n'
                                                                                'Returned as string value')),
                                                                     (':fill.status',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current fill status]',
                                                                                # description
                                                                                'Current fill status\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bdraw\.(?:antialiasing|blendingmode|shape\.status)\b",
                                                                    'Variables/Draw',
                                                                    [(':draw.antialiasing',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current antialiasing status]',
                                                                                # description
                                                                                'Current antialiasing status applied when drawing\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                     (':draw.blendingMode',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current blending mode]',
                                                                                # description
                                                                                'Current blending mode applied when drawing\n'
                                                                                'Returned as string value')),
                                                                     (':draw.shape.status',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current shape mode status]',
                                                                                # description
                                                                                'Current shape mode active or not\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\btext\.(?:font|size|bold|italic|outline|letterspacing\.(?:spacing|unit)|stretch|color|alignment\.(?:horizontal|vertical))\b",
                                                                    'Variables/Text',
                                                                    [(':text.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text color]',
                                                                                # description
                                                                                'Current text color\n'
                                                                                'Returned as color value')),
                                                                     (':text.font',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text font name]',
                                                                                # description
                                                                                'Current font name\n'
                                                                                'Returned as string value')),
                                                                     (':text.size',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text size]',
                                                                                # description
                                                                                'Current font size in current canvas unit\n'
                                                                                'Returned as decimal value')),
                                                                     (':text.bold',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text style: bold status]',
                                                                                # description
                                                                                'Current bold status\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                     (':text.italic',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text style: italic status]',
                                                                                # description
                                                                                'Current italic status\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                     (':text.outline',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text style: outline status]',
                                                                                # description
                                                                                'Current outline status\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                     (':text.letterSpacing.spacing',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text letter spacing value]',
                                                                                # description
                                                                                'Current letter spacing value\n'
                                                                                'Returned as number value, using `:text.letterSpacing.unit` unit')),
                                                                     (':text.letterSpacing.unit',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text letter spacing value]',
                                                                                # description
                                                                                'Current letter spacing value\n'
                                                                                'Returned as string')),
                                                                     (':text.stretch',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text stretch value]',
                                                                                # description
                                                                                'Current stretch value\n'
                                                                                'Returned as an integer value (100=no strech)')),
                                                                     (':text.alignment.horizontal',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text horizontal alignment]',
                                                                                # description
                                                                                'Current horizontal alignment\n'
                                                                                'Returned as string value')),
                                                                     (':text.alignment.vertical',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current text vertical alignment]',
                                                                                # description
                                                                                'Current vertical alignment\n'
                                                                                'Returned as string value')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.grid\.(?:visibility|color|bgColor|size\.main|size\.width|style|opacity)\b",
                                                                    'Variables/Canvas/Grid',
                                                                    [(':canvas.grid.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current canvas grid color]',
                                                                                # description
                                                                                'Current canvas grid color\n'
                                                                                'Returned as color value')),
                                                                     (':canvas.grid.bgColor',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current canvas grid background color]',
                                                                                # description
                                                                                'Current canvas grid background color\n'
                                                                                'Returned as color value')),
                                                                     (':canvas.grid.visibility',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas grid visibility]',
                                                                                 # description
                                                                                 'Current canvas grid visibility\n'
                                                                                 'Returned as boolean value')),
                                                                     (':canvas.grid.size.main',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas main grid frequency]',
                                                                                 # description
                                                                                 'Current canvas main grid frequency\n'
                                                                                 'Returned in current unit')),
                                                                     (':canvas.grid.size.width',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas grid size]',
                                                                                 # description
                                                                                 'Current canvas grid size\n'
                                                                                 'Returned in current unit')),
                                                                     (':canvas.grid.style.main',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas grid style (main grid)]',
                                                                                 # description
                                                                                 'Current canvas grid style (main grid)')),
                                                                     (':canvas.grid.style.secondary',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas grid style (secondary grid)]',
                                                                                 # description
                                                                                 'Current canvas grid style (secondary grid)')),
                                                                     (':canvas.grid.opacity',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas grid opacity]',
                                                                                 # description
                                                                                 'Current canvas grid opacity\n'
                                                                                 'Returned as a decimal value between 0.0 and 1.0')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.origin\.(?:visibility|color|size|style|opacity|position\.(?:absissa|ordinate))\b",
                                                                    'Variables/Canvas/Origin',
                                                                    [(':canvas.origin.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current canvas origin color]',
                                                                                # description
                                                                                'Current canvas origin color\n'
                                                                                'Returned as color value')),
                                                                     (':canvas.origin.visibility',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin visibility]',
                                                                                 # description
                                                                                 'Current canvas origin visibility\n'
                                                                                 'Returned as boolean value')),
                                                                     (':canvas.origin.size',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin size]',
                                                                                 # description
                                                                                 'Current origin size\n'
                                                                                 'Returned in current unit')),
                                                                     (':canvas.origin.style',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin style]',
                                                                                 # description
                                                                                 'Current canvas origin style')),
                                                                     (':canvas.origin.opacity',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin opacity]',
                                                                                 # description
                                                                                 'Current canvas origin opacity\n'
                                                                                 'Returned as a decimal value between 0.0 and 1.0')),
                                                                     (':canvas.origin.position.absissa',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin absissa]',
                                                                                 # description
                                                                                 'Current canvas origin absissa\n'
                                                                                 'Returned as a string')),
                                                                     (':canvas.origin.position.ordinate',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas origin ordinate]',
                                                                                 # description
                                                                                 'Current canvas origin ordinate\n'
                                                                                 'Returned as a string')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.position\.(?:visibility|color|size|opacity|fulfill)\b",
                                                                    'Variables/Canvas/Position',
                                                                    [(':canvas.position.color',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current canvas position/direction color]',
                                                                                # description
                                                                                'Current canvas position color\n'
                                                                                'Returned as color value')),
                                                                     (':canvas.position.visibility',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas position/direction visibility]',
                                                                                 # description
                                                                                 'Current canvas position visibility\n'
                                                                                 'Returned as boolean value')),
                                                                     (':canvas.position.size',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas position/direction size]',
                                                                                 # description
                                                                                 'Current position size\n'
                                                                                 'Returned in current unit')),
                                                                     (':canvas.position.opacity',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas position/direction opacity]',
                                                                                 # description
                                                                                 'Current canvas position opacity\n'
                                                                                 'Returned as a decimal value between 0.0 and 1.0')),
                                                                     (':canvas.position.fulfill',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas position/direction fulfill status]',
                                                                                 # description
                                                                                 'Current canvas position fulfill status (is empty or fulfilled)\n'
                                                                                 'Returned as boolean value')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.background\.(?:visibility|opacity|source\.type|source\.value)\b",
                                                                    'Variables/Canvas/Background',
                                                                    [(':canvas.background.visibility',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas background visibility]',
                                                                                 # description
                                                                                 'Current canvas background visibility\n'
                                                                                 'Returned as boolean value')),
                                                                     (':canvas.background.opacity',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas background opacity]',
                                                                                 # description
                                                                                 'Current canvas background opacity\n'
                                                                                 'Returned as a decimal value between 0.0 and 1.0')),
                                                                     (':canvas.background.source.type',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas background source]',
                                                                                 # description
                                                                                 'Current canvas background source is string value for which value can be\n:'
                                                                                 '- **`color`**: a color\n'
                                                                                 '- **`document`**: current document projection\n'
                                                                                 '- **`layer active`**: current active layer\n'
                                                                                 '- **`layer name`**: layer designed by name\n'
                                                                                 '- **`layer id`**: layer designed by Id')),
                                                                     (':canvas.background.source.value',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas background value linked to source]',
                                                                                 # description
                                                                                 'Current canvas background source is a value linked to source type and can be\n:'
                                                                                 '- **`color`**: a color\n'
                                                                                 '- **`document`**: current document file name\n'
                                                                                 '- **`layer active`**: current active layer name\n'
                                                                                 '- **`layer name`**: layer name\n'
                                                                                 '- **`layer id`**: layer Id')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.rulers\.(?:visibility|color|bgColor)\b",
                                                                    'Variables/Canvas/Rulers',
                                                                    [(':canvas.rulers.visibility',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas rulers visibility]',
                                                                                 # description
                                                                                 'Current canvas rulers visibility\n'
                                                                                 'Returned as boolean value')),
                                                                     (':canvas.rulers.color',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas rulers color]',
                                                                                 # description
                                                                                 'Current canvas rulers color\n'
                                                                                 'Returned as color value')),
                                                                     (':canvas.rulers.bgColor',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas rulers background color]',
                                                                                 # description
                                                                                 'Current canvas rulers background color\n'
                                                                                 'Returned as color value'))
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bcanvas\.geometry\.(?:width|height|top|bottom|left|right|resolution)\b",
                                                                    'Variables/Canvas/Geometry',
                                                                    [(':canvas.geometry.width',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry width]',
                                                                                 # description
                                                                                 'Current canvas width\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.height',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry height]',
                                                                                 # description
                                                                                 'Current canvas height\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.left',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry left position]',
                                                                                 # description
                                                                                 'Current canvas left position, relative to origin\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.right',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry right position]',
                                                                                 # description
                                                                                 'Current canvas right position, relative to origin\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.top',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry top position]',
                                                                                 # description
                                                                                 'Current canvas top position, relative to origin\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.bottom',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas geometry bottom position]',
                                                                                 # description
                                                                                 'Current canvas bottom position, relative to origin\n'
                                                                                 'Returned in current unit')),
                                                                    (':canvas.geometry.resolution',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current canvas resolution]',
                                                                                 # description
                                                                                 'Current canvas resolution\n'
                                                                                 'Returned in DPI')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),


            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bscript\.(?:execution\.(?:verbose)|randomize\.(?:seed))\b",
                                                                    'Variables/Script',
                                                                    [(':script.execution.verbose',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Current verbose status]',
                                                                                # description
                                                                                'Current verbose status for script execution\n'
                                                                                'Returned as boolean value (ACTIVE=ON, INACTIVE=OFF)')),
                                                                    (':script.randomize.seed',
                                                                            TokenizerRule.formatDescription(
                                                                                'Reserved variable [Randomize seed]',
                                                                                # description
                                                                                'Seed used to generate randomized number')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\brepeat\.(?:currentIteration|totalIteration|incAngle|currentAngle|isFirstIteration|isLastIteration)\b",
                                                                    'Variables/Flow/Loops/Repeat',
                                                                    [(':repeat.currentIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration number in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Current iteration number in loop\n'
                                                                                 'Returned as integer value, starting from 1')),
                                                                    (':repeat.totalIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Total iteration number in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Total iteration number in loop\n'
                                                                                 'Returned as integer value, starting from 1')),
                                                                    (':repeat.isFirstIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration is first iteration in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Define if current iteration is first iteration in loop\n'
                                                                                 'Returned as boolean value')),
                                                                    (':repeat.isLastIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration is last iteration in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Define if current iteration is last iteration in loop\n'
                                                                                 'Returned as boolean value')),
                                                                    (':repeat.incAngle',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current increment angle in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Define the rotation angle for one iteration\n'
                                                                                 'Returned as decimal value, in current rotation unit')),
                                                                    (':repeat.currentAngle',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current rotation angle in *`repeat`* loop]',
                                                                                 # description
                                                                                 'Define the rotation angle for current iteration\n'
                                                                                 'Returned as decimal value, in current rotation unit')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_RESERVED, r":\bforeach\.(?:currentIteration|totalIteration|incAngle|currentAngle|isFirstIteration|isLastIteration)\b",
                                                                    'Variables/Flow/Loops/For each',
                                                                    [(':foreach.currentIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration number in *`for each`* loop]',
                                                                                 # description
                                                                                 'Current iteration number in loop\n'
                                                                                 'Returned as integer value, starting from 1')),
                                                                    (':foreach.totalIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Total iteration number in *`for each`* loop]',
                                                                                 # description
                                                                                 'Total iteration number in loop\n'
                                                                                 'Returned as integer value, starting from 1')),
                                                                    (':foreach.isFirstIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration is first iteration in *`for each`* loop]',
                                                                                 # description
                                                                                 'Define if current iteration is first iteration in loop\n'
                                                                                 'Returned as boolean value')),
                                                                    (':foreach.isLastIteration',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current iteration is last iteration in *`for each`* loop]',
                                                                                 # description
                                                                                 'Define if current iteration is last iteration in loop\n'
                                                                                 'Returned as boolean value')),
                                                                    (':foreach.incAngle',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current increment angle in *`for each`* loop]',
                                                                                 # description
                                                                                 'Define the rotation angle for one iteration\n'
                                                                                 'Returned as decimal value, in current rotation unit')),
                                                                    (':foreach.currentAngle',
                                                                             TokenizerRule.formatDescription(
                                                                                 'Reserved variable [Current rotation angle in *`for each`* loop]',
                                                                                 # description
                                                                                 'Define the rotation angle for current iteration\n'
                                                                                 'Returned as decimal value, in current rotation unit')),
                                                                    ],
                                                                    'v',
                                                                    onInitValue=self.__initTokenLower),


            TokenizerRule(BSLanguageDef.ITokenType.VARIABLE_USER, r":\b[a-z]+(?:[a-z0-9]|\.[a-z]|_+[a-z])*\b", onInitValue=self.__initTokenLower),

            TokenizerRule(BSLanguageDef.ITokenType.BINARY_OPERATOR, r"\+|\*|//|/|%|<=|<>|<|>=|>|=|\bin\b|\band\b|\bor\b|\bxor\b", ignoreIndent=True, onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.UNARY_OPERATOR, r"\bnot\b", ignoreIndent=True, onInitValue=self.__initTokenLower),
            TokenizerRule(BSLanguageDef.ITokenType.DUAL_OPERATOR, r"-", ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.SEPARATOR, r","),
            TokenizerRule(BSLanguageDef.ITokenType.PARENTHESIS_OPEN, r"\("),
            TokenizerRule(BSLanguageDef.ITokenType.PARENTHESIS_CLOSE, r"\)", ignoreIndent=True),
            TokenizerRule(BSLanguageDef.ITokenType.BRACKET_OPEN, r"\["),
            TokenizerRule(BSLanguageDef.ITokenType.BRACKET_CLOSE, r"\]", ignoreIndent=True),


            # all spaces except line feed
            TokenizerRule(BSLanguageDef.ITokenType.SPACE,  r"(?:(?!\n)\s)+"),


            TokenizerRule(BSLanguageDef.ITokenType.UNKNOWN,  r"[^\s]+"),
        ])

        self.tokenizer().setSimplifyTokenSpaces(True)
        self.tokenizer().setIndent(-1)
        #print(self.tokenizer())

        self.setStyles(UITheme.DARK_THEME, [
            (BSLanguageDef.ITokenType.STRING, '#9ac07c', False, False),
            (BSLanguageDef.ITokenType.NUMBER, '#c9986a', False, False),
            (BSLanguageDef.ITokenType.COLOR_CODE, '#6a98c9', False, False),

            (BSLanguageDef.ITokenType.FLOW_EXEC, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_IMPORT, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_REPEAT, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_TIMES, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_AND_STORE_RESULT, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_WITH_PARAMETERS, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_AS, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_DO, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_FOREACH, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_CALL, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_DEFMACRO, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_RETURN, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_SET_VARIABLE, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_IF, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_ELIF, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_ELSE, '#ffffff', True, False),
            (BSLanguageDef.ITokenType.FLOW_THEN, '#ffffff', True, False),

            (BSLanguageDef.ITokenType.FLOW_UNCOMPLETE, '#ffffff', False, True),


            (BSLanguageDef.ITokenType.ACTION_SET_UNIT, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_PEN, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_FILL, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_TEXT, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_DRAW, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_RULERS, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_LAYER, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_SELECTION, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_SCRIPT, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_MISC, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_FILL, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_PEN, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_TURN, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_STATE, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_CANVAS, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_UICONSOLE, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_UIDIALOG, '#e5dd82', True, False),
            (BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, '#e5dd82', True, False),

            (BSLanguageDef.ITokenType.ACTION_UNCOMPLETE, '#e5dd82', False, True),


            (BSLanguageDef.ITokenType.FUNCTION_NUMBER, '#e582bc', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_STRING, '#e582bc', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_COLOR, '#e582bc', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_LIST, '#e582bc', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_BOOLEAN, '#e582bc', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_VARIANT, '#e582bc', False, False),

            (BSLanguageDef.ITokenType.FUNCTION_UNCOMPLETE, '#e582bc', False, True),


            (BSLanguageDef.ITokenType.BINARY_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.UNARY_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.DUAL_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.SEPARATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.PARENTHESIS_OPEN, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.PARENTHESIS_CLOSE, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.BRACKET_OPEN, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.BRACKET_CLOSE, '#af2dff', False, False),

            (BSLanguageDef.ITokenType.VARIABLE_USER, '#00dacd', False, False),
            (BSLanguageDef.ITokenType.VARIABLE_RESERVED, '#00dacd', True, False),

            (BSLanguageDef.ITokenType.CONSTANT_NONE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_ONOFF, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_M, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_M_RPCT, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_R, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENSTYLE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENCAP, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENJOIN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_FILLRULE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_POSHALIGN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_POSVALIGN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_BLENDINGMODE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_SELECTIONMODE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_COLORLABEL, '#24ff8d', True, False),

            (BSLanguageDef.ITokenType.TEXT, '#ffffff', False, False),
            (BSLanguageDef.ITokenType.COMMENT, '#999999', False, True),

            (BSLanguageDef.ITokenType.SPACE, None, False, False)
        ])
        self.setStyles(UITheme.LIGHT_THEME, [
            (BSLanguageDef.ITokenType.STRING, '#9ac07c', False, False),
            (BSLanguageDef.ITokenType.NUMBER, '#c9986a', False, False),
            (BSLanguageDef.ITokenType.COLOR_CODE, '#c9986a', False, False),

            (BSLanguageDef.ITokenType.FLOW_EXEC, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_IMPORT, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_REPEAT, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_TIMES, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_AND_STORE_RESULT, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_WITH_PARAMETERS, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_AS, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_DO, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_FOREACH, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_CALL, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_DEFMACRO, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_RETURN, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_SET_VARIABLE, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_IF, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_ELIF, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_ELSE, '#000044', True, False),
            (BSLanguageDef.ITokenType.FLOW_THEN, '#000044', True, False),

            (BSLanguageDef.ITokenType.FLOW_UNCOMPLETE, '#000044', False, True),

            (BSLanguageDef.ITokenType.ACTION_SET_UNIT, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_PEN, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_FILL, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_TEXT, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_DRAW, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_RULERS, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_LAYER, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_SELECTION, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_SET_SCRIPT, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_MISC, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_FILL, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_PEN, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_DRAW_TURN, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_STATE, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_CANVAS, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_UICONSOLE, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_UIDIALOG, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, '#c278da', True, False),
            (BSLanguageDef.ITokenType.ACTION_UNCOMPLETE, '#c278da', False, True),

            (BSLanguageDef.ITokenType.FUNCTION_NUMBER, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_STRING, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_COLOR, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_LIST, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_BOOLEAN, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_VARIANT, '#ff80ff', False, False),
            (BSLanguageDef.ITokenType.FUNCTION_UNCOMPLETE, '#ff00ff', False, True),

            (BSLanguageDef.ITokenType.BINARY_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.UNARY_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.DUAL_OPERATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.SEPARATOR, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.PARENTHESIS_OPEN, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.PARENTHESIS_CLOSE, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.BRACKET_OPEN, '#af2dff', False, False),
            (BSLanguageDef.ITokenType.BRACKET_CLOSE, '#af2dff', False, False),

            (BSLanguageDef.ITokenType.VARIABLE_USER, '#00dacd', False, False),
            (BSLanguageDef.ITokenType.VARIABLE_RESERVED, '#00dacd', True, False),

            (BSLanguageDef.ITokenType.CONSTANT_NONE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_ONOFF, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_M, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_M_RPCT, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_UNITS_R, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENSTYLE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENCAP, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_PENJOIN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_FILLRULE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_POSHALIGN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_POSVALIGN, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_BLENDINGMODE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_SELECTIONMODE, '#24ff8d', True, False),
            (BSLanguageDef.ITokenType.CONSTANT_COLORLABEL, '#24ff8d', True, False),

            (BSLanguageDef.ITokenType.TEXT, '#6aafec', False, False),
            (BSLanguageDef.ITokenType.COMMENT, '#c278da', False, False),

            (BSLanguageDef.ITokenType.SPACE, None, False, False)
        ])

        self.__grammarRules=GrammarRule.setGrammarRules()
        self.__initialiseGrammar()

    def __initialiseGrammar(self):
        """Initialise Grammar for BuliScript language

        Grammar is defined from language definition class for convenience
        (centralise everything related to buliscript language in the same place)

        """
        self.__grammarRules.setOperatorPrecedence(
                GROperatorPrecedence(95, ASTItem,  GrammarRules.OPERATOR_INDEX,  'List_Index_Expression'),
                GROperatorPrecedence(90, Token,    GrammarRules.OPERATOR_UNARY,  'not'),
                GROperatorPrecedence(89, Token,    GrammarRules.OPERATOR_UNARY,  '-'),
                GROperatorPrecedence(80, Token,    GrammarRules.OPERATOR_BINARY, '*', '/', '//', '%'),
                GROperatorPrecedence(70, Token,    GrammarRules.OPERATOR_BINARY, '+'),
                GROperatorPrecedence(70, Token,    GrammarRules.OPERATOR_BINARY, '-'),
                GROperatorPrecedence(60, Token,    GrammarRules.OPERATOR_BINARY, '<', '>', '<=', '>=', '=', '<>', 'in'),
                GROperatorPrecedence(40, Token,    GrammarRules.OPERATOR_BINARY, 'and'),
                GROperatorPrecedence(30, Token,    GrammarRules.OPERATOR_BINARY, 'xor'),
                GROperatorPrecedence(20, Token,    GrammarRules.OPERATOR_BINARY, 'or')
            )


        GrammarRule('Script',
                GrammarRule.OPTION_FIRST,   # the 'Script' grammar is defined as the first grammar rule
                GROptional('Declarations_Section'),
                GROptional('ScriptBlock')
            )

        GrammarRule('ScriptBlock',
                GrammarRule.OPTION_AST,
                # --
                GROneOrMore('Comment',
                            'Action',
                            'Flow',
                            #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
                        )
            )

        GrammarRule('Declarations_Section',
                GROneOrMore('Comment',
                            'Flow_Set_Variable',
                            'Flow_Import_Macro',
                            'Flow_Import_Image',
                            'Flow_Define_Macro',
                            #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
                        )
            )

        GrammarRule('Action',
                GROne('Action_Set_Unit_Canvas',
                      'Action_Set_Unit_Rotation',
                      'Action_Set_Pen_Color',
                      'Action_Set_Pen_Size',
                      'Action_Set_Pen_Style',
                      'Action_Set_Pen_Cap',
                      'Action_Set_Pen_Join',
                      'Action_Set_Pen_Opacity',
                      'Action_Set_Fill_Color',
                      'Action_Set_Fill_Rule',
                      'Action_Set_Fill_Opacity',
                      'Action_Set_Text_Color',
                      'Action_Set_Text_Opacity',
                      'Action_Set_Text_Font',
                      'Action_Set_Text_Size',
                      'Action_Set_Text_Bold',
                      'Action_Set_Text_Italic',
                      'Action_Set_Text_Outline',
                      'Action_Set_Text_Letter_Spacing',
                      'Action_Set_Text_Stretch',
                      'Action_Set_Text_HAlignment',
                      'Action_Set_Text_VAlignment',
                      'Action_Set_Draw_Antialiasing',
                      'Action_Set_Draw_Blending',
                      'Action_Set_Canvas_Grid_Color',
                      'Action_Set_Canvas_Grid_Style',
                      'Action_Set_Canvas_Grid_Size',
                      'Action_Set_Canvas_Grid_Opacity',
                      'Action_Set_Canvas_Rulers_Color',
                      'Action_Set_Canvas_Origin_Color',
                      'Action_Set_Canvas_Origin_Style',
                      'Action_Set_Canvas_Origin_Size',
                      'Action_Set_Canvas_Origin_Opacity',
                      'Action_Set_Canvas_Origin_Position',
                      'Action_Set_Canvas_Position_Color',
                      'Action_Set_Canvas_Position_Size',
                      'Action_Set_Canvas_Position_Opacity',
                      'Action_Set_Canvas_Position_Fulfill',
                      'Action_Set_Canvas_Background_Opacity',
                      'Action_Set_Canvas_Background_From_Document',
                      'Action_Set_Canvas_Background_From_Layer_Name',
                      'Action_Set_Canvas_Background_From_Layer_Id',
                      'Action_Set_Canvas_Background_From_Layer_Active',
                      'Action_Set_Canvas_Background_From_Color',
                      # TODO
                      #'Action_Set_Layer',
                      #'Action_Set_Selection',
                      'Action_Set_Script_Execution_Verbose',
                      'Action_Set_Script_Randomize_Seed',
                      'Action_Draw_Shape_Line',
                      'Action_Draw_Shape_Square',
                      'Action_Draw_Shape_Round_Square',
                      'Action_Draw_Shape_Rect',
                      'Action_Draw_Shape_Round_Rect',
                      'Action_Draw_Shape_Circle',
                      'Action_Draw_Shape_Ellipse',
                      'Action_Draw_Shape_Dot',
                      'Action_Draw_Shape_Pixel',
                      'Action_Draw_Shape_Image',
                      'Action_Draw_Shape_Scaled_Image',
                      'Action_Draw_Shape_Text',
                      'Action_Draw_Shape_Star',
                      'Action_Draw_Misc_Clear_Canvas',
                      # TODO
                      #'Action_Draw_Misc_Apply_To_Layer',
                      'Action_Draw_Shape_Start',
                      'Action_Draw_Shape_Stop',
                      'Action_Draw_Fill_Activate',
                      'Action_Draw_Fill_Deactivate',
                      'Action_Draw_Pen_Up',
                      'Action_Draw_Pen_Down',
                      'Action_Draw_Move_Home',
                      'Action_Draw_Move_Forward',
                      'Action_Draw_Move_Backward',
                      'Action_Draw_Move_Left',
                      'Action_Draw_Move_Right',
                      'Action_Draw_Move_To',
                      'Action_Draw_Turn_Left',
                      'Action_Draw_Turn_Right',
                      'Action_Draw_Turn_To',
                      'Action_State_Push',
                      'Action_State_Pop',
                      'Action_Canvas_Show_Grid',
                      'Action_Canvas_Hide_Grid',
                      'Action_Canvas_Show_Origin',
                      'Action_Canvas_Hide_Origin',
                      'Action_Canvas_Show_Position',
                      'Action_Canvas_Hide_Position',
                      'Action_Canvas_Show_Background',
                      'Action_Canvas_Hide_Background',
                      'Action_Canvas_Show_Rulers',
                      'Action_Canvas_Hide_Rulers',
                      'Action_UIConsole_Print',
                      'Action_UIDialog_Message',
                      'Action_UIDialog_Boolean_Input',
                      'Action_UIDialog_Integer_Input',
                      'Action_UIDialog_Decimal_Input',
                      'Action_UIDialog_Color_Input',
                      'Action_UIDialog_String_Input',
                      'Action_UIDialog_Single_Choice_Input',
                      'Action_UIDialog_Multiple_Choice_Input'

                )
            )

        GrammarRule('Action_Set_Unit_Canvas',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_UNIT, 'set unit canvas', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Unit_Rotation',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_UNIT, 'set unit rotation', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Size',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen size', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Style',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen style', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Cap',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen cap', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Join',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen join', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Pen_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_PEN, 'set pen opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Fill_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_FILL, 'set fill color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Fill_Rule',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_FILL, 'set fill rule', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Fill_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_FILL, 'set fill opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Font',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text font', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Size',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text size', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Bold',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text bold', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Italic',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text italic', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Outline',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text outline', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Letter_Spacing',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text letter spacing', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_Stretch',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text stretch', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_HAlignment',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text horizontal alignment', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Text_VAlignment',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_TEXT, 'set text vertical alignment', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Draw_Antialiasing',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_DRAW, 'set draw antialiasing', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Draw_Blending',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_DRAW, 'set draw blending mode', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Grid_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, 'set canvas grid color', False),
                'Any_Expression',
                GROptional('Any_Expression')
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Grid_Style',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, 'set canvas grid style', False),
                'Any_Expression',
                GROptional('Any_Expression')
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Grid_Size',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, 'set canvas grid size', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Grid_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_GRID, 'set canvas grid opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Rulers_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_RULERS, 'set canvas rulers color', False),
                'Any_Expression',
                GROptional('Any_Expression')
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Origin_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, 'set canvas origin color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Origin_Style',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, 'set canvas origin style', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Origin_Size',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, 'set canvas origin size', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Origin_Position',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, 'set canvas origin position', False),
                'Any_Expression',
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Origin_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_ORIGIN, 'set canvas origin opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Position_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, 'set canvas position color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Position_Size',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, 'set canvas position size', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Position_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, 'set canvas position opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Position_Fulfill',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_POSITION, 'set canvas position fulfilled', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_Opacity',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background opacity', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_From_Document',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background from document', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_From_Layer_Name',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background from layer name', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_From_Layer_Id',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background from layer id', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_From_Layer_Active',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background from layer active', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Canvas_Background_From_Color',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_CANVAS_BACKGROUND, 'set canvas background from color', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Script_Execution_Verbose',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_SCRIPT, 'set script execution verbose', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Set_Script_Randomize_Seed',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_SET_SCRIPT, 'set script randomize seed', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Square',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw square', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Line',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw line', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Round_Square',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw round square', False),
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Rect',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw rect', False),
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Round_Rect',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw round rect', False),
                'Any_Expression',
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Circle',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw circle', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Ellipse',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw ellipse', False),
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Dot',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw dot', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Pixel',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw pixel', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Image',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw image', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Scaled_Image',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw scaled image', False),
                'Any_Expression',
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Text',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw text', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Star',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'draw star', False),
                'Any_Expression',
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Misc_Clear_Canvas',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MISC, 'clear canvas', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Start',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'start to draw shape', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Shape_Stop',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_SHAPE, 'stop to draw shape', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Fill_Activate',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_FILL, 'activate fill', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Fill_Deactivate',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_FILL, 'deactivate fill', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Pen_Up',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_PEN, 'pen up', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Pen_Down',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_PEN, 'pen down', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_Home',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move home', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_Forward',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move forward', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_Backward',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move backward', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_Left',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move left', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_Right',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move right', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Move_To',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_MOVE, 'move to', False),
                'Any_Expression',
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Turn_Left',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_TURN, 'turn left', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Turn_Right',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_TURN, 'turn right', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Draw_Turn_To',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_DRAW_TURN, 'turn to', False),
                'Any_Expression',
                GROptional('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_State_Push',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_STATE, 'push state', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_State_Pop',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_STATE, 'pop state', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Show_Grid',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'show canvas grid', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Hide_Grid',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'hide canvas grid', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Show_Origin',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'show canvas origin', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Hide_Origin',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'hide canvas origin', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Show_Position',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'show canvas position', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Hide_Position',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'hide canvas position', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Show_Background',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'show canvas background', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Hide_Background',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'hide canvas background', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Show_Rulers',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'show canvas rulers', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_Canvas_Hide_Rulers',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_CANVAS, 'hide canvas rulers', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_UIConsole_Print',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UICONSOLE, 'print', False),
                GROneOrMore('Any_Expression'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False)
            )

        GrammarRule('Action_UIDialog_Message',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for message', False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Title',
                             'Action_UIDialog_Option_With_Message'),
            )

        GrammarRule('Action_UIDialog_Boolean_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for boolean input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Title',
                             'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Integer_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for integer input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Minimum_Value',
                             'Action_UIDialog_Option_With_Maximum_Value',
                             'Action_UIDialog_Option_With_Default_Value',
                             'Action_UIDialog_Option_With_Title',
                             'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Decimal_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for decimal input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Minimum_Value',
                             'Action_UIDialog_Option_With_Maximum_Value',
                             'Action_UIDialog_Option_With_Default_Value',
                             'Action_UIDialog_Option_With_Title',
                             'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Color_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for color input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Default_Value',
                             'Action_UIDialog_Option_With_Title',
                             'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_String_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for string input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Default_Value',
                            'Action_UIDialog_Option_With_Title',
                            'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Single_Choice_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for single choice input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Default_Index',
                            'Action_UIDialog_Option_With_Title',
                            'Action_UIDialog_Option_With_Combobox_Choices',
                            'Action_UIDialog_Option_With_RadioButton_Choices',
                            'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Multiple_Choice_Input',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG, 'open dialog for multiple choice input', False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRNoneOrMore('Action_UIDialog_Option_With_Default_Index',
                            'Action_UIDialog_Option_With_Title',
                            'Action_UIDialog_Option_With_Choices',
                            'Action_UIDialog_Option_With_Minimum_Choices',
                            'Action_UIDialog_Option_With_Message')
            )

        GrammarRule('Action_UIDialog_Option_With_Title',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with title', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Message',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with message', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Minimum_Value',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with minimum value', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Maximum_Value',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with maximum value', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Default_Value',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with default value', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Default_Index',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with default index', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Combobox_Choices',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with combobox choices', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_RadioButton_Choices',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with radio button choices', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Choices',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with choices', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Action_UIDialog_Option_With_Minimum_Choices',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.ACTION_UIDIALOG_OPTION, 'with minimum choices', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Flow',
                GROne('Flow_Set_Variable',
                      'Flow_Stop_Script',
                      'Flow_Call_Macro',
                      'Flow_If',
                      'Flow_Repeat',
                      'Flow_ForEach',
                      'Flow_Return'),
            )

        GrammarRule('Flow_Set_Variable',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_SET_VARIABLE),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                GRToken(BSLanguageDef.ITokenType.BINARY_OPERATOR, '=', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Flow_Import_Macro',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_IMPORT, 'import macro from', False),
                'Any_Expression',
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Flow_Import_Image',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_IMPORT, 'import image from', False),
                'Any_Expression',
                #GROptional(GRToken(BSLanguageDef.ITokenType.NEWLINE, False)),
                GRToken(BSLanguageDef.ITokenType.FLOW_AS, False),
                GROne('String_Value'),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Flow_Define_Macro',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_DEFMACRO, False),
                GROne('String_Value'),
                GROptional(GrammarRule('Flow_Define_Macro__withParameters',
                           GRToken(BSLanguageDef.ITokenType.FLOW_WITH_PARAMETERS, False),
                           GROneOrMore(GRToken(BSLanguageDef.ITokenType.VARIABLE_USER))
                       )
                   ),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.FLOW_AS, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                GROne('ScriptBlock'),
                GROptional(GRToken(BSLanguageDef.ITokenType.DEDENT, False)),
            )

        GrammarRule('Flow_Stop_Script',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_EXEC, 'stop script', False),
            )

        GrammarRule('Flow_Call_Macro',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_CALL, 'call macro', False),
                GROne('String_Value'),
                GRNoneOrMore('Any_Expression'),
                GROptional(GrammarRule('Flow_Call_Macro__storeResult',
                                       GrammarRule.OPTION_AST,
                                       # --
                                       GRToken(BSLanguageDef.ITokenType.FLOW_AND_STORE_RESULT, False),
                                       GRToken(BSLanguageDef.ITokenType.VARIABLE_USER)
                                    )
                    )
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
            )

        GrammarRule('Flow_If',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_IF, False),
                'Any_Expression',
                GRToken(BSLanguageDef.ITokenType.FLOW_THEN, False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                'ScriptBlock',
                GRToken(BSLanguageDef.ITokenType.DEDENT, False),
                GROptional('Flow_ElseIf',
                           'Flow_Else'),
            )

        GrammarRule('Flow_ElseIf',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_ELIF, False),
                'Any_Expression',
                GRToken(BSLanguageDef.ITokenType.FLOW_THEN, False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                'ScriptBlock',
                GRToken(BSLanguageDef.ITokenType.DEDENT, False),
                GROptional('Flow_ElseIf',
                           'Flow_Else'),
            )

        GrammarRule('Flow_Else',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_ELSE, False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                'ScriptBlock',
                GRToken(BSLanguageDef.ITokenType.DEDENT, False),
            )

        GrammarRule('Flow_Return',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_RETURN, False),
                GROptional('Any_Expression'),
            )

        GrammarRule('Flow_Repeat',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_REPEAT, False),
                'Any_Expression',
                #GROptional(GRToken(BSLanguageDef.ITokenType.NEWLINE, False)),
                GRToken(BSLanguageDef.ITokenType.FLOW_TIMES, False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                'ScriptBlock',
                GRToken(BSLanguageDef.ITokenType.DEDENT, False)
            )

        GrammarRule('Flow_ForEach',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.FLOW_FOREACH, False),
                'Any_Expression',
                GRToken(BSLanguageDef.ITokenType.FLOW_AS, False),
                GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                #GROptional(GRToken(BSLanguageDef.ITokenType.NEWLINE, False)),
                GRToken(BSLanguageDef.ITokenType.FLOW_DO, False),
                #GRToken(BSLanguageDef.ITokenType.NEWLINE, False),
                GRToken(BSLanguageDef.ITokenType.INDENT, False),
                GROne('ScriptBlock'),
                GRToken(BSLanguageDef.ITokenType.DEDENT, False)
            )

        GrammarRule('Any_Expression',
                GROne('Evaluation_Expression',
                      'Any_Value'
                    )
            )

        GrammarRule('Any_Value',
                GROne('Function',
                      'Variable',
                      'String_Value',
                      GRToken(BSLanguageDef.ITokenType.NUMBER),
                      GRToken(BSLanguageDef.ITokenType.COLOR_CODE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_NONE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_ONOFF),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_UNITS_M),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_UNITS_R),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_UNITS_M_RPCT),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_PENSTYLE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_PENCAP),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_PENJOIN),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_FILLRULE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_POSHALIGN),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_POSVALIGN),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_BLENDINGMODE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_SELECTIONMODE),
                      GRToken(BSLanguageDef.ITokenType.CONSTANT_COLORLABEL),
                      'List_Value',
                    ),
                GRNoneOrMore('List_Index_Expression')
            )

        GrammarRule('String_Value',
                GrammarRule.OPTION_AST,
                # --
                GROneOrMore(GRToken(BSLanguageDef.ITokenType.STRING))
            )

        GrammarRule('Evaluation_Expression',
                GrammarRule.OPTION_OPERATOR_PRECEDENCE,
                # --
                GROne('Evaluation_Expression_Unary_Operator',
                      'Evaluation_Expression_Parenthesis',
                      'Any_Value'),
                GROptional('Evaluation_Expression_Binary_Operator')
            )

        # When an evaluation expression start, only the first one need to manage operator precedence
        # for this, grammar rules are built:
        # - first evaluation expression manage OPTION_OPERATOR_PRECEDENCE
        # - following evaluation expression do not manage OPTION_OPERATOR_PRECEDENCE
        # for this, create a second Evaluation_Expression rule, without option, that is called for binary operators
        GrammarRule('Evaluation_Expression__noop',
                # --
                GROne('Evaluation_Expression_Unary_Operator',
                      'Evaluation_Expression_Parenthesis',
                      'Any_Value'),
                GROptional('Evaluation_Expression_Binary_Operator')
            )

        GrammarRule('Evaluation_Expression_Parenthesis',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.PARENTHESIS_OPEN, False),
                # use the evaluation expression with OPTION_OPERATOR_PRECEDENCE here as we're in an another level of evaluation
                'Evaluation_Expression',
                GRToken(BSLanguageDef.ITokenType.PARENTHESIS_CLOSE, False),
                GROptional('List_Index_Expression')
            )

        GrammarRule('Evaluation_Expression_Binary_Operator',
                GROne(GRToken(BSLanguageDef.ITokenType.BINARY_OPERATOR, '+', '*', '/', '//', '%', 'and', 'or', 'xor', '<=', '<>', '<', '>', '>=', '=', 'in'),
                      GRToken(BSLanguageDef.ITokenType.DUAL_OPERATOR, '-')),
                'Evaluation_Expression__noop',
                GROptional('Evaluation_Expression_Binary_Operator')
            )

        GrammarRule('Evaluation_Expression_Unary_Operator',
                #GrammarRule.OPTION_AST, ==> no!
                # --
                GROne(GRToken(BSLanguageDef.ITokenType.UNARY_OPERATOR, 'not'),
                      GRToken(BSLanguageDef.ITokenType.DUAL_OPERATOR, '-')),
                GROne('Evaluation_Expression_Unary_Operator',
                      'Evaluation_Expression_Parenthesis',
                      'Any_Value'),
                GROptional('Evaluation_Expression_Binary_Operator')
            )

        GrammarRule('List_Value',
                GrammarRule.OPTION_AST,
                # --
                GRToken(BSLanguageDef.ITokenType.BRACKET_OPEN, False),
                GROptional('List_Value_Item'),
                GRToken(BSLanguageDef.ITokenType.BRACKET_CLOSE, False),
            )

        GrammarRule('List_Value_Item',
                'Any_Expression',
                GRNoneOrMore('List_Value_Next_Item'),
            )

        GrammarRule('List_Value_Next_Item',
                GRToken(BSLanguageDef.ITokenType.SEPARATOR, False),
                'Any_Expression',
            )

        GrammarRule('List_Index_Expression',
                GrammarRule.OPTION_AST | GrammarRule.OPTION_NOT_PRECEDED_BY_SPACE,
                # --
                GRToken(BSLanguageDef.ITokenType.BRACKET_OPEN, False),
                'Evaluation_Expression',
                GRToken(BSLanguageDef.ITokenType.BRACKET_CLOSE, False)
            )

        GrammarRule('Variable',
                GROne(GRToken(BSLanguageDef.ITokenType.VARIABLE_USER),
                      GRToken(BSLanguageDef.ITokenType.VARIABLE_RESERVED))
            )

        GrammarRule('Function',
                GrammarRule.OPTION_AST,
                # --
                GROne(GRToken(BSLanguageDef.ITokenType.FUNCTION_NUMBER),
                      GRToken(BSLanguageDef.ITokenType.FUNCTION_STRING),
                      GRToken(BSLanguageDef.ITokenType.FUNCTION_COLOR),
                      GRToken(BSLanguageDef.ITokenType.FUNCTION_LIST),
                      GRToken(BSLanguageDef.ITokenType.FUNCTION_BOOLEAN),
                      GRToken(BSLanguageDef.ITokenType.FUNCTION_VARIANT)),
                GRToken(BSLanguageDef.ITokenType.PARENTHESIS_OPEN, False),
                GROptional('Function_Parameters'),
                GRToken(BSLanguageDef.ITokenType.PARENTHESIS_CLOSE, False),
            )

        GrammarRule('Function_Parameters',
                'Any_Expression',
                GRNoneOrMore('Function_Parameters_Next'),
            )

        GrammarRule('Function_Parameters_Next',
                GRToken(BSLanguageDef.ITokenType.SEPARATOR, False),
                'Any_Expression',
            )

        GrammarRule('Comment',
                GRToken(BSLanguageDef.ITokenType.COMMENT, False),
                #GROneOrMore(GRToken(BSLanguageDef.ITokenType.NEWLINE, False))
            )

    def __initTokenNumber(self, tokenType, value):
        """Convert value for NUMBER token from string to integer or decimal"""
        try:
            # try to convert value as integer
            return int(value)
        except Exception as e:
            # not an integer??
            pass

        try:
            # try to convert value as a decimal value
            return float(value)
        except Exception as e:
            # not a decimal??
            pass

        # normally shouln't occurs... return initial value
        print('__initTokenNumber ERROR??', tokenType, value)
        return value

    def __initTokenString(self, tokenType, value):
        """Convert value for STRING (remove string delimiters)"""

        if len(value)>1:
            return value[1:-1]

        return value

    def __initTokenBoolean(self, tokenType, value):
        """Convert value for BOOLEAN"""

        return (value.upper()=='ON')

    def __initTokenLower(self, tokenType, value):
        """Convert value for lower case"""

        return value.lower()

    def __initTokenUpper(self, tokenType, value):
        """Convert value for upper case"""

        return value.upper()

    def __initTokenColor(self, tokenType, value):
        """Convert value for QColor"""

        try:
            return QColor(value)
        except:
            # not a valid color?
            pass

        # normally shouln't occurs... return initial value
        print('__initTokenColor ERROR??', tokenType, value)
        return value

    def grammarRules(self):
        """Return defined grammar rules"""
        return self.__grammarRules
