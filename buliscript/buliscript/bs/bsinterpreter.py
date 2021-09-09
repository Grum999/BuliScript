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


import sys
import re
import uuid
import random
import math

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from .bssettings import (
        BSSettings,
        BSSettingsKey
    )
from .bslanguagedef import BSLanguageDef


from buliscript.pktk.modules.utils import Debug
from buliscript.pktk.modules.listutils import (
        flatten,
        rotate,
        unique
    )
from buliscript.pktk.modules.timeutils import Timer
from buliscript.pktk.modules.tokenizer import (
        Token,
        TokenizerRule
    )
from buliscript.pktk.modules.parser import (
        Parser,
        ASTStatus,
        ASTSpecialItemType,
        ASTItem
    )

from buliscript.pktk.widgets.wcolorselector import (
        WColorPicker,
        WColorComplementary
    )
from buliscript.pktk.widgets.wiodialog import (
        WDialogMessage,
        WDialogBooleanInput,
        WDialogStrInput,
        WDialogIntInput,
        WDialogFloatInput,
        WDialogComboBoxChoiceInput,
        WDialogRadioButtonChoiceInput,
        WDialogCheckBoxChoiceInput,
        WDialogColorInput
    )

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )


class EInterpreter(Exception):
    """An error occured during script execution

    Usually error is
    """
    ERROR_LEVEL_STOP = 0
    ERROR_LEVEL_ERROR = 1
    ERROR_LEVEL_CRITICAL = 2

    def __init__(self, message, ast, errorLevel=1):
        super(EInterpreter, self).__init__(message)
        self.__ast=ast
        self.__errorLevel=errorLevel

    def ast(self):
        """Return AST from which exception has been raised"""
        return self.__ast

    def errorLevel(self):
        """Return error level for exception"""
        return self.__errorLevel

class EInterpreterInternalError(EInterpreter):
    """An error occured during execution

    These exception are more related to an internal problem (initialisation, internal bug, ...)
    than a problem from script
    """
    def __init__(self, message, ast, errorLevel=2):
        super(EInterpreterInternalError, self).__init__(f"Internal error: <<{message}>>", ast, errorLevel)


class BSInterpreter(QObject):
    """The interpreter execute provided BuliScript script"""
    actionExecuted = Signal(str)
    executionStarted = Signal()
    executionFinished = Signal()

    CONST_MEASURE_UNIT=['PX', 'PCT', 'MM', 'INCH']
    CONST_MEASURE_UNIT_RPCT=['PX', 'PCT', 'MM', 'INCH', 'RPCT']
    CONST_ROTATION_UNIT=['DEGREE', 'RADIAN']
    CONST_PEN_STYLE=['SOLID','DASH','DOT','DASHDOT','NONE']
    CONST_PEN_CAP=['SQUARE','FLAT','ROUNDCAP']
    CONST_PEN_JOIN=['BEVEL','MITTER','ROUNDJOIN']
    CONST_FILL_RULE=['EVEN','WINDING']
    CONST_HALIGN=['LEFT','CENTER','RIGHT']
    CONST_VALIGN=['TOP','MIDDLE','BOTTOM']
    CONST_DRAW_BLENDING_MODE=['NORMAL','SOURCE_OVER','DESTINATION_CLEAR','DESTINATION_OVER','SOURCE_IN','SOURCE_OUT','DESTINATION_IN','DESTINATION_OUT','DESTINATION_ATOP','SOURCE_ATOP','EXCLUSIVE_OR','PLUS','MULTIPLY','SCREEN','OVERLAY','DARKEN','LIGHTEN','COLORDODGE','COLORBURN','HARD_LIGHT','SOFT_LIGHT','DIFFERENCE','EXCLUSION',
                              'BITWISE_S_OR_D','BITWISE_S_AND_D','BITWISE_S_XOR_D','BITWISE_S_NOR_D','BITWISE_S_NAND_D','BITWISE_NS_XOR_D','BITWISE_S_NOT','BITWISE_NS_AND_D','BITWISE_S_AND_ND','BITWISE_NS_OR_D','BITWISE_CLEAR','BITWISE_SET','BITWISE_NOT_D','BITWISE_S_OR_ND']

    def __init__(self, languageDef):
        super(BSInterpreter, self).__init__(None)

        # language languageDefinition
        if not isinstance(languageDef, BSLanguageDef):
            raise EInvalidType("Given `languageDef` must be <BSLanguageDef>")

        # script to execute
        self.__script=''

        # main Abstract Syntax Tree is a ASTItem
        self.__astRoot=None

        # current stack of script blocks
        self.__scriptBlockStack=BSScriptBlockStack()

        # macro definitions
        self.__macroDefinitions=BSScriptBlockDefinedMacros()

        # language definition; once defined, can't be changed
        self.__languageDef=languageDef

        # parser is initialised from language definition; once defined, can't be changed
        self.__parser=Parser(languageDef.tokenizer(), languageDef.grammarRules())
        # let parser ignore some tokens useless for execution
        self.__parser.setIgnoredTokens([BSLanguageDef.ITokenType.SPACE,
                                        BSLanguageDef.ITokenType.NEWLINE,
                                        BSLanguageDef.ITokenType.COMMENT])

        # internal value to define if an execution is currently running
        self.__isRunning=False

        # canvas is a QPaintDevice on which everything will be drawn
        self.__canvas=None

        # store current document usefull informations
        # . current document (Document)
        # . current document bounds (QRect)
        # . current document resolution (float)
        # . current layer
        # . current layer bounds (QRect)
        self.__currentDocument=None
        self.__currentDocumentBounds=QRect()
        self.__currentDocumentResolution=1.0
        self.__currentLayer=None
        self.__currentLayerBounds=QRect()


        # debug mode by default is False
        # when True, execution is made step by step
        self.__optionDebugMode=False

        # verbose mode by default is False
        # when True, all action will generate a verbose information
        self.__optionVerboseMode=False

        # delay mode by default is 0
        # when set, a delay is applied between each instruction
        self.__optionDelay=0

    # --------------------------------------------------------------------------
    # utils methods
    # --------------------------------------------------------------------------
    def __verbose(self, text, ast=None):
        """If execution is defined as verbose, will print given text"""
        if not self.__optionVerboseMode:
            return

        if ast is None:
            msg=f'Verbose [---:----->---:-----] >> {text}'
        else:
            position=ast.position()

            if position["from"]["column"]==position["to"]["column"] and position["from"]["row"]==position["to"]["row"]:
                msg=f'Verbose [---:----->---:-----] >> {text}'
            else:
                msg=f'Verbose [{position["from"]["column"]:03}:{position["from"]["row"]:05}>{position["to"]["column"]:03}:{position["to"]["row"]:05}] >> {text}'
        # need to review print... (callback, signal?)
        self.__print(msg)

    def __warning(self, text, ast=None):
        """Even if execution is not defined as verbose, will print given text as warning"""
        if ast is None:
            msg=f'Warning [---:----->---:-----] >> {text}'
        else:
            position=ast.position()

            if position["from"]["column"]==position["to"]["column"] and position["from"]["row"]==position["to"]["row"]:
                msg=f'Warning [---:----->---:-----] >> {text}'
            else:
                msg=f'Warning [{position["from"]["column"]:03}:{position["from"]["row"]:05}>{position["to"]["column"]:03}:{position["to"]["row"]:05}] >> {text}'

        # need to review print... (callback, signal?)
        self.__print(msg)

    def __error(self, text, ast=None):
        """Even if execution is not defined as verbose, will print given text as error"""
        if ast is None:
            msg=f'Error   [---:----->---:-----] >> {text}'
        else:
            position=ast.position()

            if position["from"]["column"]==position["to"]["column"] and position["from"]["row"]==position["to"]["row"]:
                msg=f'Error   [---:----->---:-----] >> {text}'
            else:
                msg=f'Error   [{position["from"]["column"]:03}:{position["from"]["row"]:05}>{position["to"]["column"]:03}:{position["to"]["row"]:05}] >> {text}'

        # need to review print... (callback, signal?)
        self.__print(msg)

    def __print(self, text):
        """Print text to console"""
        print(text)

    def __delay(self):
        """Do a pause in execution"""
        if self.__optionDelay>0:
            Timer.sleep(self.__optionDelay)

    def __evaluate(self, item):
        """Evaluate item value

        If item is a Token, return Token value
        If item is an AST, return AST evaluation
        """
        if isinstance(item, Token):
            if item.type() in (BSLanguageDef.ITokenType.VARIABLE_USER, BSLanguageDef.ITokenType.VARIABLE_RESERVED):
                # get variable value
                return self.__scriptBlockStack.current().variable(item.value())

            # otherwise return token value
            return item.value()
        elif isinstance(item, ASTItem):
            return self.__executeAst(item)
        else:
            # a str, int, float, .... provided directly
            return item

    def __checkFctParamNumber(self, currentAst, fctLabel, *values):
        """raise an exception if number of provided parameters is not expected (used for functions)"""
        if not len(currentAst.nodes())-1 in values:
            raise EInterpreter(f"{fctLabel}: invalid number of provided arguments", currentAst)

    def __checkParamNumber(self, currentAst, fctLabel, *values):
        """raise an exception if number of provided parameters is not expected (used for others)"""
        if not len(currentAst.nodes()) in values:
            raise EInterpreter(f"{fctLabel}: invalid number of provided arguments", currentAst)

    def __checkParamType(self, currentAst, fctLabel, name, value, *types):
        """raise an exception if value is not of given type"""
        if not isinstance(value, types):
            raise EInterpreter(f"{fctLabel}: invalid type for argument {name}", currentAst)

    def __checkParamDomain(self, currentAst, fctLabel, name, controlOk, msg, raiseException=True):
        """raise an exception if value is not in expected domain"""
        if not controlOk:
            if raiseException:
                raise EInterpreter(f"{fctLabel}: invalid domain for argument {name}, {msg}", currentAst)
            else:
                self.__warning(f"{fctLabel}: invalid domain for argument {name}, {msg}", currentAst)
        return controlOk

    def __checkOption(self, currentAst, fctLabel, value, forceRaise=False):
        """raise an exception is value if not of given type"""
        if not isinstance(value, ASTItem) or forceRaise:
            raise EInterpreter(f"{fctLabel}: invalid/unknown option provided", currentAst)

    def __strValue(self, variableValue):
        """Return formatted string value"""
        if isinstance(variableValue, str):
            return f'"{variableValue}"'
        elif isinstance(variableValue, QColor):
            if variableValue.alpha()==0xff:
                return variableValue.name(QColor.HexRgb)
            else:
                return variableValue.name(QColor.HexArgb)
        elif isinstance(variableValue, bool):
            if variableValue:
                return "ON"
            else:
                return "OFF"
        else:
            return variableValue


    # --------------------------------------------------------------------------
    # Script execution methods
    # --------------------------------------------------------------------------
    def __executeStart(self):
        """Execute from root AST"""
        self.__macroDefinitions.clear()
        self.__scriptBlockStack.clear()

        self.__currentDocument=Krita.instance().activeDocument()
        #if self.__currentDocument is None:
        #    raise EInterpreter("No active document!", None)

        #self.__currentDocumentBounds=self.__currentDocument.bounds()
        # assume x/y resolution are the same
        # can't use Document.resolution() as it returns an integer value and value
        # is not correct if resolution is defined with decimal properties
        #self.__currentDocumentResolution=self.__currentDocument.xRes()

        #self.__currentLayer=self.__currentDocument.activeNode()
        #self.__currentLayerBounds=self.__currentLayer.bounds()


        if self.__astRoot.id()==ASTSpecialItemType.ROOT:
            return self.__executeAst(self.__astRoot)

        raise EInterpreterInternalError("Invalid ROOT", self.__astRoot)

    def __executeAst(self, currentAst):
        """Execute current given AST"""

        # ----------------------------------------------------------------------
        # ROOT
        # ----
        if currentAst.id() == ASTSpecialItemType.ROOT:
            # given AST is the main block of instructions
            return self.__executeScriptBlock(currentAst, True, "Main script")

        # ----------------------------------------------------------------------
        # Flows
        # -----

        # ----------------------------------------------------------------------
        # Flows
        # -----
        elif currentAst.id() == 'Flow_Set_Variable':
            return self.__executeFlowSetVariable(currentAst)
        elif currentAst.id() == 'Flow_Define_Macro':
            return self.__executeFlowDefineMacro(currentAst)
        elif currentAst.id() == 'Flow_Stop_Script':
            return self.__executeFlowStopScript(currentAst)
        elif currentAst.id() == 'Flow_Call_Macro':
            return self.__executeFlowCallMacro(currentAst)
        elif currentAst.id() == 'Flow_Return':
            return self.__executeFlowReturn(currentAst)
        elif currentAst.id() == 'Flow_If':
            return self.__executeFlowIfElseIf(currentAst, 'if')
        elif currentAst.id() == 'Flow_ElseIf':
            return self.__executeFlowIfElseIf(currentAst, 'else if')
        elif currentAst.id() == 'Flow_Else':
            return self.__executeFlowElse(currentAst)
        elif currentAst.id() == 'Flow_Repeat':
            return self.__executeFlowRepeat(currentAst)
        elif currentAst.id() == 'Flow_ForEach':
            return self.__executeFlowForEach(currentAst)

        # ----------------------------------------------------------------------
        # Actions
        # -------
        elif currentAst.id() == 'Action_Set_Unit_Canvas':
            return self.__executeActionSetUnitCanvas(currentAst)
        elif currentAst.id() == 'Action_Set_Unit_Rotation':
            return self.__executeActionSetUnitRotation(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Color':
            return self.__executeActionSetPenColor(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Size':
            return self.__executeActionSetPenSize(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Style':
            return self.__executeActionSetPenStyle(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Cap':
            return self.__executeActionSetPenCap(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Join':
            return self.__executeActionSetPenJoin(currentAst)
        elif currentAst.id() == 'Action_Set_Pen_Opacity':
            return self.__executeActionSetPenOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Fill_Color':
            return self.__executeActionSetFillColor(currentAst)
        elif currentAst.id() == 'Action_Set_Fill_Rule':
            return self.__executeActionSetFillRule(currentAst)
        elif currentAst.id() == 'Action_Set_Fill_Opacity':
            return self.__executeActionSetFillOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Color':
            return self.__executeActionSetTextColor(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Opacity':
            return self.__executeActionSetTextOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Font':
            return self.__executeActionSetTextFont(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Size':
            return self.__executeActionSetTextSize(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Bold':
            return self.__executeActionSetTextBold(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Italic':
            return self.__executeActionSetTextItalic(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Outline':
            return self.__executeActionSetTextOutline(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Letter_Spacing':
            return self.__executeActionSetTextLetterSpacing(currentAst)
        elif currentAst.id() == 'Action_Set_Text_Stretch':
            return self.__executeActionSetTextStretch(currentAst)
        elif currentAst.id() == 'Action_Set_Text_HAlignment':
            return self.__executeActionSetTextHAlignment(currentAst)
        elif currentAst.id() == 'Action_Set_Text_VAlignment':
            return self.__executeActionSetTextVAlignment(currentAst)
        elif currentAst.id() == 'Action_Set_Draw_Antialiasing':
            return self.__executeActionSetDrawAntialiasing(currentAst)
        elif currentAst.id() == 'Action_Set_Draw_Blending':
            return self.__executeActionSetDrawBlending(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Color':
            return self.__executeActionSetCanvasGridColor(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Style':
            return self.__executeActionSetCanvasGridStyle(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Opacity':
            return self.__executeActionSetCanvasGridOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Size':
            return self.__executeActionSetCanvasGridSize(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Origin_Color':
            return self.__executeActionSetCanvasOriginColor(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Origin_Style':
            return self.__executeActionSetCanvasOriginStyle(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Origin_Opacity':
            return self.__executeActionSetCanvasOriginOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Origin_Size':
            return self.__executeActionSetCanvasOriginSize(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Origin_Position':
            return self.__executeActionSetCanvasOriginPosition(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Position_Color':
            return self.__executeActionSetCanvasPositionColor(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Position_Opacity':
            return self.__executeActionSetCanvasPositionOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Position_Size':
            return self.__executeActionSetCanvasPositionSize(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Position_Fulfill':
            return self.__executeActionSetCanvasPositionFulfill(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_Opacity':
            return self.__executeActionSetCanvasBackgroundOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Script_Execution_Verbose':
            return self.__executeActionSetExecutionVerbose(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Square':
            return self.__executeActionDrawShapeSquare(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Round_Square':
            return self.__executeActionDrawShapeRoundSquare(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Rect':
            return self.__executeActionDrawShapeRect(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Round_Rect':
            return self.__executeActionDrawShapeRoundRect(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Circle':
            return self.__executeActionDrawShapeCircle(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Ellipse':
            return self.__executeActionDrawShapeEllipse(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Dot':
            return self.__executeActionDrawShapeDot(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Pixel':
            return self.__executeActionDrawShapePixel(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Image':
            return self.__executeActionDrawShapeImage(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Scaled_Image':
            return self.__executeActionDrawShapeScaledImage(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Text':
            return self.__executeActionDrawShapeText(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Star':
            return self.__executeActionDrawShapeStar(currentAst)
        elif currentAst.id() == 'Action_Draw_Misc_Clear_Canvas':
            return self.__executeActionDrawMiscClearCanvas(currentAst)
        elif currentAst.id() == 'Action_Draw_Misc_Apply_To_Layer':
            return self.__executeActionDrawMiscApplyToLayer(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Start':
            return self.__executeActionDrawShapeStart(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Stop':
            return self.__executeActionDrawShapeStop(currentAst)
        elif currentAst.id() == 'Action_Draw_Fill_Activate':
            return self.__executeActionDrawFillActivate(currentAst)
        elif currentAst.id() == 'Action_Draw_Fill_Deactivate':
            return self.__executeActionDrawFillDeactivate(currentAst)
        elif currentAst.id() == 'Action_Draw_Pen_Up':
            return self.__executeActionDrawPenUp(currentAst)
        elif currentAst.id() == 'Action_Draw_Pen_Down':
            return self.__executeActionDrawPenDown(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_Home':
            return self.__executeActionDrawMoveHome(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_Forward':
            return self.__executeActionDrawMoveForward(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_Backward':
            return self.__executeActionDrawMoveBackward(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_Left':
            return self.__executeActionDrawMoveLeft(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_Right':
            return self.__executeActionDrawMoveRight(currentAst)
        elif currentAst.id() == 'Action_Draw_Move_To':
            return self.__executeActionDrawMoveTo(currentAst)
        elif currentAst.id() == 'Action_Draw_Turn_Left':
            return self.__executeActionDrawTurnLeft(currentAst)
        elif currentAst.id() == 'Action_Draw_Turn_Right':
            return self.__executeActionDrawTurnRight(currentAst)
        elif currentAst.id() == 'Action_Draw_Turn_To':
            return self.__executeActionDrawTurnTo(currentAst)
        elif currentAst.id() == 'Action_State_Push':
            return self.__executeActionStatePush(currentAst)
        elif currentAst.id() == 'Action_State_Pop':
            return self.__executeActionStatePop(currentAst)
        elif currentAst.id() == 'Action_Canvas_Show_Grid':
            return self.__executeActionCanvasShowGrid(currentAst)
        elif currentAst.id() == 'Action_Canvas_Show_Origin':
            return self.__executeActionCanvasShowOrigin(currentAst)
        elif currentAst.id() == 'Action_Canvas_Show_Position':
            return self.__executeActionCanvasShowPosition(currentAst)
        elif currentAst.id() == 'Action_Canvas_Show_Background':
            return self.__executeActionCanvasShowBackground(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Grid':
            return self.__executeActionCanvasHideGrid(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Origin':
            return self.__executeActionCanvasHideOrigin(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Position':
            return self.__executeActionCanvasHidePosition(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Background':
            return self.__executeActionCanvasHideBackground(currentAst)
        elif currentAst.id() == 'Action_UIConsole_Print':
            return self.__executeActionUIConsolePrint(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Message':
            return self.__executeActionUIDialogMessage(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Boolean_Input':
            return self.__executeActionUIDialogBooleanInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_String_Input':
            return self.__executeActionUIDialogStringInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Integer_Input':
            return self.__executeActionUIDialogIntegerInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Decimal_Input':
            return self.__executeActionUIDialogDecimalInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Color_Input':
            return self.__executeActionUIDialogColorInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Single_Choice_Input':
            return self.__executeActionUIDialogSingleChoiceInput(currentAst)
        elif currentAst.id() == 'Action_UIDialog_Multiple_Choice_Input':
            return self.__executeActionUIDialogMultipleChoiceInput(currentAst)

        # ----------------------------------------------------------------------
        # Function & Evaluation
        # ---------------------
        elif currentAst.id() == 'Function':
            return self.__executeFunction(currentAst)
        elif currentAst.id() == 'Evaluation_Expression_Parenthesis':
            return self.__executeEvaluationExpressionParenthesis(currentAst)
        elif currentAst.id() == 'String_Value':
            return self.__executeStringValue(currentAst)
        elif currentAst.id() == 'List_Value':
            return self.__executeListValue(currentAst)

        # ----------------------------------------------------------------------
        # Operators
        # ---------
        elif currentAst.id() == ASTSpecialItemType.UNARY_OPERATOR:
            return self.__executeUnaryOperator(currentAst)
        elif currentAst.id() == ASTSpecialItemType.BINARY_OPERATOR:
            return self.__executeBinaryOperator(currentAst)

        # ----------------------------------------------------------------------
        # Forgotten to implement something?
        # ---------------------------------
        else:
            print('************************************************************* TODO: implement', currentAst.id())
            return None

    def __executeScriptBlock(self, currentAst, allowLocalVariable, name, createLocalVariables=None):
        """Execute a script block

        Each script block:
        - is defined by a UUID
        - keep is own local variables
        - can access to parent variables


        If `createLocalVariables` is provided, must be a <dict>
        In this case, local variables from dict will be created for current AST

        """
        returned=None

        self.__verbose(f"Enter scriptblock: '{name}'", currentAst)
        self.__scriptBlockStack.push(currentAst, allowLocalVariable, name)

        scriptBlock=self.__scriptBlockStack.current()

        if isinstance(createLocalVariables, dict):
            # create local variables if any provided before starting block execution
            for variableName in createLocalVariables:
                scriptBlock.setVariable(variableName, createLocalVariables[variableName], True, True)

        for ast in currentAst.nodes():
            # execute all instructions from current script block
            if currentAst.id()==ASTSpecialItemType.ROOT and ast.id()=='ScriptBlock':
                # we are in a special case, still in main script block
                for subAst in ast.nodes():
                    self.__executeAst(subAst)
            else:
                returned=self.__executeAst(ast)

            if not returned is None:
                # when a value is returned, that's a RETURN flow
                break

        #Debug.print("Variables: {0}", scriptBlock.variables(True))
        self.__scriptBlockStack.pop()
        self.__verbose(f"Exit scriptblock: '{name}'", currentAst)

        return returned


    # --------------------------------------------------------------------------
    # Flows
    # --------------------------------------------------------------------------
    def __executeFlowSetVariable(self, currentAst):
        """Set a variable in current script block"""
        scriptBlock=self.__scriptBlockStack.current()

        # Defined by 2 nodes:
        #   0: variable name (<Token>)
        #   1: variable value (<Token> or <ASTItem>)
        variableName=currentAst.node(0).value()
        variableValue=self.__evaluate(currentAst.node(1))

        self.__verbose(f"set variable {variableName}={self.__strValue(variableValue)}", currentAst)

        scriptBlock.setVariable(variableName, variableValue, True)

        self.__delay()
        return None

    def __executeFlowDefineMacro(self, currentAst):
        """Define a macro"""
        # defined by N nodes:
        #   0:      macro name (<ASTitem> => String_Value)
        #   N-n:    variable name (<Token> => VARIABLE_USER)
        #   N-2:    variable name (<Token> => VARIABLE_USER)
        #   N-1:    scriptblock (<ASTItem> => ScriptBlock)
        sourceFile=''
        macroName=''
        variables=[]
        scriptBlock=None

        for index, item in enumerate(currentAst.nodes()):
            if index==0:
                macroName=self.__evaluate(item)
            elif isinstance(item, Token):
                variables.append(item.value())
            else:
                scriptBlock=item

        if macroName is None:
            # should not occurs, but...
            macroName='None'

        if len(variables)==0:
            self.__verbose(f"Define macro '{macroName}'", currentAst)
        else:
            self.__verbose(f"Define macro '{macroName}' with parameters {' '.join(variables)}", currentAst)

        if self.__macroDefinitions.alreadyDefined(macroName):
            self.__warning(f"Macro with name '{macroName}' has been overrided", self.__macroDefinitions.get(macroName).ast())

        self.__macroDefinitions.add(BSScriptBlockMacro(sourceFile, macroName, scriptBlock, *variables))

        #self.__delay()
        return None

    def __executeFlowStopScript(self, currentAst):
        """stop script

        Stop script execution
        """
        raise EInterpreter("Explicit call to stop script", currentAst, EInterpreter.ERROR_LEVEL_STOP)

    def __executeFlowCallMacro(self, currentAst):
        """call macro

        Call defined and execute it
        """
        fctLabel='Flow `call macro`'

        if len(currentAst.nodes())<1:
            # at least, must have one parameter (macro name to call)
            self.__checkParamNumber(currentAst, fctLabel, 1)

        macroName=None
        variablesAsParameter=[]
        storeResultName=None
        storeResultValue=None
        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                macroName=self.__evaluate(node)
            elif isinstance(node, ASTItem) and node.id()=='Flow_Call_Macro__storeResult':
                # <ASTItem(Flow_Call_Macro__storeResult>
                #       <Token(ITokenType.VARIABLE_USER, `:v1`)>
                storeResultName=node.nodes()[0].value()
            else:
                variablesAsParameter.append(self.__evaluate(node))


        self.__checkParamType(currentAst, fctLabel, '<MACRO>', macroName, str)

        macroDefinition=self.__macroDefinitions.get(macroName)
        self.__checkParamDomain(currentAst, fctLabel, '<MACRO>', not macroDefinition is None, f"no macro matching given name '{macroName}' found")

        nbExpectedArgs=len(macroDefinition.argumentsName())
        nbProvidedArgs=len(variablesAsParameter)

        if nbExpectedArgs!=nbProvidedArgs:
            raise EInterpreter(f"{fctLabel}: number of provided parameters ({nbProvidedArgs}) do not match expected number of parameters ({nbExpectedArgs}) for macro '{macroName}'", currentAst)

        localVariables={}
        for index, argName in enumerate(macroDefinition.argumentsName()):
            # build a dictionnary to match variable name with given values
            localVariables[argName]=variablesAsParameter[index]

        #self.__delay()
        verboseText=f"call macro '{macroName}' "
        if len(localVariables)>0:
            verboseText+="with parameters"+' '.join([f'{key}={localVariables[key]}' for key in localVariables])+' '
        if not storeResultName is None:
            verboseText+='and store result into variable '+storeResultName
        self.__verbose(verboseText, currentAst)

        storeResultValue=self.__executeScriptBlock(macroDefinition.ast(), True, f"Macro: {macroName}", localVariables)

        if isinstance(storeResultName, str):
            self.__scriptBlockStack.current().setVariable(storeResultName, storeResultValue, True)

        return storeResultValue

    def __executeFlowReturn(self, currentAst):
        """return

        Return given value or False if no value is provided
        """
        fctLabel='Flow `return`'
        self.__checkParamNumber(currentAst, fctLabel, 0, 1)

        returned=False

        if len(currentAst.nodes())>0:
            returned=self.__evaluate(currentAst.node(0))

        self.__verbose(f"return {self.__strValue(returned)}", currentAst)

        #self.__delay()
        return returned

    def __executeFlowIfElseIf(self, currentAst, mode='if'):
        """if <condition> then

        Execute a scriptblock if condition is met
        """
        fctLabel='Flow `if ... then`'

        # 1st parameter: condition
        # 2nd parameter: scriptblock to execute
        # 3rd parameter: Else/ElseIf
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        condition=self.__evaluate(currentAst.node(0))

        if isinstance(condition, (int, float)):
            # when condition is a number value, consider 0 value as FALSE and other as TRUE
            condition=(condition!=0)
        elif isinstance(condition, str):
            # when condition is a string value, consider empty string value as FALSE and non empty string as TRUE
            condition=(condition!='')
        elif isinstance(condition, list):
            # when condition is a list value, consider empty list value as FALSE and non empty list as TRUE
            condition=(len(condition)>0)
        elif isinstance(condition, QColor):
            # when condition is a color value, consider black color value as FALSE and any other color as TRUE
            condition=condition!=QColor(Qt.black)
        elif not isinstance(condition, bool):
            # when condition is not a boolean (can occurs?), condition is False
            condition=False

        astScriptBlock=None
        execFct=None

        if condition==True:
            verboseText=f'{mode} (condition validated) then ...'
            astBlockName=f'{mode} (ON) then (Execute statement)'
            astScriptBlock=currentAst.node(1)
            execFct='__executeScriptBlock'
        elif len(currentAst.nodes())==3:
            # else or else if
            astScriptBlock=currentAst.node(2)
            if astScriptBlock.id()=='Flow_ElseIf':
                verboseText=f'{mode} (condition not validated) then ... else if (...)'
                astBlockName=f'{mode} (OFF) then ... elseif (...)'
                execFct='__executeFlowIfElseIf'
            else:
                verboseText=f'{mode} (condition not validated) then ... else'
                astBlockName=f'{mode} (OFF) then ... else '
                execFct='__executeFlowElse'
        else:
            verboseText=f'{mode} (condition not validated) then ...'

        self.__verbose(verboseText, currentAst)

        if execFct=='__executeScriptBlock':
            self.__executeScriptBlock(astScriptBlock, False, astBlockName)
        elif execFct=='__executeFlowIfElseIf':
            self.__executeFlowIfElseIf(astScriptBlock, 'else if')
        elif execFct=='__executeFlowElse':
            self.__executeFlowElse(astScriptBlock)


        #self.__delay()
        return None

    def __executeFlowElse(self, currentAst):
        """... else ...

        Execute a scriptblock
        """
        fctLabel='Flow `else ...`'

        # 1st parameter: scriptblock to execute
        self.__checkParamNumber(currentAst, fctLabel, 1)

        self.__verbose('else ...', currentAst)
        self.__executeScriptBlock(currentAst.node(0), False, 'else')

        #self.__delay()
        return None

    def __executeFlowRepeat(self, currentAst):
        """repeat <COUNT> times

        Execute a repeat loop
        """
        fctLabel='Flow `repeat <COUNT> times`'

        # 1st parameter: number of repetition
        # 2nd parameter: scriptblock to execute
        self.__checkParamNumber(currentAst, fctLabel, 2)

        repeatTotal=self.__evaluate(currentAst.node(0))
        astScriptBlock=currentAst.node(1)

        if isinstance(repeatTotal, float):
            asInt=round(repeatTotal)
            if asInt==repeatTotal:
                # a float value without decimals (4.0 for exsample => convert to <int>)
                repeatTotal=asInt

        self.__checkParamType(currentAst, fctLabel, '<COUNT>', repeatTotal, int)

        if not self.__checkParamDomain(currentAst, fctLabel, '<COUNT>', repeatTotal>=0, f"Can't repeat negative value (count={repeatTotal})", False):
            return None

        scriptBlockName=f'repeat {repeatTotal} times'

        # define loop variable
        if repeatTotal>0:
            repeatIncAngle=360/repeatTotal
        else:
            repeatIncAngle=0

        repeatCurrentAngle=0
        for repeatCurrent in range(repeatTotal):
            loopVariables={
                    ':repeat.total': repeatTotal,
                    ':repeat.current': repeatCurrent+1,
                    ':repeat.first': (repeatCurrent==0),
                    ':repeat.last': (repeatCurrent==repeatTotal-1),
                    ':repeat.incAngle': repeatIncAngle,
                    ':repeat.currentAngle': repeatCurrentAngle
                }

            self.__executeScriptBlock(astScriptBlock, False, scriptBlockName, loopVariables)

            repeatCurrentAngle+=repeatIncAngle

        return None

    def __executeFlowForEach(self, currentAst):
        """for each <variable> in <list>

        Do llop over items in list
        """
        fctLabel='Flow `for each ... in ...`'

        # 1st parameter: target variable
        # 2nd parameter: source list
        # 3rd parameter: scriptblock to execute
        self.__checkParamNumber(currentAst, fctLabel, 3)

        forVarName=currentAst.node(0).value()
        forEachList=self.__evaluate(currentAst.node(1))
        astScriptBlock=currentAst.node(2)


        self.__checkParamType(currentAst, fctLabel, '<LIST>', forEachList, list, str)

        if isinstance(forEachList, str):
            forEachList=[c for c in forEachList]

        if len(forEachList)>5:
            scriptBlockName=f'for {forVarName} in {forEachList[0:5]}'.replace(']', ', ...]')
        else:
            scriptBlockName=f'for {forVarName} in {forEachList}'

        # define loop variable
        forEachTotal=len(forEachList)
        if forEachTotal>0:
            forEachIncAngle=360/forEachTotal
        else:
            forEachIncAngle=0

        forEachCurrentAngle=0
        for index, forEachCurrentValue in enumerate(forEachList):
            loopVariables={
                    ':foreach.total': forEachTotal,
                    ':foreach.current': index+1,
                    ':foreach.first': (index==0),
                    ':foreach.last': (index==forEachTotal-1),
                    ':foreach.incAngle': forEachIncAngle,
                    ':foreach.currentAngle': forEachCurrentAngle,
                    forVarName: forEachCurrentValue
                }

            self.__executeScriptBlock(astScriptBlock, False, scriptBlockName, loopVariables)

            forEachCurrentAngle+=forEachIncAngle

        return None



    # --------------------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------------------
    # Set
    # ---
    def __executeActionSetUnitCanvas(self, currentAst):
        """Set canvas unit

        :unit.canvas
        """
        fctLabel='Action `set unit canvas`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', value in BSInterpreter.CONST_MEASURE_UNIT, f"coordinates & measures unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"set unit canvas {self.__strValue(value)}      => :unit.canvas", currentAst)

        self.__scriptBlockStack.current().setVariable(':unit.canvas', value, True)

        self.__delay()
        return None

    def __executeActionSetUnitRotation(self, currentAst):
        """Set canvas unit

        :unit.rotation
        """
        fctLabel='Action `set unit rotation`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', value in BSInterpreter.CONST_ROTATION_UNIT, f"angle unit value for rotation can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.__verbose(f"set unit rotation {self.__strValue(value)}      => :unit.rotation", currentAst)

        self.__scriptBlockStack.current().setVariable(':unit.rotation', value, True)

        self.__delay()
        return None

    def __executeActionSetPenColor(self, currentAst):
        """Set pen color

        :pen.color
        """
        fctLabel='Action `set pen color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set pen color {self.__strValue(value)}      => :pen.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.color', value, True)

        self.__delay()
        return None

    def __executeActionSetPenSize(self, currentAst):
        """Set pen size

        :pen.size
        """
        fctLabel='Action `set pen size`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, '<SIZE>', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<SIZE>', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.__verbose(f"set pen size {self.__strValue(value)} {self.__strValue(unit)}     => :pen.size", currentAst)
        else:
            self.__verbose(f"set pen size {self.__strValue(value)}      => :pen.size", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.size', value, True)

        self.__delay()
        return None

    def __executeActionSetPenStyle(self, currentAst):
        """Set pen style

        :pen.style
        """
        fctLabel='Action `set pen style`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<STYLE>', value in BSInterpreter.CONST_PEN_STYLE, f"style value for pen can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.__verbose(f"set pen style {self.__strValue(value)}      => :pen.style", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.style', value, True)

        self.__delay()
        return None

    def __executeActionSetPenCap(self, currentAst):
        """Set pen cap

        :pen.cap
        """
        fctLabel='Action `set pen cap`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<CAP>', value in BSInterpreter.CONST_PEN_CAP, f"cap value for pen can be: {', '.join(BSInterpreter.CONST_PEN_CAP)}")

        self.__verbose(f"set pen cap {self.__strValue(value)}      => :pen.cap", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.cap', value, True)

        self.__delay()
        return None

    def __executeActionSetPenJoin(self, currentAst):
        """Set pen join

        :pen.join
        """
        fctLabel='Action `set pen join`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<JOIN>', value in BSInterpreter.CONST_PEN_JOIN, f"join value for pen can be: {', '.join(BSInterpreter.CONST_PEN_JOIN)}")

        self.__verbose(f"set pen join {self.__strValue(value)}      => :pen.join", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.join', value, True)

        self.__delay()
        return None

    def __executeActionSetPenOpacity(self, currentAst):
        """Set pen opacity

        :pen.color
        """
        fctLabel='Action `set pen opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set pen opacity {self.__strValue(value)}      => :pen.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':pen.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':pen.color', color, True)

        self.__delay()
        return None

    def __executeActionSetFillColor(self, currentAst):
        """Set fill color

        :fill.color
        """
        fctLabel='Action `set fill color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set fill color {self.__strValue(value)}      => :fill.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':fill.color', value, True)

        self.__delay()
        return None

    def __executeActionSetFillRule(self, currentAst):
        """Set fill rule

        :fill.rule
        """
        fctLabel='Action `set fill rule`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<RULE>', value in BSInterpreter.CONST_FILL_RULE, f"rule value for fill can be: {', '.join(BSInterpreter.CONST_FILL_RULE)}")

        self.__verbose(f"set fill rule {self.__strValue(value)}      => :fill.rule", currentAst)

        self.__scriptBlockStack.current().setVariable(':fill.rule', value, True)

        self.__delay()
        return None

    def __executeActionSetFillOpacity(self, currentAst):
        """Set fill opacity

        :fill.color
        """
        fctLabel='Action `set fill opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set fill opacity {self.__strValue(value)}      => :fill.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':fill.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':fill.color', color, True)

        self.__delay()
        return None

    def __executeActionSetTextColor(self, currentAst):
        """Set text color

        :text.color
        """
        fctLabel='Action `set text color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set text color {self.__strValue(value)}      => :text.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.color', value, True)

        self.__delay()
        return None

    def __executeActionSetTextOpacity(self, currentAst):
        """Set text opacity

        :text.color
        """
        fctLabel='Action `set text opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set text opacity {self.__strValue(value)}      => :text.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':text.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':text.color', color, True)

        self.__delay()
        return None

    def __executeActionSetTextFont(self, currentAst):
        """Set text font

        :text.font
        """
        fctLabel='Action `set text font`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<FONT>', value, str)

        self.__verbose(f"set text font {self.__strValue(value)}      => :text.font", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.font', value, True)

        self.__delay()
        return None

    def __executeActionSetTextSize(self, currentAst):
        """Set text size

        :text.size
        """
        fctLabel='Action `set text size`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, '<SIZE>', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<SIZE>', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.__verbose(f"set text size {self.__strValue(value)} {self.__strValue(unit)}     => :text.size", currentAst)
        else:
            self.__verbose(f"set text size {self.__strValue(value)}      => :text.size", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.size', value, True)

        self.__delay()
        return None

    def __executeActionSetTextBold(self, currentAst):
        """Set text bold

        :text.bold
        """
        fctLabel='Action `set text bold`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set text bold {self.__strValue(value)}      => :text.bold", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.bold', value, True)

        self.__delay()
        return None

    def __executeActionSetTextItalic(self, currentAst):
        """Set text italic

        :text.italic
        """
        fctLabel='Action `set text italic`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set text italic {self.__strValue(value)}      => :text.italic", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.italic', value, True)

        self.__delay()
        return None

    def __executeActionSetTextOutline(self, currentAst):
        """Set text outline

        :text.outline
        """
        fctLabel='Action `set text outline`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set text outline {self.__strValue(value)}      => :text.outline", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.outline', value, True)

        self.__delay()
        return None

    def __executeActionSetTextLetterSpacing(self, currentAst):
        """Set text letter spacing

        :text.letterSpacing.spacing
        :text.letterSpacing.unit
        """
        fctLabel='Action `set text letter spacing`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<SPACING>', value, int, float)

        if unit=='PCT':
            # in this case, relative to text letter spacing base (not document dimension)
            if not self.__checkParamDomain(currentAst, fctLabel, '<SPACING>', value>0, f"a non-zero positive number is expected when expressed in percentage (current={value})", False):
                # if value<=0, force to 0.1 (non blocking)
                value=max(1, value)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"letter spacing unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__verbose(f"set text letter spacing {self.__strValue(value)} {self.__strValue(unit)}     => :text.letterSpacing.spacing, text.letterSpacing.unit ", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.letterspacing.spacing', value, True)
        self.__scriptBlockStack.current().setVariable(':text.letterspacing.unit', unit, True)

        self.__delay()
        return None

    def __executeActionSetTextStretch(self, currentAst):
        """Set text stretch

        :text.stretch
        """
        fctLabel='Action `set text stretch`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<STRETCH>', value, int, float)

        if isinstance(value, int):
            # from 1 to 4000
            if not self.__checkParamDomain(currentAst, fctLabel, '<STRETCH>', value>0 and value<=4000, f"allowed stretch value when provided as an integer number is range [1;4000] (current={value})", False):
                value=min(4000, max(1, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<STRETCH>', value>0 and value<=40, f"allowed stretch value when provided as a decimal number is range [0.01;40] (current={value})", False):
                value=min(40.0, max(1.0, value))
            value=round(value*100)

        self.__scriptBlockStack.current().setVariable(':text.stretch', value, True)

        self.__delay()
        return None

    def __executeActionSetTextHAlignment(self, currentAst):
        """Set text horizontal alignment

        :text.alignment.horizontal
        """
        fctLabel='Action `set text horizontal alignment`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<H-ALIGNMENT>', value in BSInterpreter.CONST_HALIGN, f"text horizontal alignment value can be: {', '.join(BSInterpreter.CONST_HALIGN)}")

        self.__verbose(f"set text horizontal alignment {self.__strValue(value)}      => :text.alignment.horizontal", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.alignment.horizontal', value, True)

        self.__delay()
        return None

    def __executeActionSetTextVAlignment(self, currentAst):
        """Set text vertical alignment

        :text.alignment.vertical
        """
        fctLabel='Action `set text vertical alignment`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<V-ALIGNMENT>', value in BSInterpreter.CONST_VALIGN, f"text vertical alignment value can be: {', '.join(BSInterpreter.CONST_VALIGN)}")

        self.__verbose(f"set text vertical alignment {self.__strValue(value)}      => :text.alignment.vertical", currentAst)

        self.__scriptBlockStack.current().setVariable(':text.alignment.vertical', value, True)

        self.__delay()
        return None

    def __executeActionSetDrawAntialiasing(self, currentAst):
        """Set draw antialiasing

        :draw.antialiasing
        """
        fctLabel='Action `set draw antialiasing`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set draw antialiasing {self.__strValue(value)}      => :draw.antialiasing", currentAst)

        self.__scriptBlockStack.current().setVariable(':draw.antialiasing', value, True)

        self.__delay()
        return None

    def __executeActionSetDrawBlending(self, currentAst):
        """Set draw blending mode

        :draw.blendingMode
        """
        fctLabel='Action `set draw blending mode`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<BLENDING-MODE>', value in BSInterpreter.CONST_DRAW_BLENDING_MODE, f"blending mode value can be: {', '.join(BSInterpreter.CONST_DRAW_BLENDING_MODE)}")

        self.__verbose(f"set draw blending mode {self.__strValue(value)}      => :draw.blendingMode", currentAst)

        self.__scriptBlockStack.current().setVariable(':draw.blendingmode', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasGridColor(self, currentAst):
        """Set canvas grid color

        :canvas.grid.color
        """
        fctLabel='Action `set canvas grid color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set canvas grid color {self.__strValue(value)}      => :canvas.grid.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.grid.color', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasGridStyle(self, currentAst):
        """Set canvas grid style

        :canvas.grid.style
        """
        fctLabel='Action `set canvas grid style`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<STYLE>', value in BSInterpreter.CONST_PEN_STYLE, f"style value for grid can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.__verbose(f"set canvas grid style {self.__strValue(value)}      => :canvas.grid.style", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.grid.style', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasGridOpacity(self, currentAst):
        """Set canvas grid opacity

        :canvas.grid.color
        """
        fctLabel='Action `set canvas grid opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set canvas grid opacity {self.__strValue(value)}      => :canvas.grid.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':canvas.grid.color', QColor(60,60,128))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':canvas.grid.color', color, True)

        self.__delay()
        return None

    def __executeActionSetCanvasGridSize(self, currentAst):
        """Set canvas grid size

        :canvas.grid.size.major
        :canvas.grid.size.minor
        :canvas.grid.size.unit
        """
        fctLabel='Action `set canvas grid size`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2, 3)

        major=self.__evaluate(currentAst.node(0))
        p2=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))

        if p2 is None and p3 is None:
            # no other parameters provided, set default value
            minor=self.__scriptBlockStack.current().variable(':canvas.grid.size.minor', 0)
            unit=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
        elif p3 is None:
            # p2 has been provided
            if isinstance(p2, (int, float)):
                minor=p2
                unit=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            else:
                minor=self.__scriptBlockStack.current().variable(':canvas.grid.size.minor', 0)
                unit=p2
        else:
            # p2+p3 provided
            minor=p2
            unit=p3

        self.__checkParamType(currentAst, fctLabel, '<MAJOR>', major, int, float)
        self.__checkParamType(currentAst, fctLabel, '<MINOR>', minor, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, '<MAJOR>', major>0, f"a positive number is expected (current={major})", False):
            # let default value being applied in this case
            major=self.__scriptBlockStack.current().variable(':canvas.grid.size.major', major, True)

        if not self.__checkParamDomain(currentAst, fctLabel, '<MINOR>', minor>=0, f"a zero or positive number is expected (current={minor})", False):
            # let default value being applied in this case
            minor=self.__scriptBlockStack.current().variable(':canvas.grid.size.minor', minor, True)

        if not self.__checkParamDomain(currentAst, fctLabel, '<MINOR>', minor<major, f"size for minor grid must be lower than major grid size (current={minor}>{major})", False):
            # force minor grid to be lower than major grid
            minor=major/2

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"grid unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"set canvas grid size {self.__strValue(major)} {self.__strValue(minor)} {self.__strValue(unit)}     => :canvas.grid.size.major, :canvas.grid.size.minor, :canvas.grid.size.unit", currentAst)


        self.__scriptBlockStack.current().setVariable(':canvas.grid.size.major', major, True)
        self.__scriptBlockStack.current().setVariable(':canvas.grid.size.minor', minor, True)
        self.__scriptBlockStack.current().setVariable(':canvas.grid.size.unit', unit, True)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginColor(self, currentAst):
        """Set canvas origin color

        :canvas.origin.color
        """
        fctLabel='Action `set canvas origin color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set canvas origin color {self.__strValue(value)}      => :canvas.origin.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.color', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginStyle(self, currentAst):
        """Set canvas origin style

        :canvas.origin.style
        """
        fctLabel='Action `set canvas origin style`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<STYLE>', value in BSInterpreter.CONST_PEN_STYLE, f"style value for origin can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.__verbose(f"set canvas origin style {self.__strValue(value)}      => :canvas.origin.style", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.style', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginOpacity(self, currentAst):
        """Set canvas origin opacity

        :canvas.origin.color
        """
        fctLabel='Action `set canvas origin opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set canvas origin opacity {self.__strValue(value)}      => :canvas.origin.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':canvas.origin.color', QColor(60,60,128))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.color', color, True)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginSize(self, currentAst):
        """Set canvas origin size

        :canvas.origin.size
        """
        fctLabel='Action `set canvas origin size`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, '<SIZE>', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<SIZE>', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.__verbose(f"set canvas origin size {self.__strValue(value)} {self.__strValue(unit)}     => :canvas.origin.size", currentAst)
        else:
            self.__verbose(f"set canvas origin size {self.__strValue(value)}      => :canvas.origin.size", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.size', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginPosition(self, currentAst):
        """Set canvas origin position

        :canvas.origin.position.absissa
        :canvas.origin.position.ordinate
        """
        fctLabel='Action `set canvas origin position`'
        self.__checkParamNumber(currentAst, fctLabel, 2)

        absissa=self.__evaluate(currentAst.node(0))
        ordinate=self.__evaluate(currentAst.node(1))

        self.__checkParamDomain(currentAst, fctLabel, '<ABSISSA>', absissa in BSInterpreter.CONST_HALIGN, f"absissa position value can be: {', '.join(BSInterpreter.CONST_HALIGN)}")
        self.__checkParamDomain(currentAst, fctLabel, '<ORDINATE>', ordinate in BSInterpreter.CONST_VALIGN, f"ordinate position value can be: {', '.join(BSInterpreter.CONST_VALIGN)}")

        self.__verbose(f"set canvas origin position {self.__strValue(absissa)} {self.__strValue(ordinate)}     => :canvas.origin.position.absissa, canvas.origin.position.ordinate", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.position.absissa', absissa, True)
        self.__scriptBlockStack.current().setVariable(':canvas.origin.position.ordinate', ordinate, True)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionColor(self, currentAst):
        """Set canvas position color

        :canvas.position.color
        """
        fctLabel='Action `set canvas position color`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<COLOR>', value, QColor)

        self.__verbose(f"set canvas position color {self.__strValue(value)}      => :canvas.position.color", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.position.color', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionOpacity(self, currentAst):
        """Set canvas position opacity

        :canvas.position.color
        """
        fctLabel='Action `set canvas position opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set canvas position opacity {self.__strValue(value)}      => :canvas.position.color", currentAst)

        color=self.__scriptBlockStack.current().variable(':canvas.position.color', QColor(60,60,128))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.current().setVariable(':canvas.position.color', color, True)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionSize(self, currentAst):
        """Set canvas position size

        :canvas.position.size
        """
        fctLabel='Action `set canvas position size`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, '<SIZE>', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<SIZE>', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.__verbose(f"set canvas position size {self.__strValue(value)} {self.__strValue(unit)}     => :canvas.position.size", currentAst)
        else:
            self.__verbose(f"set canvas position size {self.__strValue(value)}      => :canvas.position.size", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.position.size', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionFulfill(self, currentAst):
        """Set canvas position fulfilled

        :canvas.position.fulfill
        """
        fctLabel='Action `set canvas position fulfilled`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set canvas position fulfilled {self.__strValue(value)}      => :canvas.position.fulfill", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.position.fulfill', value, True)

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundOpacity(self, currentAst):
        """Set canvas background opacity

        :canvas.background.opacity
        """
        fctLabel='Action `set canvas background opacity`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<OPACITY>', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
            value/=255
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, '<OPACITY>', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.__verbose(f"set canvas background opacity {self.__strValue(value)}      => :canvas.background.opacity", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.background.opacity', value, True)

        self.__delay()
        return None

    def __executeActionSetExecutionVerbose(self, currentAst):
        """Set execution verbose

        :script.execution.verbose
        """
        fctLabel='Action `set execution verbose`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<SWITCH>', value, bool)

        self.__verbose(f"set execution verbose {self.__strValue(value)}      => :script.execution.verbose", currentAst)

        self.__scriptBlockStack.current().setVariable(':script.execution.verbose', value, True)
        self.__optionVerboseMode=value

        self.__delay()
        return None

    # Draw
    # ----
    def __executeActionDrawShapeSquare(self, currentAst):
        """Draw square"""
        fctLabel='Action `draw square`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        width=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<WIDTH>', width, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<WIDTH>', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.__verbose(f"draw square {self.__strValue(width)} {self.__strValue(unit)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"width unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__verbose(f"draw square {self.__strValue(width)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRoundSquare(self, currentAst):
        """Draw square"""
        fctLabel='Action `draw round square`'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3, 4)

        width=self.__evaluate(currentAst.node(0))
        p2=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))
        p4=self.__evaluate(currentAst.node(3))

        if len(currentAst.nodes())==2:
            # second parameter is radius
            radius=p2
            unitWidth=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            unitRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
        elif len(currentAst.nodes())==3:
            if isinstance(p2, str):
                # second parameter is a string, consider it's a width unit
                radius=p3
                unitWidth=p2
                unitRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            else:
                # second parameter is not a string, consider it's radius
                radius=p2
                unitWidth=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
                unitRadius=p3
        elif len(currentAst.nodes())==4:
            radius=p3
            unitWidth=p2
            unitRadius=p4


        self.__checkParamType(currentAst, fctLabel, '<WIDTH>', width, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<WIDTH>', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.__verbose(f"draw round square {self.__strValue(width)} {self.__strValue(unitWidth)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<W-UNIT>', unitWidth in BSInterpreter.CONST_MEASURE_UNIT, f"width unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__checkParamType(currentAst, fctLabel, '<RADIUS>', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<RADIUS>', radius>=0, f"a zero or positive number is expected (current={radius})", False):
            radius=0

        self.__checkParamDomain(currentAst, fctLabel, '<R-UNIT>', unitRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.__verbose(f"draw round square {self.__strValue(width)} {self.__strValue(unitWidth)} {self.__strValue(radius)} {self.__strValue(unitRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRect(self, currentAst):
        """Draw rect"""
        fctLabel='Action `draw rect`'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        width=self.__evaluate(currentAst.node(0))
        height=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<WIDTH>', width, int, float)
        self.__checkParamType(currentAst, fctLabel, '<HEIGHT>', height, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, '<WIDTH>', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.__verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<HEIGHT>', height>0, f"a positive number is expected (current={height})", False):
            # if value<=0, exit
            self.__verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRoundRect(self, currentAst):
        """Draw square"""
        fctLabel='Action `draw round square`'
        self.__checkParamNumber(currentAst, fctLabel, 3, 4, 5)

        width=self.__evaluate(currentAst.node(0))
        height=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))
        p4=self.__evaluate(currentAst.node(3))
        p5=self.__evaluate(currentAst.node(4))

        if len(currentAst.nodes())==3:
            # third parameter is radius
            radius=p3
            unitDimension=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            unitRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
        elif len(currentAst.nodes())==4:
            if isinstance(p3, str):
                # third parameter is a string, consider it's a dimension unit
                radius=p4
                unitDimension=p3
                unitRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            else:
                # third parameter is not a string, consider it's radius
                radius=p3
                unitDimension=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
                unitRadius=p4
        elif len(currentAst.nodes())==5:
            radius=p4
            unitDimension=p3
            unitRadius=p5


        self.__checkParamType(currentAst, fctLabel, '<WIDTH>', width, int, float)
        self.__checkParamType(currentAst, fctLabel, '<HEIGHT>', height, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, '<WIDTH>', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.__verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<HEIGHT>', height>0, f"a positive number is expected (current={height})", False):
            # if value<=0, exit
            self.__verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<S-UNIT>', unitDimension in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__checkParamType(currentAst, fctLabel, '<RADIUS>', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<RADIUS>', radius>=0, f"a zero or positive number is expected (current={radius})", False):
            radius=0

        self.__checkParamDomain(currentAst, fctLabel, '<R-UNIT>', unitRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.__verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeCircle(self, currentAst):
        """Draw circle"""
        fctLabel='Action `draw circle`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        radius=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<RADIUS>', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, '<RADIUS>', radius>0, f"a positive number is expected (current={radius})", False):
            # if value<=0, exit
            self.__verbose(f"draw circle {self.__strValue(radius)} {self.__strValue(unit)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__verbose(f"draw circle {self.__strValue(radius)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeEllipse(self, currentAst):
        """Draw ellipse"""
        fctLabel='Action `draw ellipse`'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        hRadius=self.__evaluate(currentAst.node(0))
        vRadius=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<H-RADIUS>', hRadius, int, float)
        self.__checkParamType(currentAst, fctLabel, '<V-RADIUS>', vRadius, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, '<H-RADIUS>', hRadius>0, f"a positive number is expected (current={hRadius})", False):
            # if value<=0, exit
            self.__verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<V-RADIUS>', vRadius>0, f"a positive number is expected (current={vRadius})", False):
            # if value<=0, exit
            self.__verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeDot(self, currentAst):
        """Draw dot"""
        fctLabel='Action `draw dot`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"draw dot", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapePixel(self, currentAst):
        """Draw pixel"""
        fctLabel='Action `draw pixel`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"draw pixel", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeImage(self, currentAst):
        """Draw image"""
        fctLabel='Action `draw image`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        fileName=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<IMAGE>', fileName, str)

        # TODO: implement file management
        fileIsValid=True

        if not self.__checkParamDomain(currentAst, fctLabel, '<IMAGE>', fileIsValid, f"image can't be found: {fileName}", False):
            # if value<=0, exit
            self.__verbose(f"draw image {self.__strValue(fileName)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__verbose(f"draw image {self.__strValue(fileName)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeScaledImage(self, currentAst):
        """Draw scaled image"""
        fctLabel='Action `draw scaled image`'
        self.__checkParamNumber(currentAst, fctLabel, 3, 4)

        fileName=self.__evaluate(currentAst.node(0))
        width=self.__evaluate(currentAst.node(1))
        height=self.__evaluate(currentAst.node(2))
        unit=self.__evaluate(currentAst.node(3, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<IMAGE>', fileName, str)
        self.__checkParamType(currentAst, fctLabel, '<WIDTH>', width, int, float)
        self.__checkParamType(currentAst, fctLabel, '<HEIGHT>', height, int, float)

        # TODO: implement file management
        fileIsValid=True

        if not self.__checkParamDomain(currentAst, fctLabel, '<IMAGE>', fileIsValid, f"image can't be found: {fileName}", False):
            # if value<=0, exit
            self.__verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<WIDTH>', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.__verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<HEIGHT>', height>0, f"a positive number is expected (current={height})", False):
            # if value<=0, exit
            self.__verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")


        self.__verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeText(self, currentAst):
        """Draw text"""
        fctLabel='Action `draw text`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<TEXT>', text, str)

        self.__verbose(f"draw text {self.__strValue(text)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeStar(self, currentAst):
        """Draw star"""
        fctLabel='Action `draw star`'
        self.__checkParamNumber(currentAst, fctLabel, 3, 4, 5)

        branches=self.__evaluate(currentAst.node(0))
        oRadius=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))
        p4=self.__evaluate(currentAst.node(3))
        p5=self.__evaluate(currentAst.node(4))

        if len(currentAst.nodes())==3:
            # third parameter is inner radius
            iRadius=p3
            unitORadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            unitIRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
        elif len(currentAst.nodes())==4:
            if isinstance(p3, str):
                # third parameter is a string, consider it's a dimension unit
                iRadius=p4
                unitORadius=p3
                unitIRadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            else:
                # third parameter is not a string, consider it's radius
                iRadius=p3
                unitORadius=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
                unitIRadius=p4
        elif len(currentAst.nodes())==5:
            iRadius=p4
            unitORadius=p3
            unitIRadius=p5

        self.__checkParamType(currentAst, fctLabel, '<BRANCHES>', branches, int)
        self.__checkParamType(currentAst, fctLabel, '<O-RADIUS>', oRadius, int, float)
        self.__checkParamType(currentAst, fctLabel, '<I-RADIUS>', iRadius, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, '<BRANCHES>', branches>=3, f"a positive integer greater or equal than 3 is expected (current={branches})", False):
            # force minimum
            branches=3

        if not self.__checkParamDomain(currentAst, fctLabel, '<O-RADIUS>', oRadius>0, f"a positive number is expected (current={oRadius})", False):
            # if value<=0, exit
            self.__verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, '<I-RADIUS>', iRadius>0, f"a positive number is expected (current={iRadius})", False):
            # if value<=0, exit
            self.__verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, '<OR-UNIT>', unitORadius in BSInterpreter.CONST_MEASURE_UNIT, f"outer radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__checkParamDomain(currentAst, fctLabel, '<IR-UNIT>', unitIRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"inter radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.__verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMiscClearCanvas(self, currentAst):
        """Clear canvas"""
        fctLabel='Action `clear canvas`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"clear canvas", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMiscApplyToLayer(self, currentAst):
        """Apply to layer"""
        fctLabel='Action `apply to layer`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"apply to layer", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeStart(self, currentAst):
        """Start to draw shape

        :draw.shape.status
        """
        fctLabel='Action `start to draw shape`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"start to draw shape", currentAst)

        self.__scriptBlockStack.current().setVariable(':draw.shape.status', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeStop(self, currentAst):
        """Stop to draw shape

        :draw.shape.status
        """
        fctLabel='Action `stop to draw shape`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"stop to draw shape", currentAst)

        self.__scriptBlockStack.current().setVariable(':draw.shape.status', False, True)
        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawFillActivate(self, currentAst):
        """Activate fill mode

        :fill.status
        """
        fctLabel='Action `activate fill`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"activate fill", currentAst)

        self.__scriptBlockStack.current().setVariable(':fill.status', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawFillDeactivate(self, currentAst):
        """Deactivate fill mode

        :fill.status
        """
        fctLabel='Action `deactivate fill`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"deactivate fill", currentAst)

        self.__scriptBlockStack.current().setVariable(':fill.status', False, True)
        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawPenUp(self, currentAst):
        """Pen up

        :pen.status
        """
        fctLabel='Action `pen up`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"pen up", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.status', False, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawPenDown(self, currentAst):
        """Pen down

        :pen.status
        """
        fctLabel='Action `pen down`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"pen down", currentAst)

        self.__scriptBlockStack.current().setVariable(':pen.status', True, True)
        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveHome(self, currentAst):
        """Move home"""
        fctLabel='Action `move home`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"move home", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveForward(self, currentAst):
        """Move forward"""
        fctLabel='Action `move forward`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"move forward {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveBackward(self, currentAst):
        """Move backward"""
        fctLabel='Action `move backward`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"move backward {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveLeft(self, currentAst):
        """Move left"""
        fctLabel='Action `move left`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"move left {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveRight(self, currentAst):
        """Move right"""
        fctLabel='Action `move right`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"move right {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveTo(self, currentAst):
        """Move to"""
        fctLabel='Action `move to`'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        valueX=self.__evaluate(currentAst.node(0))
        valueY=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, '<X>', valueX, int, float)
        self.__checkParamType(currentAst, fctLabel, '<Y>', valueY, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"move to {self.__strValue(valueX)} {self.__strValue(valueY)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnLeft(self, currentAst):
        """Turn left"""
        fctLabel='Action `turn left`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.__verbose(f"turn left {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnRight(self, currentAst):
        """Turn right"""
        fctLabel='Action `turn right`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.__verbose(f"turn right {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnTo(self, currentAst):
        """Turn to"""
        fctLabel='Action `turn to`'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.__verbose(f"turn to {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionStatePush(self, currentAst):
        """Push state"""
        fctLabel='Action `push state`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"push state", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionStatePop(self, currentAst):
        """Push state"""
        fctLabel='Action `pop state`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"pop state", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasShowGrid(self, currentAst):
        """Show canvas grid

        :canvas.grid.visibility
        """
        fctLabel='Action `show canvas grid`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"show canvas grid", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.grid.visibility', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasHideGrid(self, currentAst):
        """Hide canvas grid

        :canvas.grid.visibility
        """
        fctLabel='Action `hide canvas grid`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"hide canvas grid", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.grid.visibility', False, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasShowOrigin(self, currentAst):
        """Show canvas origin

        :canvas.origin.visibility
        """
        fctLabel='Action `show canvas origin`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"show canvas origin", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.visibility', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasHideOrigin(self, currentAst):
        """Hide canvas origin

        :canvas.origin.visibility
        """
        fctLabel='Action `hide canvas origin`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"hide canvas origin", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.origin.visibility', False, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasShowPosition(self, currentAst):
        """Show canvas position

        :canvas.position.visibility
        """
        fctLabel='Action `show canvas position`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"show canvas position", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.position.visibility', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasHidePosition(self, currentAst):
        """Hide canvas position

        :canvas.position.visibility
        """
        fctLabel='Action `hide canvas position`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"hide canvas position", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.position.visibility', False, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasShowBackground(self, currentAst):
        """Show canvas background

        :canvas.background.visibility
        """
        fctLabel='Action `show canvas background`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"show canvas background", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.background.visibility', True, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasHideBackground(self, currentAst):
        """Hide canvas background

        :canvas.background.visibility
        """
        fctLabel='Action `hide canvas background`'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.__verbose(f"hide canvas background", currentAst)

        self.__scriptBlockStack.current().setVariable(':canvas.background.visibility', False, True)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionUIConsolePrint(self, currentAst):
        """Print"""
        fctLabel='Action `print`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        printed=[]
        for node in currentAst.nodes():
            printed.append(str(self.__strValue(self.__evaluate(node))))

        self.__print(' '.join(printed))

        #self.__delay()
        return None

    def __executeActionUIDialogOptionWithMessage(self, currentAst):
        """with message

        Return optional message for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with message`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<TEXT>', text, str)

        return text

    def __executeActionUIDialogOptionWithTitle(self, currentAst):
        """with title

        Return optional title for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with title`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<TEXT>', text, str)

        return text

    def __executeActionUIDialogOptionWithDefaultValue(self, currentAst, type):
        """with default value

        Return optional default for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with default value`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, type)

        return value

    def __executeActionUIDialogOptionWithMinimumValue(self, currentAst, type):
        """with minimum value

        Return optional minimum value for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with minimum value`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, type)

        return value

    def __executeActionUIDialogOptionWithMaximumValue(self, currentAst, type):
        """with maximum value

        Return optional minimum value for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with maximum value`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, type)

        return value

    def __executeActionUIDialogOptionWithDefaultIndex(self, currentAst, type):
        """with default index

        Return optional default index for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with default index`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, type)

        return value

    def __executeActionUIDialogOptionWithChoices(self, currentAst):
        """with default combobox choices

        Return optional list of choices for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option `with combobox choices`'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, list)
        value=[str(item) for item in value]

        return value

    def __executeActionUIDialogMessage(self, currentAst):
        """Open dialog for message"""
        fctLabel='Action `open dialog for message`'

        # there's no control about number of parameter: just, each parameter MUSt be a ACTION_UIDIALOG_OPTION

        message='<h1>Oops!</h1><p>Did you forgot to set a <b>with message</b> option?'
        title='BuliScript message!'

        for node in currentAst.nodes():
            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        WDialogMessage.display(title, message)

        #self.__delay()
        return None

    def __executeActionUIDialogBooleanInput(self, currentAst):
        """Open dialog for boolean input"""
        fctLabel='Action `open dialog for boolean input`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message='<h1>Oops!</h1><p>Did you forgot to set a <b>with message</b> option?'
        title='BuliScript message!'

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        scriptBlock=self.__scriptBlockStack.current()
        scriptBlock.setVariable(variableName, WDialogBooleanInput.display(title, message), True)

        #self.__delay()
        return None

    def __executeActionUIDialogStringInput(self, currentAst):
        """Open dialog for string input"""
        fctLabel='Action `open dialog for string input`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultValue=''

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Value":
                defaultValue=self.__executeActionUIDialogOptionWithDefaultValue(node, str)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        scriptBlock=self.__scriptBlockStack.current()
        scriptBlock.setVariable(variableName, WDialogStrInput.display(title, message, defaultValue=defaultValue), True)

        #self.__delay()
        return None

    def __executeActionUIDialogIntegerInput(self, currentAst):
        """Open dialog for integer input"""
        fctLabel='Action `open dialog for integer input`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultValue=0
        minimumValue=None
        maximumValue=None

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Value":
                defaultValue=self.__executeActionUIDialogOptionWithDefaultValue(node, int)
            elif node.id()=="Action_UIDialog_Option_With_Minimum_Value":
                minimumValue=self.__executeActionUIDialogOptionWithMinimumValue(node, int)
            elif node.id()=="Action_UIDialog_Option_With_Maximum_Value":
                maximumValue=self.__executeActionUIDialogOptionWithMaximumValue(node, int)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        scriptBlock=self.__scriptBlockStack.current()
        scriptBlock.setVariable(variableName, WDialogIntInput.display(title, message, defaultValue=defaultValue, minValue=minimumValue, maxValue=maximumValue), True)

        #self.__delay()
        return None

    def __executeActionUIDialogDecimalInput(self, currentAst):
        """Open dialog for decimal input"""
        fctLabel='Action `open dialog for decimal input`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultValue=0
        minimumValue=None
        maximumValue=None

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Value":
                defaultValue=self.__executeActionUIDialogOptionWithDefaultValue(node, float)
            elif node.id()=="Action_UIDialog_Option_With_Minimum_Value":
                minimumValue=self.__executeActionUIDialogOptionWithMinimumValue(node, float)
            elif node.id()=="Action_UIDialog_Option_With_Maximum_Value":
                maximumValue=self.__executeActionUIDialogOptionWithMaximumValue(node, float)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        scriptBlock=self.__scriptBlockStack.current()
        scriptBlock.setVariable(variableName, WDialogFloatInput.display(title, message, defaultValue=defaultValue, minValue=minimumValue, maxValue=maximumValue), True)

        #self.__delay()
        return None

    def __executeActionUIDialogColorInput(self, currentAst):
        """Open dialog for color input"""
        fctLabel='Action `open dialog for color input`'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultValue=QColor('#FF0000')

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Value":
                defaultValue=self.__executeActionUIDialogOptionWithDefaultValue(node, QColor)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        minSize=None
        if message=='':
            minSize=QSize(640, 480)

        scriptBlock=self.__scriptBlockStack.current()

        scriptBlock.setVariable(variableName, WDialogColorInput.display(title, message, defaultValue=defaultValue,
                                options={'layout':
                                            ['colorRGB',
                                             'colorHSV',
                                             'colorWheel',
                                             'colorAlpha',
                                             'colorPreview',
                                             f'colorCombination:{WColorComplementary.COLOR_COMBINATION_TETRADIC}',
                                             f'layoutOrientation:{WColorPicker.OPTION_ORIENTATION_HORIZONTAL}']
                                    },
                                minSize=minSize), True)

        #self.__delay()
        return None







        #choiceList=['Item A', 'Item B', 'Item C', 'Item D']

        #print(WDialogComboBoxChoiceInput.display('test combobox', msg, inputLabel='Please make a choice', choicesValue=choiceList))
        #print(WDialogComboBoxChoiceInput.display('test combobox', msg2, choicesValue=choiceList, defaultIndex=2))
        #print(WDialogComboBoxChoiceInput.display('test combobox', inputLabel='Your choice', choicesValue=choiceList))

        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', msg, inputLabel='Please make a choice', choicesValue=choiceList))
        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', msg2, choicesValue=choiceList, defaultIndex=2))
        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', inputLabel='Your choice', choicesValue=choiceList))

        #print(WDialogCheckBoxChoiceInput.display('test checkbox', msg, inputLabel='Please make a choice', choicesValue=choiceList, defaultChecked=[1,3], minimumChecked=2))
        #print(WDialogCheckBoxChoiceInput.display('test checkbox', msg2, choicesValue=choiceList))
        #print(WDialogCheckBoxChoiceInput.display('test checkbox', inputLabel='Your choice', choicesValue=choiceList))


        #print(WDialogColorInput.display('test checkbox', msg, inputLabel='Please choose a color'))
        #print(WDialogColorInput.display('test checkbox', inputLabel='Choose', defaultValue='#ffff00', options={"menu":WColorPicker.OPTION_MENU_ALL, "layout": ['layoutOrientation:1', 'colorWheel', 'colorRGB']}, minSize=QSize(300,700)))
        #print(WDialogColorInput.display('test checkbox', msg2, defaultValue=QColor('#ff00ff'), options={"layout": ['colorpalette', 'colorWheel', 'colorRGB', 'colorHSL']}))


        #self.__delay()
        return None

    def __executeActionUIDialogSingleChoiceInput(self, currentAst):
        """Open dialog for single choice input"""
        fctLabel='Action `open dialog for single choice input`'

        if len(currentAst.nodes())<2:
            # at least need 2 parameters (variable + option choices)
            self.__checkParamNumber(currentAst, fctLabel, 2)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultIndex=0
        choicesValue=None
        comboboxListChoice=True

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Index":
                defaultIndex=self.__executeActionUIDialogOptionWithDefaultIndex(node, int)
            elif node.id()=="Action_UIDialog_Option_With_Combobox_Choices":
                choicesValue=self.__executeActionUIDialogOptionWithChoices(node)
                comboboxListChoice=True
            elif node.id()=="Action_UIDialog_Option_With_RadioButton_Choices":
                choicesValue=self.__executeActionUIDialogOptionWithChoices(node)
                comboboxListChoice=False
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        if choicesValue is None:
            raise EInterpreter(f"{fctLabel}: option 'with combobox choices' or 'with radio button choices' is required", currentAst)
        elif len(choicesValue)==0:
            raise EInterpreter(f"{fctLabel}: provided choices can't be an empty list", currentAst)

        defaultIndex-=1         # given index is in [1 ; len(choices)] ==> so in python [0 ; len(choices) - 1]
        defaultIndex=max(0, min(defaultIndex, len(choicesValue) - 1))

        scriptBlock=self.__scriptBlockStack.current()
        if comboboxListChoice:
            value=WDialogComboBoxChoiceInput.display(title, message, defaultIndex=defaultIndex, choicesValue=choicesValue)
        else:
            value=WDialogRadioButtonChoiceInput.display(title, message, defaultIndex=defaultIndex, choicesValue=choicesValue)


        if isinstance(value, int):
            # +1 because in BuliScript, index in list start from 1, not 0
            value+=1
        scriptBlock.setVariable(variableName, value, True)

        #self.__delay()
        return None

    def __executeActionUIDialogMultipleChoiceInput(self, currentAst):
        """Open dialog for multiple choice input"""
        fctLabel='Action `open dialog for multiple choice input`'

        if len(currentAst.nodes())<2:
            # at least need 2 parameters (variable + option choices)
            self.__checkParamNumber(currentAst, fctLabel, 2)

        # no need to check if is a user variable (parser already check it)
        variableName=currentAst.node(0).value()

        message=''
        title='BuliScript message!'
        defaultChecked=[0]
        choicesValue=None
        minimumChecked=0

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_UIDialog_Option_With_Message":
                message=self.__executeActionUIDialogOptionWithMessage(node)
            elif node.id()=="Action_UIDialog_Option_With_Title":
                title=self.__executeActionUIDialogOptionWithTitle(node)
            elif node.id()=="Action_UIDialog_Option_With_Default_Index":
                defaultChecked=self.__executeActionUIDialogOptionWithDefaultIndex(node, (int, list))
            elif node.id()=="Action_UIDialog_Option_With_Choices":
                choicesValue=self.__executeActionUIDialogOptionWithChoices(node)
            elif node.id()=="Action_UIDialog_Option_With_Minimum_Choices":
                minimumChecked=self.__executeActionUIDialogOptionWithMinimumValue(node, int)
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)

        if choicesValue is None:
            raise EInterpreter(f"{fctLabel}: option 'with choices' is required", currentAst)
        elif len(choicesValue)==0:
            raise EInterpreter(f"{fctLabel}: provided choices can't be an empty list", currentAst)

        if isinstance(defaultChecked, int):
            defaultChecked=[defaultChecked]
        defaultChecked=[max(0, min(item, len(choicesValue) - 1)) for item in defaultChecked]

        minimumChecked=max(0, min(minimumChecked, len(choicesValue) - 1))

        scriptBlock=self.__scriptBlockStack.current()
        value=WDialogCheckBoxChoiceInput.display(title, message, defaultChecked=defaultChecked, choicesValue=choicesValue, minimumChecked=minimumChecked)


        if isinstance(value, list):
            # +1 because in BuliScript, index in list start from 1, not 0
            value=[item+1 for item in value]
        scriptBlock.setVariable(variableName, value, True)

        #self.__delay()
        return None








        #choiceList=['Item A', 'Item B', 'Item C', 'Item D']

        #print(WDialogComboBoxChoiceInput.display('test combobox', msg, inputLabel='Please make a choice', choicesValue=choiceList))
        #print(WDialogComboBoxChoiceInput.display('test combobox', msg2, choicesValue=choiceList, defaultIndex=2))
        #print(WDialogComboBoxChoiceInput.display('test combobox', inputLabel='Your choice', choicesValue=choiceList))

        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', msg, inputLabel='Please make a choice', choicesValue=choiceList))
        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', msg2, choicesValue=choiceList, defaultIndex=2))
        #print(WDialogRadioButtonChoiceInput.display('test radiobutton', inputLabel='Your choice', choicesValue=choiceList))

        #print(WDialogCheckBoxChoiceInput.display('test checkbox', msg, inputLabel='Please make a choice', choicesValue=choiceList, defaultChecked=[1,3], minimumChecked=2))
        #print(WDialogCheckBoxChoiceInput.display('test checkbox', msg2, choicesValue=choiceList))
        #print(WDialogCheckBoxChoiceInput.display('test checkbox', inputLabel='Your choice', choicesValue=choiceList))


        #print(WDialogColorInput.display('test checkbox', msg, inputLabel='Please choose a color'))
        #print(WDialogColorInput.display('test checkbox', inputLabel='Choose', defaultValue='#ffff00', options={"menu":WColorPicker.OPTION_MENU_ALL, "layout": ['layoutOrientation:1', 'colorWheel', 'colorRGB']}, minSize=QSize(300,700)))
        #print(WDialogColorInput.display('test checkbox', msg2, defaultValue=QColor('#ff00ff'), options={"layout": ['colorpalette', 'colorWheel', 'colorRGB', 'colorHSL']}))


        #self.__delay()
        return None





    # --------------------------------------------------------------------------
    # Functions & Evaluation
    # --------------------------------------------------------------------------
    def __executeFunction(self, currentAst):
        """Execute a function"""
        def sortKey(x):
            # a function used to compare items in list, allowing to sort list with values
            # mixed values (int, float, string, QColor, ...)
            if isinstance(x, (int, float)):
                return f"{x:050.25f}"
            elif isinstance(x, QColor):
                return x.name(QColor.HexArgb)
            else:
                try:
                    return f"{float(x):050.25f}"
                except:
                    return str(x)

        # Defined by N+1 nodes:
        #   0: function (<Token>)
        #   N: value (<Token> or <ASTItem>)  -- arguments, 0 to N; will depend of function

        # get function name
        fctName=currentAst.node(0).value()
        fctLabel=f'Function {fctName}()'

        if fctName=='math.random':
            self.__checkFctParamNumber(currentAst, fctLabel, 0, 2)

            if currentAst.countNodes()==1:
                # no parameters
                return random.random()
            elif currentAst.countNodes()==3:
                minValue=self.__evaluate(currentAst.node(1))
                maxValue=self.__evaluate(currentAst.node(2))

                self.__checkParamType(currentAst, fctLabel, '<MIN>', minValue, int, float)
                self.__checkParamType(currentAst, fctLabel, '<MAX>', maxValue, int, float)

                if minValue>maxValue:
                    # switch values
                    minValue, maxValue=maxValue, minValue

                if isinstance(minValue, int) and isinstance(maxValue, int):
                    # both bound value are integer, return integer
                    return random.randrange(minValue, maxValue)
                else:
                    # at least one decimal value, return decimal value
                    return random.uniform(minValue, maxValue)

        elif fctName=='math.abs':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return abs(value)
        elif fctName=='math.even':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return (value%2)==0
        elif fctName=='math.odd':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return (value%2)==1
        elif fctName=='math.sign':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            if isinstance(value, int):
                if value==0:
                    return 0
                elif value>0:
                    return 1
                else:
                    return -1
            elif isinstance(value, float):
                if value==0:
                    return 0.0
                elif value>0:
                    return 1.0
                else:
                    return -1.0
        elif fctName=='math.exp':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.exp(value)
        elif fctName=='math.power':
            self.__checkFctParamNumber(currentAst, fctLabel, 2)
            value=self.__evaluate(currentAst.node(1))
            power=self.__evaluate(currentAst.node(2))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamType(currentAst, fctLabel, '<POWER>', power, int, float)

            return math.pow(value, power)
        elif fctName=='math.square_root':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>=0, f'must be a zero or positive numeric value (current={value})')


            return math.sqrt(value)
        elif fctName=='math.logn':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>0, f'must be a positive numeric value (current={value})')

            return math.log(value)
        elif fctName=='math.log':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            base=self.__evaluate(currentAst.node(2, 10))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamType(currentAst, fctLabel, '<BASE>', value, int, float)

            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>0, f'must be a positive numeric value (current={value})')
            self.__checkParamDomain(currentAst, fctLabel, '<BASE>', base>0 and base!=1, f'must be a positive numeric value not equal to 1  (current={base})')

            return math.log(value, base)
        elif fctName=='math.convert':
            self.__checkFctParamNumber(currentAst, fctLabel, 3,4)

            value=self.__evaluate(currentAst.node(1))
            convertFrom=self.__evaluate(currentAst.node(2))
            convertTo=self.__evaluate(currentAst.node(3))
            refPct=self.__evaluate(currentAst.node(4))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamType(currentAst, fctLabel, '<F-UNIT>', convertFrom, str)
            self.__checkParamType(currentAst, fctLabel, '<T-UNIT>', convertTo, str)

            # need to check consistency convertFrom->convertTo
            if convertFrom in ['PX', 'PCT', 'MM', 'INCH']:
                self.__checkParamDomain(currentAst, fctLabel, '<T-UNIT>', convertTo in ['PX', 'PCT', 'MM', 'INCH'], 'conversion of a measure unit can only be converted to another measure unit (PC, PCT, MM, INCH)')
                returned=BSConvertUnits.convert(value, convertFrom, convertTo, refPct)
            elif convertFrom in ['DEGREE','RADIAN']:
                self.__checkParamDomain(currentAst, fctLabel, '<T-UNIT>', convertTo in ['DEGREE','RADIAN'], 'conversion of an angle unit can only be converted to another angle unit (DEGREE, RADIAN)')
                returned=BSConvertUnits.convert(value, convertFrom, convertTo, refPct)
            else:
                self.__checkParamDomain(currentAst, fctLabel, '<F-UNIT>', False, 'can only convert measures and angles units')

            return returned
        elif fctName=='math.minimum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'<VALUE[{index}]>', value, int, float)

            return min(values)
        elif fctName=='math.maximum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'<VALUE[{index}]>', value, int, float)

            return max(values)
        elif fctName=='math.sum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'<VALUE[{index}]>', value, int, float)

            return sum(values)
        elif fctName=='math.average':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'<VALUE[{index}]>', value, int, float)

            nbItems=len(values)
            if nbItems>0:
                return sum(values)/nbItems
            return 0
        elif fctName=='math.product':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'<VALUE[{index}]>', value, int, float)

            nbItems=len(values)
            if nbItems>0:
                return math.prod(values)
            return 0
        elif fctName=='math.ceil':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.ceil(value)
        elif fctName=='math.floor':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.floor(value)
        elif fctName=='math.round':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            roundValue=self.__evaluate(currentAst.node(2, 0))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamType(currentAst, fctLabel, '<DECIMALS>', roundValue, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<DECIMALS>', roundValue>=0 and isinstance(roundValue, int), f"must be a zero or positive integer value (current={roundValue})")

            if roundValue==0:
                # because math.floor(x, 0) return a float
                # and here we want an integer if rounded to 0 decimal
                return round(value)
            else:
                return round(value, roundValue)
        elif fctName=='math.cos':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.cos(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.sin':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.sin(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.tan':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.tan(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.acos':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>=-1 and value<=1 , f"must be a numeric value in range [-1.0;1.0] (current={value})")

            return math.acos(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.asin':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>=-1 and value<=1 , f"must be a numeric value in range [-1.0;1.0] (current={value})")

            return math.asin(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.atan':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.atan(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.cosh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.cosh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.sinh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.sinh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.tanh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.tanh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.acosh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>=1, f"must be a numeric value in range [1.0;infinite[ (current={value})")

            return math.acosh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.asinh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)

            return math.asinh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.atanh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<VALUE>', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, '<VALUE>', value>-1 and value<1 , f"must be a numeric value in range ]-1.0;1.0[ (current={value})")

            return math.atanh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='string.length':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<TEXT>', value, str)

            return len(value)
        elif fctName=='string.upper':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<TEXT>', value, str)

            return value.upper()
        elif fctName=='string.lower':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<TEXT>', value, str)

            return value.lower()
        elif fctName=='string.substring':
            self.__checkFctParamNumber(currentAst, fctLabel, 2,3)

            value=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, '<TEXT>', value, str)

            nbChar=len(value)
            if value=='':
                # empty string, return result immediately
                return ''


            fromIndex=self.__evaluate(currentAst.node(2))
            self.__checkParamType(currentAst, fctLabel, '<INDEX>', fromIndex, int)
            if fromIndex==0 or abs(fromIndex)>nbChar:
                # invalid index, return empty string immediately
                return ''

            countChar=self.__evaluate(currentAst.node(3))
            if countChar:
                self.__checkParamType(currentAst, fctLabel, '<COUNT>', countChar, int)

            if fromIndex>0:
                # positive value, start from beginning
                if countChar:
                    # return a specific number of characters
                    return value[fromIndex-1:fromIndex+countChar-1]
                else:
                    # return all characters
                    return value[fromIndex-1:]
            else:
                if countChar:
                    # return a specific number of characters
                    return value[fromIndex:fromIndex+countChar]
                else:
                    # return all characters
                    return value[fromIndex:]
        elif fctName=='color.rgb':
            self.__checkFctParamNumber(currentAst, fctLabel, 3)

            rValue=self.__evaluate(currentAst.node(1))
            gValue=self.__evaluate(currentAst.node(2))
            bValue=self.__evaluate(currentAst.node(3))


            self.__checkParamType(currentAst, fctLabel, '<R-VALUE>', rValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<G-VALUE>', gValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<B-VALUE>', bValue, int, float)

            if isinstance(rValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<R-VALUE>', rValue>=0 and rValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={rValue})", False):
                    rValue=min(255, max(0, rValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<R-VALUE>', rValue>=0.0 and rValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={rValue})", False):
                    rValue=min(1.0, max(0.0, rValue))

            if isinstance(gValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<G-VALUE>', gValue>=0 and gValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={gValue})", False):
                    gValue=min(255, max(0, gValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<G-VALUE>', gValue>=0.0 and gValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={gValue})", False):
                    gValue=min(1.0, max(0.0, gValue))

            if isinstance(bValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<B-VALUE>', bValue>=0 and bValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={bValue})", False):
                    bValue=min(255, max(0, bValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<B-VALUE>', bValue>=0.0 and bValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={bValue})", False):
                    bValue=min(1.0, max(0.0, bValue))

            # convert all values as integer 0-255
            if isinstance(rValue, float):
                rValue=round(rValue*255)
            if isinstance(gValue, float):
                gValue=round(gValue*255)
            if isinstance(bValue, float):
                bValue=round(bValue*255)

            return QColor.fromRgb(rValue, gValue, bValue)
        elif fctName=='color.rgba':
            self.__checkFctParamNumber(currentAst, fctLabel, 4)

            rValue=self.__evaluate(currentAst.node(1))
            gValue=self.__evaluate(currentAst.node(2))
            bValue=self.__evaluate(currentAst.node(3))
            aValue=self.__evaluate(currentAst.node(4))


            self.__checkParamType(currentAst, fctLabel, '<R-VALUE>', rValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<G-VALUE>', gValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<B-VALUE>', bValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<O-VALUE>', aValue, int, float)

            if isinstance(rValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<R-VALUE>', rValue>=0 and rValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={rValue})", False):
                    rValue=min(255, max(0, rValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<R-VALUE>', rValue>=0.0 and rValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={rValue})", False):
                    rValue=min(1.0, max(0.0, rValue))

            if isinstance(gValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<G-VALUE>', gValue>=0 and gValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={gValue})", False):
                    gValue=min(255, max(0, gValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<G-VALUE>', gValue>=0.0 and gValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={gValue})", False):
                    gValue=min(1.0, max(0.0, gValue))

            if isinstance(bValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<B-VALUE>', bValue>=0 and bValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={bValue})", False):
                    bValue=min(255, max(0, bValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<B-VALUE>', bValue>=0.0 and bValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={bValue})", False):
                    bValue=min(1.0, max(0.0, bValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
                    aValue=min(1.0, max(0.0, aValue))

            # convert all values as integer 0-255
            if isinstance(rValue, float):
                rValue=round(rValue*255)
            if isinstance(gValue, float):
                gValue=round(gValue*255)
            if isinstance(bValue, float):
                bValue=round(bValue*255)
            if isinstance(aValue, float):
                aValue=round(aValue*255)

            return QColor.fromRgb(rValue, gValue, bValue, aValue)
        elif fctName=='color.hsl':
            self.__checkFctParamNumber(currentAst, fctLabel, 3)

            hValue=self.__evaluate(currentAst.node(1))
            sValue=self.__evaluate(currentAst.node(2))
            lValue=self.__evaluate(currentAst.node(3))

            self.__checkParamType(currentAst, fctLabel, '<H-VALUE>', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<S-VALUE>', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<L-VALUE>', lValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(lValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<L-VALUE>', lValue>=0 and lValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={lValue})", False):
                    lValue=min(255, max(0, lValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<L-VALUE>', lValue>=0.0 and lValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={lValue})", False):
                    lValue=min(1.0, max(0.0, lValue))


            # convert all values as integer 255
            if isinstance(hValue, float):
                hValue=round(hValue*255)
            if isinstance(sValue, float):
                sValue=round(sValue*255)
            if isinstance(lValue, float):
                lValue=round(lValue*255)

            return QColor.fromHsl(hValue%360, sValue, lValue)
        elif fctName=='color.hsla':
            self.__checkFctParamNumber(currentAst, fctLabel, 4)

            hValue=self.__evaluate(currentAst.node(1))
            sValue=self.__evaluate(currentAst.node(2))
            lValue=self.__evaluate(currentAst.node(3))
            aValue=self.__evaluate(currentAst.node(4))


            self.__checkParamType(currentAst, fctLabel, '<H-VALUE>', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<S-VALUE>', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<L-VALUE>', lValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<O-VALUE>', aValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(lValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<L-VALUE>', lValue>=0 and lValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={lValue})", False):
                    lValue=min(255, max(0, lValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<L-VALUE>', lValue>=0.0 and lValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={lValue})", False):
                    lValue=min(1.0, max(0.0, lValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
                    aValue=min(1.0, max(0.0, aValue))

            # convert all values as integer 255
            if isinstance(hValue, float):
                hValue=round(hValue*255)
            if isinstance(sValue, float):
                sValue=round(sValue*255)
            if isinstance(lValue, float):
                lValue=round(lValue*255)
            if isinstance(aValue, float):
                aValue=round(aValue*255)

            return QColor.fromHsl(hValue%360, sValue, lValue, aValue)
        elif fctName=='color.hsv':
            self.__checkFctParamNumber(currentAst, fctLabel, 3)

            hValue=self.__evaluate(currentAst.node(1))
            sValue=self.__evaluate(currentAst.node(2))
            vValue=self.__evaluate(currentAst.node(3))

            self.__checkParamType(currentAst, fctLabel, '<H-VALUE>', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<S-VALUE>', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<V-VALUE>', vValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(vValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<V-VALUE>', vValue>=0 and vValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={vValue})", False):
                    vValue=min(255, max(0, vValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<V-VALUE>', vValue>=0.0 and vValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={vValue})", False):
                    vValue=min(1.0, max(0.0, vValue))

            # convert all values as integer 255
            if isinstance(hValue, float):
                hValue=round(hValue*255)
            if isinstance(sValue, float):
                sValue=round(sValue*255)
            if isinstance(vValue, float):
                vValue=round(vValue*255)

            return QColor.fromHsv(hValue%360, sValue, vValue)
        elif fctName=='color.hsva':
            self.__checkFctParamNumber(currentAst, fctLabel, 4)

            hValue=self.__evaluate(currentAst.node(1))
            sValue=self.__evaluate(currentAst.node(2))
            vValue=self.__evaluate(currentAst.node(3))
            aValue=self.__evaluate(currentAst.node(4))

            self.__checkParamType(currentAst, fctLabel, '<H-VALUE>', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<S-VALUE>', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<V-VALUE>', vValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<O-VALUE>', aValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<S-VALUE>', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(vValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<V-VALUE>', vValue>=0 and vValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={vValue})", False):
                    vValue=min(255, max(0, vValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<V-VALUE>', vValue>=0.0 and vValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={vValue})", False):
                    vValue=min(1.0, max(0.0, vValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
                    aValue=min(1.0, max(0.0, aValue))

            # convert all values as integer 255
            if isinstance(hValue, float):
                hValue=round(hValue*255)
            if isinstance(sValue, float):
                sValue=round(sValue*255)
            if isinstance(vValue, float):
                vValue=round(vValue*255)
            if isinstance(aValue, float):
                aValue=round(aValue*255)

            return QColor.fromHsv(hValue%360, sValue, vValue, aValue)
        elif fctName=='color.cmyk':
            self.__checkFctParamNumber(currentAst, fctLabel, 4)

            cValue=self.__evaluate(currentAst.node(1))
            mValue=self.__evaluate(currentAst.node(2))
            yValue=self.__evaluate(currentAst.node(3))
            kValue=self.__evaluate(currentAst.node(4))


            self.__checkParamType(currentAst, fctLabel, '<C-VALUE>', cValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<M-VALUE>', mValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<Y-VALUE>', yValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<K-VALUE>', kValue, int, float)

            if isinstance(cValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<C-VALUE>', cValue>=0 and cValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={cValue})", False):
                    cValue=min(255, max(0, cValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<C-VALUE>', cValue>=0.0 and cValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={cValue})", False):
                    cValue=min(1.0, max(0.0, cValue))

            if isinstance(mValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<M-VALUE>', mValue>=0 and mValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={mValue})", False):
                    mValue=min(255, max(0, mValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<M-VALUE>', mValue>=0.0 and mValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={mValue})", False):
                    mValue=min(1.0, max(0.0, mValue))

            if isinstance(yValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<Y-VALUE>', yValue>=0 and yValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={yValue})", False):
                    yValue=min(255, max(0, yValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<Y-VALUE>', yValue>=0.0 and yValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={yValue})", False):
                    yValue=min(1.0, max(0.0, yValue))

            if isinstance(kValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<K-VALUE>', kValue>=0 and kValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={kValue})", False):
                    kValue=min(255, max(0, kValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<K-VALUE>', kValue>=0.0 and kValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={kValue})", False):
                    kValue=min(1.0, max(0.0, kValue))

            # convert all values as integer 0-255
            if isinstance(cValue, float):
                cValue=round(cValue*255)
            if isinstance(mValue, float):
                mValue=round(mValue*255)
            if isinstance(yValue, float):
                yValue=round(yValue*255)
            if isinstance(kValue, float):
                kValue=round(kValue*255)

            return QColor.fromCmyk(cValue, mValue, yValue, kValue)
        elif fctName=='color.cmyka':
            self.__checkFctParamNumber(currentAst, fctLabel, 5)

            cValue=self.__evaluate(currentAst.node(1))
            mValue=self.__evaluate(currentAst.node(2))
            yValue=self.__evaluate(currentAst.node(3))
            kValue=self.__evaluate(currentAst.node(4))
            aValue=self.__evaluate(currentAst.node(5))


            self.__checkParamType(currentAst, fctLabel, '<C-VALUE>', cValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<M-VALUE>', mValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<Y-VALUE>', yValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<K-VALUE>', kValue, int, float)
            self.__checkParamType(currentAst, fctLabel, '<O-VALUE>', aValue, int, float)

            if isinstance(cValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<C-VALUE>', cValue>=0 and cValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={cValue})", False):
                    cValue=min(255, max(0, cValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<C-VALUE>', cValue>=0.0 and cValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={cValue})", False):
                    cValue=min(1.0, max(0.0, cValue))

            if isinstance(mValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<M-VALUE>', mValue>=0 and mValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={mValue})", False):
                    mValue=min(255, max(0, mValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<M-VALUE>', mValue>=0.0 and mValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={mValue})", False):
                    mValue=min(1.0, max(0.0, mValue))

            if isinstance(yValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<Y-VALUE>', yValue>=0 and yValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={yValue})", False):
                    yValue=min(255, max(0, yValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<Y-VALUE>', yValue>=0.0 and yValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={yValue})", False):
                    yValue=min(1.0, max(0.0, yValue))

            if isinstance(kValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<K-VALUE>', kValue>=0 and kValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={kValue})", False):
                    kValue=min(255, max(0, kValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<K-VALUE>', kValue>=0.0 and kValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={kValue})", False):
                    kValue=min(1.0, max(0.0, kValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, '<O-VALUE>', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
                    aValue=min(1.0, max(0.0, aValue))

            # convert all values as integer 0-255
            if isinstance(cValue, float):
                cValue=round(cValue*255)
            if isinstance(mValue, float):
                mValue=round(mValue*255)
            if isinstance(yValue, float):
                yValue=round(yValue*255)
            if isinstance(kValue, float):
                kValue=round(kValue*255)
            if isinstance(aValue, float):
                aValue=round(aValue*255)

            return QColor.fromCmyk(cValue, mValue, yValue, kValue, aValue)
        elif fctName=='list.length':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)

            return len(value)
        elif fctName=='list.join':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            sepChar=self.__evaluate(currentAst.node(2, ','))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)
            self.__checkParamType(currentAst, fctLabel, '<SEPARATOR>', sepChar, str)

            # do join; force string conversion of items
            return sepChar.join([item.name() if isinstance(item, QColor) and item.alpha()==255
                                 else item.name(QColor.HexArgb) if isinstance(item, QColor)
                                 else str(item)
                                 for item in value])
        elif fctName=='string.split':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            sepChar=self.__evaluate(currentAst.node(2, ','))

            self.__checkParamType(currentAst, fctLabel, '<TEXT>', value, str)
            self.__checkParamType(currentAst, fctLabel, '<SEPARATOR>', sepChar, str)

            return value.split(sepChar)
        elif fctName=='list.rotate':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            shiftValue=self.__evaluate(currentAst.node(2, 1))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)
            self.__checkParamType(currentAst, fctLabel, '<VALUE>', shiftValue, int)

            return rotate(value, shiftValue)
        elif fctName=='list.sort':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            ascending=self.__evaluate(currentAst.node(2, True))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)
            self.__checkParamType(currentAst, fctLabel, '<ASCENDING>', ascending, bool)

            return sorted(value, key=sortKey, reverse=not ascending)
        elif fctName=='list.revert':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)

            return value[::-1]
        elif fctName=='list.unique':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)

            return unique(value)
        elif fctName=='list.shuffle':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)

            return random.sample(value, len(value))
        elif fctName=='list.index':
            self.__checkFctParamNumber(currentAst, fctLabel, 2,3)

            value=self.__evaluate(currentAst.node(1))
            index=self.__evaluate(currentAst.node(2))
            default=self.__evaluate(currentAst.node(3, 0))

            self.__checkParamType(currentAst, fctLabel, '<LIST>', value, list)
            self.__checkParamType(currentAst, fctLabel, '<INDEX>', index, int)

            if index>0 and index<=len(value):
                return value[index-1]
            elif index<0 and index > -len(value):
                return value[index]
            else:
                return default
        elif fctName=='boolean.isstring':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, str)
        elif fctName=='boolean.isnumber':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, (int, float))
        elif fctName=='boolean.isinteger':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, int)
        elif fctName=='boolean.isdecimal':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, float)
        elif fctName=='boolean.isboolean':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, bool)
        elif fctName=='boolean.iscolor':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, QColor)
        elif fctName=='boolean.islist':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            return isinstance(value, list)
        else:
            # shouldn't occurs
            raise EInterpreterInternalError(f"Function {fctName}() hasn't been implemented!?", currentAst)

    def __executeEvaluationExpressionParenthesis(self, currentAst):
        """return evaluation of expression in parenthesis"""
        # defined by 1 Token nodes (<Token> or <ASTItem>)
        return self.__evaluate(currentAst.node(0))

    def __executeStringValue(self, currentAst):
        """return string value"""
        # defined by N Token nodes (String)

        returned=[]
        for item in currentAst.nodes():
            returned.append(item.value())

        return ''.join(returned)

    def __executeListValue(self, currentAst):
        """return string value"""
        # defined by N nodes (ASTItem)
        returned=[]
        for item in currentAst.nodes():
            returned.append(self.__evaluate(item))

        return returned


    # --------------------------------------------------------------------------
    # Operators
    # --------------------------------------------------------------------------
    def __executeUnaryOperator(self, currentAst):
        """return unary operation result"""
        # Defined by 2 nodes:
        #   0: operator (<Token>)
        #   1: value (<Token> or <ASTItem>)

        # get operator
        operator=currentAst.node(0).value()

        # evaluate value
        value=self.__evaluate(currentAst.node(1))

        if operator=='not':
            if isinstance(value, bool):
                return not value

            # not a boolean, raise an error
            raise EInterpreter(f"Boolean operator 'NOT' can only be applied on a boolean value", currentAst)
        elif operator=='-':
            if isinstance(value, float) or isinstance(value, int):
                return -value

            # not a boolean, raise an error
            raise EInterpreter(f"Negative operator '-' can only be applied on a numeric value", currentAst)

        # should not occurs
        raise EInterpreter(f"Unknown operator: {operator}", currentAst)

    def __executeBinaryOperator(self, currentAst):
        """return binary operation result"""
        # Defined by 3 nodes:
        #   0: operator (<Token>)
        #   1: left value (<Token> or <ASTItem>)
        #   2: right value (<Token> or <ASTItem>)

        # get opertor
        operator=currentAst.node(0).value()

        # evaluate values
        leftValue=self.__evaluate(currentAst.node(1))
        rightValue=self.__evaluate(currentAst.node(2))

        if operator=='*':
            # product operator can be applied
            # - between 2 numeric values
            # - between 1 numeric value and 1 string
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float, str)) or
                isinstance(leftValue, str) and isinstance(rightValue, (int, float))):
                return leftValue * rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Multiply operator '*' can only be applied between:\n- 2 numeric values\n- 1 numeric value and 1 string value", currentAst)
        elif operator=='/':
            # divide operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue / rightValue
                raise EInterpreter(f"Division by zero", currentAst)

            # not a valid operation, raise an error
            raise EInterpreter(f"Divide operator '/' can only be applied between 2 numeric values", currentAst)
        elif operator=='//':
            # Floor division operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue // rightValue
                raise EInterpreter(f"Division by zero", currentAst)

            # not a valid operation, raise an error
            raise EInterpreter(f"Floor division operator '//' can only be applied between 2 numeric values", currentAst)
        elif operator=='%':
            # Modulus operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue % rightValue
                raise EInterpreter(f"Division by zero", currentAst)

            # not a valid operation, raise an error
            raise EInterpreter(f"Modulus operator '%' can only be applied between 2 numeric values", currentAst)
        elif operator=='+':
            # addition operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str)):
                return leftValue + rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Addition operator '+' can only be applied between\n- 2 numeric values\n- 2 string values", currentAst)
        elif operator=='-':
            # Subtraction operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                return leftValue - rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Subtraction operator '-' can only be applied between 2 numeric values", currentAst)
        elif operator=='<':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue < rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Lower than comparison operator '<' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='<=':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue <= rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Lower or equal than operator '<=' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='>':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue > rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Greater than operator '>' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='>=':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue >= rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Greater or equal than operator '>=' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='=':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue == rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Equal comparison operator '=' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='<>':
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str) or
                isinstance(leftValue, bool) and isinstance(rightValue, bool)):
                return leftValue != rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Not equal comparison operator '!=' can only be applied between\n- 2 numeric values\n- 2 string values\n- 2 boolean values", currentAst)
        elif operator=='and':
            # Logical operator can be applied
            # - between 2 boolean values
            if isinstance(leftValue, bool) and isinstance(rightValue, bool):
                return leftValue and rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Logical operator 'AND' can only be applied between 2 boolean values", currentAst)
        elif operator=='or':
            # Logical operator can be applied
            # - between 2 boolean values
            if isinstance(leftValue, bool) and isinstance(rightValue, bool):
                return leftValue or rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Logical operator 'OR' can only be applied between 2 boolean values", currentAst)
        elif operator=='xor':
            # Logical operator can be applied
            # - between 2 boolean values
            if isinstance(leftValue, bool) and isinstance(rightValue, bool):
                return leftValue ^ rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"Logical operator 'XOR' can only be applied between 2 boolean values", currentAst)

        # should not occurs
        raise EInterpreter(f"Unknown operator: {operator}", currentAst)


    # --------------------------------------------------------------------------
    # Public
    # --------------------------------------------------------------------------
    def script(self):
        """Return current script content"""
        return self.__script

    def setScript(self, script):
        """Set current script content

        If text is different than current text, parse it
        """
        # ensure parsed text is properly finished (ie: this ensure for example that
        # we have DEDENT in case of INDENT)
        script+="\n\n#<EOT>"

        if script!=self.__script:
            self.__script=script
            self.__astRoot=self.__parser.parse(self.__script)

        Debug.print('setScript/Errors: {0}', self.__parser.errors())
        Debug.print('setScript/AST: {0}', self.__astRoot)

        if len(self.__parser.errors())>0:
            raise EInterpreterInternalError("Can't parse", self.__astRoot)

    def parserErrors(self):
        """Return parser errors"""
        return self.__parser.errors()

    def canvas(self):
        """Return canvas content

        Return result as a QPaintDevice or None if interpreted has never been executed
        """
        return self.__canvas

    def running(self):
        """Return if interpreter is currently running a script"""
        return self.__isRunning

    def optionDebugMode(self):
        """Return if interpreter is in debug mode or not"""
        return self.__optionDebugMode

    def setOptionDebugMode(self, value):
        """Set if interpreter is in debug mode or not"""
        if not isinstance(value, bool):
            raise EInvalidValue("Given `value` must be <bool>")
        self.__optionDebugMode=value

    def optionVerboseMode(self):
        """Return if interpreter is in verbose mode or not"""
        return self.__optionDebugMode

    def setOptionVerboseMode(self, value):
        """Set if interpreter is in verbose mode or not"""
        if not isinstance(value, bool):
            raise EInvalidValue("Given `value` must be <bool>")
        self.__optionVerboseMode=value

    def optionDelay(self):
        """Return current delay (in ms) applied between instructions"""
        return self.__optionDelay

    def setOptionDelay(self, value):
        """Return current delay (in ms) applied between instructions"""
        if not isinstance(value, int):
            raise EInvalidValue("Given `value` must be <int>")
        elif value<0 or value>30000:
            raise EInvalidValue("Given `value` must be in range [0 - 30000] (maximum delay is 30s)")
        self.__optionDelay=value

    def execute(self):
        """Execute script"""
        if self.__isRunning:
            # can't execute while previous execution is not yet finished
            raise EInterpreterInternalError("Interpreter is already running", None)

        self.__isRunning=True
        self.executionStarted.emit()

        try:
            returned=self.__executeStart()
        except Exception as e:
            self.executionFinished.emit()
            self.__isRunning=False
            raise e

        self.executionFinished.emit()
        self.__isRunning=False
        return returned

    def executeNext(self):
        """Execute next instruction

        Notes:
        - execution must be started
        - debug mode must be active
        """
        if not self.__isRunning:
            # can't execute if execution not started
            raise EInterpreterInternalError("Interpreter is not running", None)
        elif not self.__optionDebugMode:
            # can't execute if not in debug mode
            raise EInterpreterInternalError("Interpreter is not in Debug Mode", None)



class BSScriptBlockProperties:
    """Define current script block properties"""

    def __init__(self, parent, ast, allowLocalVariable, id=None):
        if not(parent is None or isinstance(parent, BSScriptBlockProperties)):
            raise EInvalidType("Given `parent` must be None or a <BSScriptBlockProperties>")

        # keep parent, used to access to parents variables
        self.__parent=parent

        # textual Id (informatiional, not used by scipt)
        self.__id=id

        # ast that contain script block
        self.__ast=ast

        # unique Id for script execution
        self.__uuid=str(uuid.uuid4())

        # the allowLocalVariable is used here for information only
        # and no control is applied
        self.__allowLocalVariable=allowLocalVariable

        # maintain a dictionary of local Variables
        self.__variables={}

    def id(self):
        """Return informational ID, if any"""
        return self.__id

    def uuid(self):
        """Return Unique ID"""
        return self.__uuid

    def ast(self):
        """Return AST that contain script block"""
        return self.__ast

    def allowLocalVariable(self):
        """Return if current script block allows or not creation of local variables

        Example:
            for a macro, we can define local variables

            but in a "repeat", or "if then else" statements, variables are not
            created/updated in script block that match statement but in parent (root or macro)


            define macro "test" :v
                if :v1 > 50 then
                    set variable :x = :v/2              # the :x variable is defined "define macro" scriptblock, not in "if then" scriptblock
                else
                    set variable :x = :v/3

                print :x
        """
        return self.__allowLocalVariable

    def variable(self, name, default=None):
        """return variable value

        If variable doesn't exist in current dictionnary, return variable from
        parent script block, if exist, otherwise return default value
        """
        name=name.lower()
        if name in self.__variables:
            return self.__variables[name]
        elif not self.__parent is None:
            return self.__parent.variable(name, default)
        else:
            return default

    def setVariable(self, name, value, localVariable, forceToBeLocal=False):
        """Set `value` for variable designed by given `name`

        If variable doesn't exist in script block, create it
        """
        name=name.lower()
        if localVariable and self.__allowLocalVariable or not localVariable or forceToBeLocal:
            self.__variables[name]=value
        elif not self.__parent is None:
            self.__parent.setVariable(name, value, localVariable)
        else:
            # should not occurs, root scriptblock always allows user defined variable
            pass

    def variables(self, all=False):
        """Return dictionnary key/value of current variables

        If `all` is True, build a dictionnary with all variable accessible for current script block
        (ie: return parent variables)
        """
        if all and not self.__parent is None:
            # merge dictionaries
            return {**self.__parent.variables(True), **self.__variables}
        else:
            return self.__variables


class BSScriptBlockStack:
    """Stack of current executed scripts blocks"""

    def __init__(self, maxStackSize=1000):
        self.__maxStackSize=maxStackSize
        self.__stack=[]

    def push(self, ast, allowLocalVariable, name=None):
        if len(self.__stack)>0:
            parent=self.__stack[-1]
        else:
            parent=None
        if len(self.__stack)<self.__maxStackSize:
            self.__stack.append(BSScriptBlockProperties(parent, ast, allowLocalVariable, name))
        else:
            raise EInvalidStatus(f"Current stack size limit ({self.__maxStackSize}) reached!")

    def pop(self):
        """Pop current script block stack"""
        # do not control if there's something to pop
        # normally this method is called only if stack is not empty
        # if called on an empty stack, must raise an error because it must never occurs
        return self.__stack.pop()

    def current(self):
        """Return current script block

        If nothing in stack, return None
        """
        if len(self.__stack)>0:
            return self.__stack[-1]
        return None

    def count(self):
        """Return number of script block in stack"""
        return len(self.__stack)

    def clear(self):
        """Clear stack"""
        self.__stack.clear()


class BSScriptBlockMacro:
    """A macro definition"""

    def __init__(self, sourceFile, name, ast, *args):
        self.__sourceFile=sourceFile
        self.__name=name
        self.__ast=ast
        self.__argumentsName=args

    def __repr__(self):
        return f"<BSScriptBlockMacro('{self.__sourceFile}', '{self.__name}', {self.__argumentsName}, {self.__ast})>"

    def sourceFile(self):
        """Return source file from which macro has been defined"""
        return self.__sourceFile

    def name(self):
        """Return macro name"""
        return self.__name

    def ast(self):
        """Return ast scriptBlock"""
        return self.__ast

    def argumentsName(self):
        """Return list of arguments names"""
        return self.__argumentsName


class BSScriptBlockDefinedMacros:
    """Reference all macros"""

    def __init__(self):
        self.__macro={}

    def clear(self):
        """Clear all macro definitions"""
        self.__macro={}

    def alreadyDefined(self, name):
        """return True if a macro as already been defined with given `name`"""
        return (name in self.__macro)

    def add(self, macro):
        """Add a macro definition"""
        if not isinstance(macro, BSScriptBlockMacro):
            raise EInvalidType("Given `macro` must be <BSScriptBlockMacro>")

        self.__macro[macro.name()]=macro

    def get(self, name=None):
        """Return macro defined given `name`

        If macro doesn't exist, return None

        If `name` is None, return a dictionary of all macro definition
        """
        if name is None:
            return self.__macro
        elif name in self.__macro:
            return self.__macro[name]
        return None


class BSConvertUnits:

    @staticmethod
    def convert(value, fromUnit, toUnit, refPct=None):
        return value

    @staticmethod
    def convertAngle(value, fromUnit, toUnit):
        return value

    @staticmethod
    def convertMeasure(value, fromUnit, toUnit, refPct=None):
        return value



Debug.setEnabled(True)
