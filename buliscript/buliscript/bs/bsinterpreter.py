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
import time

from enum import Enum

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from .bssettings import (
        BSSettings,
        BSSettingsKey
    )
from .bslanguagedef import BSLanguageDef


from buliscript.pktk.modules.ekrita import (
        EKritaNode,
        EKritaDocument
    )
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

from buliscript.pktk.widgets.wconsole import (
        WConsoleType,
        WConsole
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

    output = Signal(str, WConsoleType, dict, bool)

    OPTION_BACKGROUND_FROM_ACTIVE_LAYER = 0
    OPTION_BACKGROUND_FROM_DOCUMENT = 1
    OPTION_BACKGROUND_FROM_COLOR = 2

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

    # conversion tables BuliScript<>Qt
    __CONV_PEN_STYLE={
            'SOLID': Qt.SolidLine,
            'DASH': Qt.DashLine,
            'DOT': Qt.DotLine,
            'DASHDOT': Qt.DashDotLine,
            'NONE': Qt.NoPen
        }

    __CONST_HALIGN={
            'LEFT': -1,
            'CENTER': 0,
            'RIGHT': 1
        }

    __CONST_VALIGN={
            'TOP': -1,
            'MIDDLE': 0,
            'BOTTOM': 1
        }


    def __init__(self, languageDef, renderedScene):
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
        self.__currentDocumentGeometry=QRectF()
        self.__currentDocumentResolution=1.0
        self.__currentLayer=None
        self.__currentLayerBounds=QRect()

        # -- default options values

        # debug mode by default is False
        # when True, execution is made step by step
        self.__optionDebugMode=False

        # verbose mode by default is False
        # when True, all action will generate a verbose information
        self.__optionVerboseMode=True

        # delay mode by default is 0
        # when set, a delay is applied between each instruction
        self.__optionDelay=0

        # default background properties for canvas
        self.__optionDefaulCanvasBackgroundFrom=BSInterpreter.OPTION_BACKGROUND_FROM_ACTIVE_LAYER
        self.__optionDefaulCanvasBackgroundFromColor=QColor(Qt.white)
        self.__optionDefaulCanvasBackgroundVisibility=True
        self.__optionDefaulCanvasBackgroundOpacity=1.0

        # default grid properties for canvas
        self.__optionDefaulCanvasGridVisibility=True
        self.__optionDefaulCanvasGridColor=QColor("#808080")
        self.__optionDefaulCanvasGridBgColor=QColor("#303030")
        self.__optionDefaulCanvasGridStyleMain='SOLID'
        self.__optionDefaulCanvasGridStyleSecondary='DOT'
        self.__optionDefaulCanvasGridOpacity=0.25
        self.__optionDefaulCanvasGridSizeWidth=10
        self.__optionDefaulCanvasGridSizeMain=5
        self.__optionDefaulCanvasGridSizeUnit='PX'

        # default rulers properties for canvas
        self.__optionDefaulCanvasRulersVisibility=True
        self.__optionDefaulCanvasRulersColor=QColor('#808080')
        self.__optionDefaulCanvasRulersBgColor=QColor('#303030')

        # default origin properties for canvas
        self.__optionDefaulCanvasOriginVisibility=True
        self.__optionDefaulCanvasOriginColor=QColor("#d51ba7")
        self.__optionDefaulCanvasOriginStyle='SOLID'
        self.__optionDefaulCanvasOriginOpacity=1.0
        self.__optionDefaulCanvasOriginSize=45
        self.__optionDefaulCanvasOriginPositionAbsissa='CENTER'
        self.__optionDefaulCanvasOriginPositionOrdinate='MIDDLE'

        # default position properties for canvas
        self.__optionDefaulCanvasPositionVisibility=True
        self.__optionDefaulCanvasPositionColor=QColor('#229922')
        self.__optionDefaulCanvasPositionOpacity=1.0
        self.__optionDefaulCanvasPositionSize=25.0
        self.__optionDefaulCanvasPositionFulfill=True
        self.__optionDefaulCanvasPositionAxis=False
        self.__optionDefaulCanvasPositionModel='BASIC'

        # define rendered scene, on which grid, origin, ... are drawn
        self.__renderedScene=renderedScene
        self.__renderedScene.propertyChanged.connect(lambda x: print(x))

    # --------------------------------------------------------------------------
    # utils methods
    # --------------------------------------------------------------------------
    def __escapeText(self, text, fmtCode=''):
        """Return escaped text"""
        returned=text

        if fmtCode=='':
            return returned
        else:
            lines=returned.split("\n")
            returned=[]
            for line in lines:
                tmpFmtCode=fmtCode
                if '***' in tmpFmtCode:
                    line=f"***{line}***"
                elif '**' in tmpFmtCode:
                    line=f"**{line}**"
                elif '*' in tmpFmtCode:
                    line=f"*{line}*"

                tmpFmtCode=tmpFmtCode.replace('*','')
                if tmpFmtCode!='':
                    line=f"#{tmpFmtCode}#{line}#"

                returned.append(line)

            return "\n".join(returned)

    def __formatVarName(self, value):
        """Format given variable name

        Example:
            'TEST'
            will return:
            '***&lt;TEST&gt;***'
        """
        return f'***&lt;{value}&gt;***'

    def __formatStoreResult(self, *values):
        """Format given variable name

        Examples:
            ':v1'
            will return:
            '#lk#*(Stored as variable **:v1**)*#'

            ':v1', ':v2'
            will return:
            '#lk#*(Stored as variables **:v1**, **:v2**)*#'
        """
        returned=[f"**{value}**" for value in values]
        if len(returned)>1:
            return f" #lk#*(Stored as variables {', '.join(returned)})*#"
        else:
            return f" #lk#*(Stored as variable {', '.join(returned)})*#"

    def __formatPosition(self, ast=None, lineNumber=None, endLine=' '):
        if not ast is None:
            position=ast.position()
            if position["from"]["row"]==position["to"]["row"]:
                return f"#w#line# #y#{position['from']['row']}#{endLine}"
            else:
                return f"#w#lines# #y#{position['from']['row']}##w#-##y#{position['to']['row']}#{endLine}"

        elif not lineNumber is None:
            return f"#w#line# #y#{lineNumber}#{endLine}"
        else:
            return ''


    def verbose(self, text, ast=None, cReturn=True):
        """If execution is defined as verbose, will print given text"""
        if not self.__optionVerboseMode:
            return

        msg=f'#c#Verbose# {self.__formatPosition(ast)}#lw#>># {self.__escapeText(text)}'
        data={}
        if isinstance(ast, ASTItem):
            data={'position': ast.position()}
        self.print(msg, WConsoleType.INFO, data, cReturn=cReturn)

    def warning(self, text, ast=None, cReturn=True):
        """Even if execution is not defined as verbose, will print given text as warning"""
        msg=f'#y#Warning# {self.__formatPosition(ast)}#lw#>># {self.__escapeText(text, "y*")}'
        data={}
        if isinstance(ast, ASTItem):
            data={'position': ast.position()}
        self.print(msg, WConsoleType.WARNING, data, cReturn=cReturn)

    def error(self, text, ast=None, cReturn=True):
        """Even if execution is not defined as verbose, will print given text as error"""
        msg=f'#r#Error# {self.__formatPosition(ast)}#lw#>># {self.__escapeText(text, "r*")}'
        data={}
        if isinstance(ast, ASTItem):
            data={'position': ast.position()}
        self.print(msg, WConsoleType.ERROR, data, cReturn=cReturn)

    def valid(self, text, ast=None, cReturn=True):
        """Even if execution is not defined as verbose, will print given text as valid"""
        msg=f'#g#Information# {self.__formatPosition(ast)}#lw#>># {self.__escapeText(text, "g*")}'
        data={}
        if isinstance(ast, ASTItem):
            data={'position': ast.position()}
        self.print(msg, WConsoleType.VALID, data, cReturn=cReturn)

    def print(self, text, type=WConsoleType.NORMAL, data={}, cReturn=True):
        """Print text to console"""
        if not isinstance(data, dict):
            data={}
        self.output.emit(self.__escapeText(text), type, data, cReturn)

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
            raise EInterpreter(f"{fctLabel}: invalid type for argument {self.__formatVarName(name)}", currentAst)

    def __checkParamDomain(self, currentAst, fctLabel, name, controlOk, msg, raiseException=True):
        """raise an exception if value is not in expected domain"""
        if not controlOk:
            if raiseException:
                raise EInterpreter(f"{fctLabel}: invalid domain for argument {self.__formatVarName(name)}, {msg}", currentAst)
            else:
                self.warning(f"{fctLabel}: invalid domain for argument {self.__formatVarName(name)}, {msg}", currentAst)
        return controlOk

    def __checkOption(self, currentAst, fctLabel, value, forceRaise=False):
        """raise an exception is value if not of given type"""
        if not isinstance(value, ASTItem) or forceRaise:
            raise EInterpreter(f"{fctLabel}: invalid/unknown option provided", currentAst)

    def __strValue(self, variableValue):
        """Return formatted string value"""
        if isinstance(variableValue, QColor):
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

    def __valueTypeFromName(self, name):
        """Return value type"""
        if name=='str':
            return "STRING"
        elif name=='int':
            return "INTEGER"
        elif name=='float':
            return "DECIMAL"
        elif name=='list':
            return "LIST"
        elif name=='bool':
            return "SWITCH"
        elif name=='QColor':
            return "COLOR"
        elif name is None or name=='NoneType':
            return "NONE"
        else:
            return "UNKNOWN"

    def __valueType(self, value):
        """Return value type"""
        if isinstance(value, str):
            return "STRING"
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "DECIMAL"
        elif isinstance(value, list):
            return "LIST"
        elif isinstance(value, bool):
            return "SWITCH"
        elif isinstance(value, QColor):
            return "COLOR"
        elif value is None:
            return "NONE"
        else:
            return "UNKNOWN"

    # --------------------------------------------------------------------------
    # Script execution methods
    # --------------------------------------------------------------------------
    def __executeStart(self, reset):
        """Execute from root AST"""
        if reset:
            self.__macroDefinitions.clear()
            self.__scriptBlockStack.clear()

        # convenience variable on current document
        self.__currentDocument=Krita.instance().activeDocument()
        if self.__currentDocument is None:
            raise EInterpreter("No active document!", None)

        self.__currentDocumentBounds=self.__currentDocument.bounds()
        # assume x/y resolution are the same
        # can't use Document.resolution() as it returns an integer value and value
        # is not correct if resolution is defined with decimal properties
        self.__currentDocumentResolution=self.__currentDocument.xRes()

        # convenience variable on current active layer
        # note: current layer might be changed by executed script and then the
        #       variables might be updated
        self.__currentLayer=self.__currentDocument.activeNode()
        self.__currentLayerBounds=self.__currentLayer.bounds()

        # initialise execution environment
        self.__renderedScene.setDocumentBounds(self.__currentDocumentBounds)
        self.__updateGeometry()

        if reset:
            # -- canvas configuration                                               # --- Option to implement ---
            self.__setCanvasGridVisible(self.__optionDefaulCanvasGridVisibility)
            self.__setCanvasGridColor(self.__optionDefaulCanvasGridColor)
            self.__setCanvasGridBgColor(self.__optionDefaulCanvasGridBgColor)
            self.__setCanvasGridStyleMain(self.__optionDefaulCanvasGridStyleMain)
            self.__setCanvasGridStyleSecondary(self.__optionDefaulCanvasGridStyleSecondary)
            self.__setCanvasGridOpacity(self.__optionDefaulCanvasGridOpacity)
            self.__setCanvasGridSize(self.__optionDefaulCanvasGridSizeWidth, self.__optionDefaulCanvasGridSizeMain, self.__optionDefaulCanvasGridSizeUnit)

            self.__setCanvasRulersVisible(self.__optionDefaulCanvasRulersVisibility)
            self.__setCanvasRulersColor(self.__optionDefaulCanvasRulersColor)
            self.__setCanvasRulersBgColor(self.__optionDefaulCanvasRulersBgColor)

            self.__setCanvasOriginVisible(self.__optionDefaulCanvasOriginVisibility)
            self.__setCanvasOriginColor(self.__optionDefaulCanvasOriginColor)
            self.__setCanvasOriginStyle(self.__optionDefaulCanvasOriginStyle)
            self.__setCanvasOriginOpacity(self.__optionDefaulCanvasOriginOpacity)
            self.__setCanvasOriginSize(self.__optionDefaulCanvasOriginSize)
            self.__setCanvasOriginPosition(self.__optionDefaulCanvasOriginPositionAbsissa, self.__optionDefaulCanvasOriginPositionOrdinate)

            self.__setCanvasPositionVisible(self.__optionDefaulCanvasPositionVisibility)
            self.__setCanvasPositionColor(self.__optionDefaulCanvasPositionColor)
            self.__setCanvasPositionOpacity(self.__optionDefaulCanvasPositionOpacity)
            self.__setCanvasPositionSize(self.__optionDefaulCanvasPositionSize)
            self.__setCanvasPositionFulfill(self.__optionDefaulCanvasPositionFulfill)
            self.__setCanvasPositionAxis(self.__optionDefaulCanvasPositionAxis)
            self.__setCanvasPositionModel(self.__optionDefaulCanvasPositionModel)

            self.__setCanvasBackgroundVisible(self.__optionDefaulCanvasBackgroundVisibility)
            self.__setCanvasBackgroundOpacity(self.__optionDefaulCanvasBackgroundOpacity)
            if self.__optionDefaulCanvasBackgroundFrom==BSInterpreter.OPTION_BACKGROUND_FROM_ACTIVE_LAYER:
                self.__setCanvasBackgroundFromLayerActive()
            elif self.__optionDefaulCanvasBackgroundFrom==BSInterpreter.OPTION_BACKGROUND_FROM_DOCUMENT:
                self.__setCanvasBackgroundFromDocument()
            elif self.__optionDefaulCanvasBackgroundFrom==BSInterpreter.OPTION_BACKGROUND_FROM_COLOR:
                self.__setCanvasBackgroundFromColor(self.__optionDefaulCanvasBackgroundFromColor)


            # -- default environment initialisation:
            #       hardcoded to ensure that default values are always the same for everyone
            #       let user's define default value they're prefering through scripting
            self.__setUnitRotation('DEGREE')
            self.__setUnitCanvas('PX')

            self.__setPenColor(QColor(Qt.black))
            self.__setPenSize(5.0)
            self.__setPenStyle('SOLID')
            self.__setPenCap('FLAT')
            self.__setPenJoin('MITTER')
            self.__setPenOpacity(True)

            self.__setFillColor(QColor(Qt.black))
            self.__setFillRule('EVEN')
            self.__setFillOpacity(False)

            self.__setTextColor(QColor(Qt.black))
            self.__setTextOpacity(1.0)
            self.__setTextFont("Helvetica")
            self.__setTextSize(25)
            self.__setTextBold(False)
            self.__setTextItalic(False)
            self.__setTextOutline(False)
            self.__setTextLetterSpacing(100.0, 'PCT')
            self.__setTextStretch(100.0)
            self.__setTextHAlignment('LEFT')
            self.__setTextVAlignment('TOP')

            self.__setDrawAntialiasing(True)
            self.__setDrawBlending('NORMAL')
            self.__setDrawShapeStatus(False)

            # -- misc initialisation
            self.__setExecutionVerbose(self.__optionVerboseMode)
            self.__setRandomizeSeed()

            # -- default configuration                                                > Default option value to implement
            ###':position.x':                      0.0,
            ###':position.y':                      0.0,
            ###':angle':                           0.0,

        self.__renderedScene.setBackgroundImage(EKritaNode.toQPixmap(self.__currentLayer), self.__currentLayerBounds)

        self.valid(f"**Start script execution**# #w#[##lw#*{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}*##w#]")
        if self.__astRoot.id()==ASTSpecialItemType.ROOT:
            startTime=time.time()
            try:
                returned=self.__executeAst(self.__astRoot)
                totalTime=round(time.time()-startTime,4)
                self.valid(f"**Script executed**# #w#[Executed in# #lw#*{totalTime}s*##w#]")
                return returned
            except EInterpreter as e:
                if e.errorLevel()==EInterpreter.ERROR_LEVEL_STOP:
                    totalTime=round(time.time()-startTime, 4)
                    raise EInterpreter(f"{str(e)}\nInformation# #lw#>># #lg#**Script executed **# #w#[Executed in# #lw#*{totalTime}s*##w#]", e.ast(), EInterpreter.ERROR_LEVEL_STOP)
                raise e
            except Exception as e:
                raise e

        raise EInterpreterInternalError("Invalid ROOT", self.__astRoot)

    def __executeAst(self, currentAst):
        """Execute current given AST"""

        # ----------------------------------------------------------------------
        # ROOT
        # ----
        if currentAst.id() == ASTSpecialItemType.ROOT:
            # given AST is the main block of instructions
            # initialise reserved 'constant' variables
            predefinedVariables={
                    ':math.pi':                         math.pi,
                    ':math.e':                          math.e,
                    ':math.phi':                        1.618033988749895
                }
            return self.__executeScriptBlock(currentAst, True, "Main script", predefinedVariables)

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
        elif currentAst.id() == 'Flow_Import_Image_From_File':
            return self.__executeFlowImportImageFromFile(currentAst)
        elif currentAst.id() == 'Flow_Import_Image_From_LayerName':
            return self.__executeFlowImportImageFromLayerName(currentAst)
        elif currentAst.id() == 'Flow_Import_Image_From_LayerId':
            return self.__executeFlowImportImageFromLayerId(currentAst)
        elif currentAst.id() == 'Flow_Import_Image_From_LayerCurrent':
            return self.__executeFlowImportImageFromLayerCurrent(currentAst)
        elif currentAst.id() == 'Flow_Import_Image_From_Document':
            return self.__executeFlowImportImageFromDocument(currentAst)
        elif currentAst.id() == 'Flow_Import_Image_From_Canvas':
            return self.__executeFlowImportImageFromCanvas(currentAst)

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
        elif currentAst.id() == 'Action_Set_Draw_Opacity':
            return self.__executeActionSetDrawOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Color':
            return self.__executeActionSetCanvasGridColor(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Style':
            return self.__executeActionSetCanvasGridStyle(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Opacity':
            return self.__executeActionSetCanvasGridOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Grid_Size':
            return self.__executeActionSetCanvasGridSize(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Rulers_Color':
            return self.__executeActionSetCanvasRulersColor(currentAst)
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
        elif currentAst.id() == 'Action_Set_Canvas_Position_Axis':
            return self.__executeActionSetCanvasPositionAxis(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Position_Model':
            return self.__executeActionSetCanvasPositionModel(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_Opacity':
            return self.__executeActionSetCanvasBackgroundOpacity(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_From_Color':
            return self.__executeActionSetCanvasBackgroundFromColor(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_From_Document':
            return self.__executeActionSetCanvasBackgroundFromDocument(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_From_Layer_Id':
            return self.__executeActionSetCanvasBackgroundFromLayerId(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_From_Layer_Name':
            return self.__executeActionSetCanvasBackgroundFromLayerName(currentAst)
        elif currentAst.id() == 'Action_Set_Canvas_Background_From_Layer_Active':
            return self.__executeActionSetCanvasBackgroundFromLayerActive(currentAst)
        elif currentAst.id() == 'Action_Set_Script_Execution_Verbose':
            return self.__executeActionSetExecutionVerbose(currentAst)
        elif currentAst.id() == 'Action_Set_Script_Randomize_Seed':
            return self.__executeActionSetRandomizeSeed(currentAst)
        elif currentAst.id() == 'Action_Draw_Shape_Line':
            return self.__executeActionDrawShapeLine(currentAst)
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
        elif currentAst.id() == 'Action_Draw_Misc_Fill_Canvas_From_Color':
            return self.__executeActionDrawMiscFillCanvasFromColor(currentAst)
        elif currentAst.id() == 'Action_Draw_Misc_Fill_Canvas_From_Image':
            return self.__executeActionDrawMiscFillCanvasFromImage(currentAst)
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
        elif currentAst.id() == 'Action_Canvas_Show_Rulers':
            return self.__executeActionCanvasShowRulers(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Grid':
            return self.__executeActionCanvasHideGrid(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Origin':
            return self.__executeActionCanvasHideOrigin(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Position':
            return self.__executeActionCanvasHidePosition(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Background':
            return self.__executeActionCanvasHideBackground(currentAst)
        elif currentAst.id() == 'Action_Canvas_Hide_Rulers':
            return self.__executeActionCanvasHideRulers(currentAst)
        elif currentAst.id() == 'Action_UIConsole_Print':
            return self.__executeActionUIConsolePrint(currentAst)
        elif currentAst.id() == 'Action_UIConsole_Print_Formatted':
            return self.__executeActionUIConsolePrint(currentAst, formatted=True)
        elif currentAst.id() == 'Action_UIConsole_Print_Error':
            return self.__executeActionUIConsolePrint(currentAst, consoleType=WConsoleType.ERROR)
        elif currentAst.id() == 'Action_UIConsole_Print_Warning':
            return self.__executeActionUIConsolePrint(currentAst, consoleType=WConsoleType.WARNING)
        elif currentAst.id() == 'Action_UIConsole_Print_Verbose':
            return self.__executeActionUIConsolePrint(currentAst, consoleType=WConsoleType.INFO)
        elif currentAst.id() == 'Action_UIConsole_Print_Valid':
            return self.__executeActionUIConsolePrint(currentAst, consoleType=WConsoleType.VALID)
        elif currentAst.id() == 'Action_UIConsole_Print_Formatted_Error':
            return self.__executeActionUIConsolePrint(currentAst, formatted=True, consoleType=WConsoleType.ERROR)
        elif currentAst.id() == 'Action_UIConsole_Print_Formatted_Warning':
            return self.__executeActionUIConsolePrint(currentAst, formatted=True, consoleType=WConsoleType.WARNING)
        elif currentAst.id() == 'Action_UIConsole_Print_Formatted_Verbose':
            return self.__executeActionUIConsolePrint(currentAst, formatted=True, consoleType=WConsoleType.INFO)
        elif currentAst.id() == 'Action_UIConsole_Print_Formatted_Valid':
            return self.__executeActionUIConsolePrint(currentAst, formatted=True, consoleType=WConsoleType.VALID)
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
        elif currentAst.id() == 'List_Index_Expression':
            return self.__executeListIndexExpression(currentAst)

        # ----------------------------------------------------------------------
        # Operators
        # ---------
        elif currentAst.id() == ASTSpecialItemType.UNARY_OPERATOR:
            return self.__executeUnaryOperator(currentAst)
        elif currentAst.id() == ASTSpecialItemType.BINARY_OPERATOR:
            return self.__executeBinaryOperator(currentAst)
        elif currentAst.id() == ASTSpecialItemType.INDEX_OPERATOR:
            return self.__executeIndexOperator(currentAst)

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

        self.verbose(f"Enter scriptblock: '{name}'", currentAst)
        self.__scriptBlockStack.push(currentAst, allowLocalVariable, name)

        if isinstance(createLocalVariables, dict):
            # create local variables if any provided before starting block execution
            for variableName in createLocalVariables:
                self.__scriptBlockStack.setVariable(variableName, createLocalVariables[variableName], BSVariableScope.LOCAL)

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
        self.verbose(f"Exit scriptblock: '{name}'", currentAst)

        return returned


    # --------------------------------------------------------------------------
    # Flows
    # --------------------------------------------------------------------------
    def __executeFlowSetVariable(self, currentAst):
        """Set a variable in current script block"""
        # Defined by 2 nodes:
        #   0: global/local variable
        #   1: variable name (<Token>)
        #   2: variable value (<Token> or <ASTItem>)
        variableLocalScope=(currentAst.node(0).value()=='set variable')
        variableName=currentAst.node(1).value()
        variableValue=self.__evaluate(currentAst.node(2))

        if not variableLocalScope:
            globalVar='global '
            scope=BSVariableScope.GLOBAL
        else:
            globalVar=''
            scope=BSVariableScope.CURRENT



        self.verbose(f"set {globalVar}variable {variableName}={self.__strValue(variableValue)}", currentAst)

        self.__scriptBlockStack.setVariable(variableName, variableValue, scope)

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
            self.verbose(f"Define macro '{macroName}'", currentAst)
        else:
            self.verbose(f"Define macro '{macroName}' with parameters {' '.join(variables)}", currentAst)

        if self.__macroDefinitions.alreadyDefined(macroName):
            self.warning(f"Macro with name '{macroName}' has been overrided", self.__macroDefinitions.get(macroName).ast())

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
        fctLabel='Flow ***call macro***'

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


        self.__checkParamType(currentAst, fctLabel, 'MACRO', macroName, str)

        macroDefinition=self.__macroDefinitions.get(macroName)
        self.__checkParamDomain(currentAst, fctLabel, 'MACRO', not macroDefinition is None, f"no macro matching given name '{macroName}' found")

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
        self.verbose(verboseText, currentAst)

        storeResultValue=self.__executeScriptBlock(macroDefinition.ast(), True, f"Macro: {macroName}", localVariables)

        if isinstance(storeResultName, str):
            self.__scriptBlockStack.setVariable(storeResultName, storeResultValue, BSVariableScope.CURRENT)

        return storeResultValue

    def __executeFlowReturn(self, currentAst):
        """return

        Return given value or False if no value is provided
        """
        fctLabel='Flow ***return***'
        self.__checkParamNumber(currentAst, fctLabel, 0, 1)

        returned=False

        if len(currentAst.nodes())>0:
            returned=self.__evaluate(currentAst.node(0))

        self.verbose(f"return {self.__strValue(returned)}", currentAst)

        #self.__delay()
        return returned

    def __executeFlowIfElseIf(self, currentAst, mode='if'):
        """if <condition> then

        Execute a scriptblock if condition is met
        """
        fctLabel='Flow ***if ... then***'

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

        self.verbose(verboseText, currentAst)

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
        fctLabel='Flow ***else ...***'

        # 1st parameter: scriptblock to execute
        self.__checkParamNumber(currentAst, fctLabel, 1)

        self.verbose('else ...', currentAst)
        self.__executeScriptBlock(currentAst.node(0), False, 'else')

        #self.__delay()
        return None

    def __executeFlowRepeat(self, currentAst):
        """repeat <COUNT> times

        Execute a repeat loop
        """
        fctLabel='Flow ***repeat *<COUNT>* times***'

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

        self.__checkParamType(currentAst, fctLabel, 'COUNT', repeatTotal, int)

        if not self.__checkParamDomain(currentAst, fctLabel, 'COUNT', repeatTotal>=0, f"Can't repeat negative value (count={repeatTotal})", False):
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
                    ':repeat.totalIteration': repeatTotal,
                    ':repeat.currentIteration': repeatCurrent+1,
                    ':repeat.isFirstIteration': (repeatCurrent==0),
                    ':repeat.isLastIteration': (repeatCurrent==repeatTotal-1),
                    ':repeat.incAngle': repeatIncAngle,
                    ':repeat.currentAngle': repeatCurrentAngle
                }

            self.__executeScriptBlock(astScriptBlock, False, scriptBlockName, loopVariables)

            repeatCurrentAngle+=repeatIncAngle

        return None

    def __executeFlowForEach(self, currentAst):
        """for each <variable> in <list>

        Do loop over items in list
        """
        fctLabel='Flow ***for each ... in ...***'

        # 1st parameter: source list
        # 2nd parameter: target variable
        # 3rd parameter: scriptblock to execute
        self.__checkParamNumber(currentAst, fctLabel, 3)

        forEachList=self.__evaluate(currentAst.node(0))
        forVarName=currentAst.node(1).value()
        astScriptBlock=currentAst.node(2)


        self.__checkParamType(currentAst, fctLabel, 'LIST', forEachList, list, str)

        if isinstance(forEachList, str):
            forEachList=[c for c in forEachList]

        if len(forEachList)>5:
            scriptBlockName=f'for each item from {forEachList[0:5]} as {forVarName} do'.replace(']', ', ...]')
        else:
            scriptBlockName=f'for each item from {forEachList} as {forVarName} do'

        # define loop variable
        forEachTotal=len(forEachList)
        if forEachTotal>0:
            forEachIncAngle=360/forEachTotal
        else:
            forEachIncAngle=0

        forEachCurrentAngle=0
        for index, forEachCurrentValue in enumerate(forEachList):
            loopVariables={
                    ':foreach.totalIteration': forEachTotal,
                    ':foreach.currentIteration': index+1,
                    ':foreach.isFirstIteration': (index==0),
                    ':foreach.isLastIteration': (index==forEachTotal-1),
                    ':foreach.incAngle': forEachIncAngle,
                    ':foreach.currentAngle': forEachCurrentAngle,
                    forVarName: forEachCurrentValue
                }

            self.__executeScriptBlock(astScriptBlock, False, scriptBlockName, loopVariables)

            forEachCurrentAngle+=forEachIncAngle

        return None

    def __executeFlowImportImageFromFile(self, currentAst):
        """import file into image library from

        Import a file in image library
        """
        fctLabel='Flow ***import file into image library from***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 2)

        sourceName=self.__evaluate(currentAst.node(0))
        targetName=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'FILE-NAME', sourceName, str)
        self.__checkParamType(currentAst, fctLabel, 'RESOURCE-NAME', targetName, str)

        self.__checkParamDomain(currentAst, fctLabel, 'FILE-NAME', sourceName!='', "File name can't be empty string")
        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")


        self.verbose(f"import file into image library from *'{self.__strValue(sourceName)}'* as *'{self.__strValue(targetName)}'*", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}*", currentAst)

        currentPath=os.path.dirname(os.path.normpath(os.path.expanduser("sourceName")))
        if currentPath == '':
            # file name only => need to search in current path
            if not self.__scriptSourceFileName is None:
                scriptSourcePath=os.path.dirname(os.path.normpath(os.path.expanduser(self.__scriptSourceFileName)))
            else:
                scriptSourcePath=os.path.normpath(os.path.expanduser("~"))

            sourceFileName=os.path.join(scriptSourcePath, sourceName)
        else:
            sourceFileName=sourceName

        sourceFileName=os.path.normpath(sourceFileName)

        if os.path.exists(sourceFileName):
            returned=self.__loadImage(targetName, f"file:{sourceFileName}")
            if not returned[0]:
                self.warning(f"Can't load image file into library: *{self.__strValue(sourceFileName)}*", currentAst)
                self.warning(returned[1], currentAst)
            else:
                self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}*", currentAst)
        else:
            self.warning(f"Can't load image file into library: *{self.__strValue(sourceFileName)}*", currentAst)
            self.warning("File not found", currentAst)


        return None

    def __executeFlowImportImageFromLayerName(self, currentAst):
        """import layer into image library from name

        Import a layer in image library
        """
        fctLabel='Flow ***import layer into image library from name***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 2)

        sourceName=self.__evaluate(currentAst.node(0))
        targetName=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'LAYER-NAME', sourceName, str)
        self.__checkParamType(currentAst, fctLabel, 'RESOURCE-NAME', targetName, str)

        self.__checkParamDomain(currentAst, fctLabel, 'LAYER-NAME', sourceName!='', "Layer name can't be empty string")
        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")

        self.verbose(f"import layer into image library from name *'{self.__strValue(sourceName)}'* as *'{self.__strValue(targetName)}'* ", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}* ", currentAst)

        returned=self.__loadImage(targetName, f"layer:name:{sourceName}")
        if not returned[0]:
            self.warning(f"Can't load layer into library: *{self.__strValue(sourceName)}* ", currentAst)
            self.warning(returned[1], currentAst)
        else:
            self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}* ", currentAst)

        return None

    def __executeFlowImportImageFromLayerId(self, currentAst):
        """import layer into image library from id

        Import a layer in image library
        """
        fctLabel='Flow ***import layer into image library from id***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 2)

        sourceName=self.__evaluate(currentAst.node(0))
        targetName=self.__evaluate(currentAst.node(1))

        self.__checkParamDomain(currentAst, fctLabel, 'LAYER-ID', sourceName!='', "Layer identifier can't be empty string")
        self.__checkParamDomain(currentAst, fctLabel, 'LAYER-ID', re.match('\d{8}-\d{4}-\d{4}-\d{4}-\d{12}|\{\d{8}-\d{4}-\d{4}-\d{4}-\d{12}\}', sourceName), "Invalid format for layer identifier")
        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")

        self.verbose(f"import layer into image library from id *'{self.__strValue(sourceName)}'* as *'{self.__strValue(targetName)}'* ", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}* ", currentAst)

        returned=self.__loadImage(targetName, f"layer:id:{sourceName}")
        if not returned[0]:
            self.warning(f"Can't load layer into library: *{self.__strValue(sourceName)}* ", currentAst)
            self.warning(returned[1], currentAst)
        else:
            self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}* ", currentAst)

        return None

    def __executeFlowImportImageFromLayerCurrent(self, currentAst):
        """import layer into image library from current

        Import current layer in image library
        """
        fctLabel='Flow ***import layer into image library from current***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 1)

        targetName=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")

        self.verbose(f"import layer into image library from current as *'{self.__strValue(targetName)}'* ", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}*", currentAst)

        returned=self.__loadImage(targetName, f"layer:current")
        if not returned[0]:
            self.warning(f"Can't load current layer into library", currentAst)
            self.warning(returned[1], currentAst)
        else:
            self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}* ", currentAst)

        return None

    def __executeFlowImportImageFromDocument(self, currentAst):
        """import document into image library

        Import current document in image library
        """
        fctLabel='Flow ***import document into image library***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 1)

        targetName=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")

        self.verbose(f"import document into image library as *'{self.__strValue(targetName)}'* ", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}* ", currentAst)

        returned=self.__loadImage(targetName, f"document:")
        if not returned[0]:
            self.warning(f"Can't load current document into library", currentAst)
            self.warning(returned[1], currentAst)
        else:
            self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}* ", currentAst)

        return None

    def __executeFlowImportImageFromCanvas(self, currentAst):
        """import canvas into image library

        Import current canvas in image library
        """
        fctLabel='Flow ***import canvas into image library***'

        # 1st parameter: file name
        # 2nd parameter: resource name
        self.__checkParamNumber(currentAst, fctLabel, 1)

        targetName=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'RESOURCE-NAME', targetName!='', "Resource name can't be empty string")

        self.verbose(f"import canvas into image library as *'{self.__strValue(targetName)}'*", currentAst)
        if self.__imagesLibrary.alreadyDefined(targetName):
            self.verbose(f"> Will replace current content for *{self.__strValue(targetName)}*", currentAst)

        returned=self.__loadImage(targetName, f"canvas:")
        if not returned[0]:
            self.warning(f"Can't load current canvas into library", currentAst)
            self.warning(returned[1], currentAst)
        else:
            self.verbose(f"Image loaded: *{self.__strValue(returned[1])}x{self.__strValue(returned[2])}*", currentAst)

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
        fctLabel='Action ***set unit canvas***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', value in BSInterpreter.CONST_MEASURE_UNIT, f"coordinates & measures unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"set unit canvas {self.__strValue(value)}{self.__formatStoreResult(':unit.canvas')}", currentAst)

        self.__setUnitCanvas(value)

        self.__delay()
        return None

    def __executeActionSetUnitRotation(self, currentAst):
        """Set canvas unit

        :unit.rotation
        """
        fctLabel='Action ***set unit rotation***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', value in BSInterpreter.CONST_ROTATION_UNIT, f"angle unit value for rotation can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.verbose(f"set unit rotation {self.__strValue(value)}{self.__formatStoreResult(':unit.rotation')}", currentAst)

        self.__setUnitRotation(value)

        self.__delay()
        return None

    def __executeActionSetPenColor(self, currentAst):
        """Set pen color

        :pen.color
        """
        fctLabel='Action ***set pen color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set pen color {self.__strValue(value)}{self.__formatStoreResult(':pen.color')}", currentAst)

        self.__setPenColor(value)

        self.__delay()
        return None

    def __executeActionSetPenSize(self, currentAst):
        """Set pen size

        :pen.size
        """
        fctLabel='Action ***set pen size***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'SIZE', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'SIZE', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.verbose(f"set pen size {self.__strValue(value)} {self.__strValue(unit)}{self.__formatStoreResult(':pen.size')}", currentAst)
        else:
            self.verbose(f"set pen size {self.__strValue(value)}{self.__formatStoreResult(':pen.size')}", currentAst)

        self.__setPenSize(value, unit)

        self.__delay()
        return None

    def __executeActionSetPenStyle(self, currentAst):
        """Set pen style

        :pen.style
        """
        fctLabel='Action ***set pen style***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'STYLE', value in BSInterpreter.CONST_PEN_STYLE, f"style value for pen can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.verbose(f"set pen style {self.__strValue(value)}{self.__formatStoreResult(':pen.style')}", currentAst)

        self.__setPenStyle(value)

        self.__delay()
        return None

    def __executeActionSetPenCap(self, currentAst):
        """Set pen cap

        :pen.cap
        """
        fctLabel='Action ***set pen cap***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'CAP', value in BSInterpreter.CONST_PEN_CAP, f"cap value for pen can be: {', '.join(BSInterpreter.CONST_PEN_CAP)}")

        self.verbose(f"set pen cap {self.__strValue(value)}{self.__formatStoreResult(':pen.cap')}", currentAst)

        self.__setPenCap(value)

        self.__delay()
        return None

    def __executeActionSetPenJoin(self, currentAst):
        """Set pen join

        :pen.join
        """
        fctLabel='Action ***set pen join***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'JOIN', value in BSInterpreter.CONST_PEN_JOIN, f"join value for pen can be: {', '.join(BSInterpreter.CONST_PEN_JOIN)}")

        self.verbose(f"set pen join {self.__strValue(value)}{self.__formatStoreResult(':pen.join')}", currentAst)

        self.__setPenJoin(value)

        self.__delay()
        return None

    def __executeActionSetPenOpacity(self, currentAst):
        """Set pen opacity

        :pen.color
        """
        fctLabel='Action ***set pen opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set pen opacity {self.__strValue(value)}{self.__formatStoreResult(':pen.color')}", currentAst)

        self.__setPenOpacity(value)

        self.__delay()
        return None

    def __executeActionSetFillColor(self, currentAst):
        """Set fill color

        :fill.color
        """
        fctLabel='Action ***set fill color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set fill color {self.__strValue(value)}{self.__formatStoreResult(':fill.color')}", currentAst)

        self.__setFillColor(value)

        self.__delay()
        return None

    def __executeActionSetFillRule(self, currentAst):
        """Set fill rule

        :fill.rule
        """
        fctLabel='Action ***set fill rule***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'RULE', value in BSInterpreter.CONST_FILL_RULE, f"rule value for fill can be: {', '.join(BSInterpreter.CONST_FILL_RULE)}")

        self.verbose(f"set fill rule {self.__strValue(value)}{self.__formatStoreResult(':fill.rule')}", currentAst)

        self.__setFillRule(value)

        self.__delay()
        return None

    def __executeActionSetFillOpacity(self, currentAst):
        """Set fill opacity

        :fill.color
        """
        fctLabel='Action ***set fill opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set fill opacity {self.__strValue(value)}{self.__formatStoreResult(':fill.color')}", currentAst)

        self.__setFillOpacity(value)

        self.__delay()
        return None

    def __executeActionSetTextColor(self, currentAst):
        """Set text color

        :text.color
        """
        fctLabel='Action ***set text color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set text color {self.__strValue(value)}{self.__formatStoreResult(':text.color')}", currentAst)

        self.__setTextColor(value)

        self.__delay()
        return None

    def __executeActionSetTextOpacity(self, currentAst):
        """Set text opacity

        :text.color
        """
        fctLabel='Action ***set text opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set text opacity {self.__strValue(value)}{self.__formatStoreResult(':text.color')}", currentAst)

        self.__setTextOpacity(value)

        self.__delay()
        return None

    def __executeActionSetTextFont(self, currentAst):
        """Set text font

        :text.font
        """
        fctLabel='Action ***set text font***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'FONT', value, str)

        self.verbose(f"set text font {self.__strValue(value)}{self.__formatStoreResult(':text.font')}", currentAst)

        self.__setTextFont(value)

        self.__delay()
        return None

    def __executeActionSetTextSize(self, currentAst):
        """Set text size

        :text.size
        """
        fctLabel='Action ***set text size***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'SIZE', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'SIZE', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.verbose(f"set text size {self.__strValue(value)} {self.__strValue(unit)}{self.__formatStoreResult(':text.size')}", currentAst)
        else:
            self.verbose(f"set text size {self.__strValue(value)}{self.__formatStoreResult(':text.size')}", currentAst)

        self.__setTextSize(value, unit)

        self.__delay()
        return None

    def __executeActionSetTextBold(self, currentAst):
        """Set text bold

        :text.bold
        """
        fctLabel='Action ***set text bold***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set text bold {self.__strValue(value)}{self.__formatStoreResult(':text.bold')}", currentAst)

        self.__setTextBold(value)

        self.__delay()
        return None

    def __executeActionSetTextItalic(self, currentAst):
        """Set text italic

        :text.italic
        """
        fctLabel='Action ***set text italic***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set text italic {self.__strValue(value)}{self.__formatStoreResult(':text.italic')}", currentAst)

        self.__setTextItalic(value)

        self.__delay()
        return None

    def __executeActionSetTextLetterSpacing(self, currentAst):
        """Set text letter spacing

        :text.letterSpacing.spacing
        :text.letterSpacing.unit
        """
        fctLabel='Action ***set text letter spacing***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'SPACING', value, int, float)

        if unit=='PCT':
            # in this case, relative to text letter spacing base (not document dimension)
            if not self.__checkParamDomain(currentAst, fctLabel, 'SPACING', value>0, f"a non-zero positive number is expected when expressed in percentage (current={value})", False):
                # if value<=0, force to 0.1 (non blocking)
                value=max(1, value)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"letter spacing unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"set text letter spacing {self.__strValue(value)} {self.__strValue(unit)}{self.__formatStoreResult(':text.letterSpacing.spacing', 'text.letterSpacing.unit')}", currentAst)

        self.__setTextLetterSpacing(value, unit)

        self.__delay()
        return None

    def __executeActionSetTextStretch(self, currentAst):
        """Set text stretch

        :text.stretch
        """
        fctLabel='Action ***set text stretch***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'STRETCH', value, int, float)

        if isinstance(value, int):
            # from 1 to 4000
            if not self.__checkParamDomain(currentAst, fctLabel, 'STRETCH', value>0 and value<=4000, f"allowed stretch value when provided as an integer number is range [1;4000] (current={value})", False):
                value=min(4000, max(1, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'STRETCH', value>0 and value<=40, f"allowed stretch value when provided as a decimal number is range [0.01;40] (current={value})", False):
                value=min(40.0, max(1.0, value))
            value=round(value*100)

        self.__setTextStretch(value)

        self.__delay()
        return None

    def __executeActionSetTextHAlignment(self, currentAst):
        """Set text horizontal alignment

        :text.alignment.horizontal
        """
        fctLabel='Action ***set text horizontal alignment***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'H-ALIGNMENT', value in BSInterpreter.CONST_HALIGN, f"text horizontal alignment value can be: {', '.join(BSInterpreter.CONST_HALIGN)}")

        self.verbose(f"set text horizontal alignment {self.__strValue(value)}{self.__formatStoreResult(':text.alignment.horizontal')}", currentAst)

        self.__setTextHAlignment(value)

        self.__delay()
        return None

    def __executeActionSetTextVAlignment(self, currentAst):
        """Set text vertical alignment

        :text.alignment.vertical
        """
        fctLabel='Action ***set text vertical alignment***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'V-ALIGNMENT', value in BSInterpreter.CONST_VALIGN, f"text vertical alignment value can be: {', '.join(BSInterpreter.CONST_VALIGN)}")

        self.verbose(f"set text vertical alignment {self.__strValue(value)}{self.__formatStoreResult(':text.alignment.vertical')}", currentAst)

        self.__setTextVAlignment(value)

        self.__delay()
        return None

    def __executeActionSetDrawAntialiasing(self, currentAst):
        """Set draw antialiasing

        :draw.antialiasing
        """
        fctLabel='Action ***set draw antialiasing***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set draw antialiasing {self.__strValue(value)}{self.__formatStoreResult(':draw.antialiasing')}", currentAst)

        self.__setDrawAntialiasing(value)

        self.__delay()
        return None

    def __executeActionSetDrawBlending(self, currentAst):
        """Set draw blending mode

        :draw.blendingMode
        """
        fctLabel='Action ***set draw blending mode***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'BLENDING-MODE', value in BSInterpreter.CONST_DRAW_BLENDING_MODE, f"blending mode value can be: {', '.join(BSInterpreter.CONST_DRAW_BLENDING_MODE)}")

        self.verbose(f"set draw blending mode {self.__strValue(value)}{self.__formatStoreResult(':draw.blendingMode')}", currentAst)

        self.__setDrawBlending(value)

        self.__delay()
        return None

    def __executeActionSetDrawOpacity(self, currentAst):
        """Set draw opacity

        :draw.opacity
        """
        fctLabel='Action ***set draw opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        self.verbose(f"set draw opacity {self.__strValue(value)}{self.__formatStoreResult(':draw.opacity')}", currentAst)


        self.__delay()
        return None

    def __executeActionSetCanvasGridColor(self, currentAst):
        """Set canvas grid color

        :canvas.grid.color
        :canvas.grid.bgColor
        """
        fctLabel='Action ***set canvas grid color***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)
        value=self.__evaluate(currentAst.node(0))
        valueBg=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)
        if not valueBg is None:
            self.__checkParamType(currentAst, fctLabel, 'BGCOLOR', valueBg, QColor)

        if not valueBg is None:
            self.verbose(f"set canvas grid color {self.__strValue(value)} {self.__strValue(valueBg)}{self.__formatStoreResult(':canvas.grid.color', ':canvas.grid.bgColor')}", currentAst)
        else:
            self.verbose(f"set canvas grid color {self.__strValue(value)}{self.__formatStoreResult(':canvas.grid.color')}", currentAst)

        self.__setCanvasGridColor(value)

        if not valueBg is None:
            self.__setCanvasGridBgColor(valueBg)

        self.__delay()
        return None

    def __executeActionSetCanvasGridStyle(self, currentAst):
        """Set canvas grid style

        :canvas.grid.style.main
        :canvas.grid.style.secondary
        """
        fctLabel='Action ***set canvas grid style***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        main=self.__evaluate(currentAst.node(0))
        secondary=self.__evaluate(currentAst.node(1))

        self.__checkParamDomain(currentAst, fctLabel, 'STYLE-MAIN', main in BSInterpreter.CONST_PEN_STYLE, f"style value for main grid can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")
        self.__checkParamDomain(currentAst, fctLabel, 'STYLE-SECONDARY', secondary in BSInterpreter.CONST_PEN_STYLE, f"style value for secondary grid can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.verbose(f"set canvas grid style {self.__strValue(main)} {self.__strValue(secondary)}{self.__formatStoreResult(':canvas.grid.style.main', ':canvas.grid.style.secondary')}", currentAst)

        self.__setCanvasGridStyleMain(main)
        self.__setCanvasGridStyleSecondary(secondary)

        self.__delay()
        return None

    def __executeActionSetCanvasGridOpacity(self, currentAst):
        """Set canvas grid opacity

        :canvas.grid.color
        """
        fctLabel='Action ***set canvas grid opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set canvas grid opacity {self.__strValue(value)}{self.__formatStoreResult(':canvas.grid.color')}", currentAst)

        self.__setCanvasGridOpacity(value)

        self.__delay()
        return None

    def __executeActionSetCanvasGridSize(self, currentAst):
        """Set canvas grid size

        :canvas.grid.size.width
        :canvas.grid.size.main
        """
        fctLabel='Action ***set canvas grid size***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2, 3)

        width=self.__evaluate(currentAst.node(0))
        p2=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))

        if p2 is None and p3 is None:
            # no other parameters provided, set default value
            main=self.__scriptBlockStack.current().variable(':canvas.grid.size.main', 0)
            unit=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
        elif p3 is None:
            # p2 has been provided
            if isinstance(p2, (int, float)):
                main=p2
                unit=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            else:
                main=self.__scriptBlockStack.current().variable(':canvas.grid.size.main', 0)
                unit=p2
        else:
            # p2+p3 provided
            main=p2
            unit=p3

        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        self.__checkParamType(currentAst, fctLabel, 'MAIN', main, int)

        if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>0, f"a positive number is expected (current={width})", False):
            # let default value being applied in this case
            width=self.__scriptBlockStack.current().variable(':canvas.grid.size.width', width, True)

        if not self.__checkParamDomain(currentAst, fctLabel, 'MAIN', main>=0, f"a zero or positive number is expected (current={main})", False):
            # let default value being applied in this case
            main=self.__scriptBlockStack.current().variable(':canvas.grid.size.main', main, True)


        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"grid unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"set canvas grid size {self.__strValue(width)} {self.__strValue(main)} {self.__strValue(unit)}{self.__formatStoreResult(':canvas.grid.size.width', ':canvas.grid.size.main')}", currentAst)

        self.__setCanvasGridSize(width, main, unit)

        self.__delay()
        return None

    def __executeActionSetCanvasRulersColor(self, currentAst):
        """Set canvas rulers color

        :canvas.rulers.color
        :canvas.rulers.bgColor
        """
        fctLabel='Action ***set canvas rulers color***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)
        value=self.__evaluate(currentAst.node(0))
        valueBg=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)
        if not valueBg is None:
            self.__checkParamType(currentAst, fctLabel, 'BGCOLOR', valueBg, QColor)

        if not valueBg is None:
            self.verbose(f"set canvas rulers color {self.__strValue(value)} {self.__strValue(valueBg)}{self.__formatStoreResult(':canvas.rulers.color', ':canvas.rulers.bgColor')}", currentAst)
        else:
            self.verbose(f"set canvas rulers color {self.__strValue(value)}{self.__formatStoreResult(':canvas.rulers.color')}", currentAst)

        self.__setCanvasRulersColor(value)

        if not valueBg is None:
            self.__setCanvasRulersBgColor(valueBg)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginColor(self, currentAst):
        """Set canvas origin color

        :canvas.origin.color
        """
        fctLabel='Action ***set canvas origin color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set canvas origin color {self.__strValue(value)}{self.__formatStoreResult(':canvas.origin.color')}", currentAst)

        self.__setCanvasOriginColor(value)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginStyle(self, currentAst):
        """Set canvas origin style

        :canvas.origin.style
        """
        fctLabel='Action ***set canvas origin style***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'STYLE', value in BSInterpreter.CONST_PEN_STYLE, f"style value for origin can be: {', '.join(BSInterpreter.CONST_PEN_STYLE)}")

        self.verbose(f"set canvas origin style {self.__strValue(value)}{self.__formatStoreResult(':canvas.origin.style')}", currentAst)

        self.__setCanvasOriginStyle(value)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginOpacity(self, currentAst):
        """Set canvas origin opacity

        :canvas.origin.color
        """
        fctLabel='Action ***set canvas origin opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set canvas origin opacity {self.__strValue(value)}{self.__formatStoreResult(':canvas.origin.color')}", currentAst)

        self.__setCanvasOriginOpacity(value)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginSize(self, currentAst):
        """Set canvas origin size

        :canvas.origin.size
        """
        fctLabel='Action ***set canvas origin size***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'SIZE', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'SIZE', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.verbose(f"set canvas origin size {self.__strValue(value)} {self.__strValue(unit)}{self.__formatStoreResult(':canvas.origin.size')}", currentAst)
        else:
            self.verbose(f"set canvas origin size {self.__strValue(value)}{self.__formatStoreResult(':canvas.origin.size')}", currentAst)

        self.__setCanvasOriginSize(value, unit)

        self.__delay()
        return None

    def __executeActionSetCanvasOriginPosition(self, currentAst):
        """Set canvas origin position

        :canvas.origin.position.absissa
        :canvas.origin.position.ordinate
        """
        fctLabel='Action ***set canvas origin position***'
        self.__checkParamNumber(currentAst, fctLabel, 2)

        absissa=self.__evaluate(currentAst.node(0))
        ordinate=self.__evaluate(currentAst.node(1))

        self.__checkParamDomain(currentAst, fctLabel, 'ABSISSA', absissa in BSInterpreter.CONST_HALIGN, f"absissa position value can be: {', '.join(BSInterpreter.CONST_HALIGN)}")
        self.__checkParamDomain(currentAst, fctLabel, 'ORDINATE', ordinate in BSInterpreter.CONST_VALIGN, f"ordinate position value can be: {', '.join(BSInterpreter.CONST_VALIGN)}")

        self.verbose(f"set canvas origin position {self.__strValue(absissa)} {self.__strValue(ordinate)}{self.__formatStoreResult(':canvas.origin.position.absissa', 'canvas.origin.position.ordinate')}", currentAst)

        self.__setCanvasOriginPosition(absissa, ordinate)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionColor(self, currentAst):
        """Set canvas position color

        :canvas.position.color
        """
        fctLabel='Action ***set canvas position color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set canvas position color {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.color')}", currentAst)

        self.__setCanvasPositionColor(value)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionOpacity(self, currentAst):
        """Set canvas position opacity

        :canvas.position.color
        """
        fctLabel='Action ***set canvas position opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set canvas position opacity {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.color')}", currentAst)

        self.__setCanvasPositionOpacity(value)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionSize(self, currentAst):
        """Set canvas position size

        :canvas.position.size
        """
        fctLabel='Action ***set canvas position size***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'SIZE', value, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'SIZE', value>0, f"a positive number is expected (current={value})", False):
            # if value<=0, force to 0.1 (non blocking)
            value=max(0.1, value)

        if unit:
            self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"size unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
            self.verbose(f"set canvas position size {self.__strValue(value)} {self.__strValue(unit)}{self.__formatStoreResult(':canvas.position.size')}", currentAst)
        else:
            self.verbose(f"set canvas position size {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.size')}", currentAst)

        self.__setCanvasPositionSize(value, unit)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionFulfill(self, currentAst):
        """Set canvas position fulfilled

        :canvas.position.fulfill
        """
        fctLabel='Action ***set canvas position fulfilled***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set canvas position fulfilled {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.fulfill')}", currentAst)

        self.__setCanvasPositionFulfill(value)

        self.__delay()
        return None

    def __executeActionSetCanvasPositionAxis(self, currentAst):
        """Set canvas position axis

        :canvas.position.axis
        """
        fctLabel='Action ***set canvas position axis***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set canvas position axis {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.axis')}", currentAst)


        self.__delay()
        return None

    def __executeActionSetCanvasPositionModel(self, currentAst):
        """Set canvas position model

        :canvas.position.model
        """
        fctLabel='Action ***set canvas position model***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, 'MODEL', value in BSInterpreter.CONST_POSITIONMODEL, f"model value for position can be: {', '.join(BSInterpreter.CONST_POSITIONMODEL)}")

        self.verbose(f"set canvas position model {self.__strValue(value)}{self.__formatStoreResult(':canvas.position.model')}", currentAst)


        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundOpacity(self, currentAst):
        """Set canvas background opacity

        :canvas.background.opacity
        """
        fctLabel='Action ***set canvas background opacity***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'OPACITY', value, int, float)

        if isinstance(value, int):
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0 and value<=255, f"allowed opacity value when provided as an integer number is range [0;255] (current={value})", False):
                value=min(255, max(0, value))
            value/=255
        else:
            if not self.__checkParamDomain(currentAst, fctLabel, 'OPACITY', value>=0.0 and value<=1.0, f"allowed opacity value when provided as a decimal number is range [0.0;1.0] (current={value})", False):
                value=min(1.0, max(0.0, value))

        self.verbose(f"set canvas background opacity {self.__strValue(value)}{self.__formatStoreResult(':canvas.background.opacity')}", currentAst)

        self.__setCanvasBackgroundOpacity(value)

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundFromColor(self, currentAst):
        """Set canvas background from color

        :canvas.background.source.type
        :canvas.background.source.value
        """
        fctLabel='Action ***set canvas background from color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"set canvas background from color {self.__strValue(value)}{self.__formatStoreResult(':canvas.background.source.type', ':canvas.background.source.value')}", currentAst)

        self.__setCanvasBackgroundFromColor(value)

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundFromDocument(self, currentAst):
        """Set canvas background from document

        :canvas.background.source.type
        :canvas.background.source.value
        """
        fctLabel='Action ***set canvas background from document***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"set canvas background from document {self.__formatStoreResult(':canvas.background.source.type', ':canvas.background.source.value')}", currentAst)

        self.__setCanvasBackgroundFromDocument()

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundFromLayerActive(self, currentAst):
        """Set canvas background from layer active

        :canvas.background.source.type
        :canvas.background.source.value
        """
        fctLabel='Action ***set canvas background from layer active***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"set canvas background from layer active {self.__formatStoreResult(':canvas.background.source.type', ':canvas.background.source.value')}", currentAst)

        self.__setCanvasBackgroundFromLayerActive()

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundFromLayerName(self, currentAst):
        """Set canvas background from layer name

        :canvas.background.source.type
        :canvas.background.source.value
        """
        fctLabel='Action ***set canvas background from layer name***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'NAME', value, str)

        self.verbose(f"set canvas background from layer name {self.__strValue(value)}{self.__formatStoreResult(':canvas.background.source.type', ':canvas.background.source.value')}", currentAst)

        layerApplied=self.__setCanvasBackgroundFromLayerName(value)
        if layerApplied[0]!='layer name':
            self.warning(f"Unable to find a layer with given name '*{value}*', active layer will be used instead", currentAst)

        self.__delay()
        return None

    def __executeActionSetCanvasBackgroundFromLayerId(self, currentAst):
        """Set canvas background from layer id

        :canvas.background.source.type
        :canvas.background.source.value
        """
        fctLabel='Action ***set canvas background from layer id***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'ID', value, str)

        self.verbose(f"set canvas background from layer id {self.__strValue(value)}{self.__formatStoreResult(':canvas.background.source.type', ':canvas.background.source.value')}", currentAst)

        layerApplied=self.__setCanvasBackgroundFromLayerId(value)
        if layerApplied[0]!='layer id':
            self.warning(f"Unable to find a layer with given Id '*{value}*', active layer will be used instead", currentAst)

        self.__delay()
        return None

    def __executeActionSetExecutionVerbose(self, currentAst):
        """Set script execution verbose

        :script.execution.verbose
        """
        fctLabel='Action ***set script execution verbose***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SWITCH', value, bool)

        self.verbose(f"set script execution verbose {self.__strValue(value)}{self.__formatStoreResult(':script.execution.verbose')}", currentAst)

        self.__setExecutionVerbose(value)

        self.__delay()
        return None

    def __executeActionSetRandomizeSeed(self, currentAst):
        """Set script randomize seed

        :script.randomize.seed
        """
        fctLabel='Action ***set script randomize seed***'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'SEED', value, int, str)

        self.verbose(f"set script randomize seed {self.__strValue(value)}{self.__formatStoreResult(':script.randomize.seed')}", currentAst)

        self.__setRandomizeSeed(value)

        self.__delay()
        return None

    # Draw
    # ----
    def __executeActionDrawShapeLine(self, currentAst):
        """Draw line"""
        fctLabel='Action ***draw line***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        length=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'LENGTH', length, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'LENGTH', length>0, f"a positive number is expected (current={length})", False):
            # if value<=0, exit
            self.verbose(f"draw square {self.__strValue(length)} {self.__strValue(unit)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"width unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"draw line {self.__strValue(length)} {self.__strValue(unit)}", currentAst)


        self.__delay()
        return None

    def __executeActionDrawShapeSquare(self, currentAst):
        """Draw square"""
        fctLabel='Action ***draw square***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        width=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.verbose(f"draw square {self.__strValue(width)} {self.__strValue(unit)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"width unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"draw square {self.__strValue(width)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRoundSquare(self, currentAst):
        """Draw square"""
        fctLabel='Action ***draw round square***'
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


        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.verbose(f"draw round square {self.__strValue(width)} {self.__strValue(unitWidth)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'W-UNIT', unitWidth in BSInterpreter.CONST_MEASURE_UNIT, f"width unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__checkParamType(currentAst, fctLabel, 'RADIUS', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'RADIUS', radius>=0, f"a zero or positive number is expected (current={radius})", False):
            radius=0

        self.__checkParamDomain(currentAst, fctLabel, 'R-UNIT', unitRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.verbose(f"draw round square {self.__strValue(width)} {self.__strValue(unitWidth)} {self.__strValue(radius)} {self.__strValue(unitRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRect(self, currentAst):
        """Draw rect"""
        fctLabel='Action ***draw rect***'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        width=self.__evaluate(currentAst.node(0))
        height=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        self.__checkParamType(currentAst, fctLabel, 'HEIGHT', height, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, 'HEIGHT', height>0, f"a positive number is expected (current={height})", False):
            # if value<=0, exit
            self.verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"draw rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeRoundRect(self, currentAst):
        """Draw square"""
        fctLabel='Action ***draw round square***'
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


        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        self.__checkParamType(currentAst, fctLabel, 'HEIGHT', height, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>0, f"a positive number is expected (current={width})", False):
            # if value<=0, exit
            self.verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, 'HEIGHT', height>0, f"a positive number is expected (current={height})", False):
            # if value<=0, exit
            self.verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'S-UNIT', unitDimension in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__checkParamType(currentAst, fctLabel, 'RADIUS', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'RADIUS', radius>=0, f"a zero or positive number is expected (current={radius})", False):
            radius=0

        self.__checkParamDomain(currentAst, fctLabel, 'R-UNIT', unitRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.verbose(f"draw round rect {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unitDimension)} {self.__strValue(radius)} {self.__strValue(unitRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeCircle(self, currentAst):
        """Draw circle"""
        fctLabel='Action ***draw circle***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        radius=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'RADIUS', radius, int, float)
        if not self.__checkParamDomain(currentAst, fctLabel, 'RADIUS', radius>0, f"a positive number is expected (current={radius})", False):
            # if value<=0, exit
            self.verbose(f"draw circle {self.__strValue(radius)} {self.__strValue(unit)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"draw circle {self.__strValue(radius)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeEllipse(self, currentAst):
        """Draw ellipse"""
        fctLabel='Action ***draw ellipse***'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        hRadius=self.__evaluate(currentAst.node(0))
        vRadius=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'H-RADIUS', hRadius, int, float)
        self.__checkParamType(currentAst, fctLabel, 'V-RADIUS', vRadius, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, 'H-RADIUS', hRadius>0, f"a positive number is expected (current={hRadius})", False):
            # if value<=0, exit
            self.verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, 'V-RADIUS', vRadius>0, f"a positive number is expected (current={vRadius})", False):
            # if value<=0, exit
            self.verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}     => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.verbose(f"draw ellipse {self.__strValue(hRadius)} {self.__strValue(vRadius)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeDot(self, currentAst):
        """Draw dot"""
        fctLabel='Action ***draw dot***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"draw dot", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapePixel(self, currentAst):
        """Draw pixel"""
        fctLabel='Action ***draw pixel***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"draw pixel", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeImage(self, currentAst):
        """Draw image"""
        fctLabel='Action ***draw image***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        imageReference=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'IMAGE', imageReference, str)

        self.verbose(f"draw image *'{self.__strValue(imageReference)}'*", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeScaledImage(self, currentAst):
        """Draw scaled image"""
        fctLabel='Action ***draw scaled image***'
        self.__checkParamNumber(currentAst, fctLabel, 3, 4, 5)

        imageReference=self.__evaluate(currentAst.node(0))
        width=self.__evaluate(currentAst.node(1))

        p2=self.__evaluate(currentAst.node(2))
        p3=self.__evaluate(currentAst.node(3))
        p4=self.__evaluate(currentAst.node(4))

        if isinstance(p2, (int, float)):
            # p2 is a numeric value
            # consider we have
            #   draw scaled image "image ref" width height [unit]
            # same unit for witdh and height
            height=p2
            unitW=self.__evaluate(currentAst.node(3, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))
            unitH=unitW
        elif isinstance(p2, str):
            # p2 is a string value
            # consider we have
            #   draw scaled image "image ref" width unit height [unit]
            unitW=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))
            height=p3
            unitH=self.__evaluate(currentAst.node(4, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'IMAGE', imageReference, str)
        self.__checkParamType(currentAst, fctLabel, 'WIDTH', width, int, float)
        self.__checkParamType(currentAst, fctLabel, 'HEIGHT', height, int, float)
        self.__checkParamType(currentAst, fctLabel, 'UNIT-WIDTH', unitW, str)
        self.__checkParamType(currentAst, fctLabel, 'UNIT-HEIGHT', unitH, str)

        #if not self.__checkParamDomain(currentAst, fctLabel, 'WIDTH', width>=0, f"a positive number is expected (current={width})", False):
        #    # if value<=0, exit
        #    self.verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
        #    self.__delay()
        #    return None

        #if not self.__checkParamDomain(currentAst, fctLabel, 'HEIGHT', height>=0, f"a positive number is expected (current={height})", False):
        #    # if value<=0, exit
        #    self.verbose(f"draw scaled image {self.__strValue(fileName)} {self.__strValue(width)} {self.__strValue(height)} {self.__strValue(unit)}     => Cancelled", currentAst)
        #    self.__delay()
        #    return None

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT-WIDTH', unitW in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")
        self.__checkParamDomain(currentAst, fctLabel, 'UNIT-HEIGHT', unitH in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"dimension unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")


        self.verbose(f"draw scaled image *'{self.__strValue(imageReference)}'* {self.__strValue(width)} {self.__strValue(unitW)} {self.__strValue(height)} {self.__strValue(unitH)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeText(self, currentAst):
        """Draw text"""
        fctLabel='Action ***draw text***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'TEXT', text, str)

        self.verbose(f"draw text {self.__strValue(text)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawShapeStar(self, currentAst):
        """Draw star"""
        fctLabel='Action ***draw star***'
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

        self.__checkParamType(currentAst, fctLabel, 'BRANCHES', branches, int)
        self.__checkParamType(currentAst, fctLabel, 'O-RADIUS', oRadius, int, float)
        self.__checkParamType(currentAst, fctLabel, 'I-RADIUS', iRadius, int, float)

        if not self.__checkParamDomain(currentAst, fctLabel, 'BRANCHES', branches>=3, f"a positive integer greater or equal than 3 is expected (current={branches})", False):
            # force minimum
            branches=3

        if not self.__checkParamDomain(currentAst, fctLabel, 'O-RADIUS', oRadius>0, f"a positive number is expected (current={oRadius})", False):
            # if value<=0, exit
            self.verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        if not self.__checkParamDomain(currentAst, fctLabel, 'I-RADIUS', iRadius>0, f"a positive number is expected (current={iRadius})", False):
            # if value<=0, exit
            self.verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}      => Cancelled", currentAst)
            self.__delay()
            return None

        self.__checkParamDomain(currentAst, fctLabel, 'OR-UNIT', unitORadius in BSInterpreter.CONST_MEASURE_UNIT, f"outer radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
        self.__checkParamDomain(currentAst, fctLabel, 'IR-UNIT', unitIRadius in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"inter radius unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        self.verbose(f"draw star {self.__strValue(branches)} {self.__strValue(oRadius)} {self.__strValue(unitORadius)} {self.__strValue(iRadius)} {self.__strValue(unitIRadius)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMiscClearCanvas(self, currentAst):
        """Clear canvas"""
        fctLabel='Action ***clear canvas***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"clear canvas", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMiscFillCanvasFromColor(self, currentAst):
        """Fill canvas from color"""
        fctLabel='Action ***fill canvas from color***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'COLOR', value, QColor)

        self.verbose(f"fill canvas from color {self.__strValue(value)}", currentAst)


        self.__delay()
        return None

    def __executeActionDrawMiscFillCanvasFromImage(self, currentAst):
        """Fill canvas from image"""
        fctLabel='Action ***fill canvas from image***'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        imageReference=self.__evaluate(currentAst.node(0))
        tiling=False
        scale=None
        rotation=None
        offset=None

        self.__checkParamType(currentAst, fctLabel, 'IMAGE', imageReference, str)

        for index, node in enumerate(currentAst.nodes()):
            if index==0:
                continue

            # node must be an ASTItem
            self.__checkOption(currentAst, fctLabel, node)

            if node.id()=="Action_Draw_Misc_Fill_Canvas_From_Image_Option_With_Tiling":
                tiling=self.__executeActionDrawMiscFillCanvasFromImageOptionTiling(node)
            elif node.id()=="Action_Draw_Misc_Fill_Canvas_From_Image_Option_With_Scale":
                scale=self.__executeActionDrawMiscFillCanvasFromImageOptionScale(node)
            elif node.id()=="Action_Draw_Misc_Fill_Canvas_From_Image_Option_With_Offset":
                offset=self.__executeActionDrawMiscFillCanvasFromImageOptionOffset(node)
            elif node.id()=="Action_Draw_Misc_Fill_Canvas_From_Image_Option_With_Rotation_Left":
                rotation=self.__executeActionDrawMiscFillCanvasFromImageOptionRotation(node, 'L')
            elif node.id()=="Action_Draw_Misc_Fill_Canvas_From_Image_Option_With_Rotation_Right":
                rotation=self.__executeActionDrawMiscFillCanvasFromImageOptionRotation(node, 'R')
            else:
                # force to raise an error
                self.__checkOption(currentAst, fctLabel, node, True)


        self.__delay()
        return None

    def __executeActionDrawMiscFillCanvasFromImageOptionTiling(self, currentAst):
        """with tiling

        Return optional tiling option for draw fill image action
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with tiling***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        return True

    def __executeActionDrawMiscFillCanvasFromImageOptionScale(self, currentAst):
        """with scale

        Return optional scale option for draw fill image action
        Returned value is a tuple(float, str, float, str)

        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with scale***'
        self.__checkParamNumber(currentAst, fctLabel, 2,3,4)

        scaleH=self.__evaluate(currentAst.node(0))
        p2=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))
        p4=self.__evaluate(currentAst.node(3))

        if len(currentAst.nodes())==2:
            # second parameter is v scale
            scaleV=p2
            unitScaleH=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            unitScaleV=unitScaleH
        elif len(currentAst.nodes())==3:
            if isinstance(p2, str):
                # a unit
                unitScaleH=p2
                # third parameter is v scale
                scaleV=p3
                unitScaleV=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            elif isinstance(p2, (int, float)):
                # second parameter is v scale
                scaleV=p2
                unitScaleH=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
                unitScaleV=p3
        elif len(currentAst.nodes())==4:
                unitScaleH=p2
                scaleV=p3
                unitScaleV=p4

        self.__checkParamType(currentAst, fctLabel, 'WIDTH', scaleH, int, float)
        self.__checkParamType(currentAst, fctLabel, 'HEIGHT', scaleV, int, float)
        self.__checkParamType(currentAst, fctLabel, 'WIDTH-UNIT', unitScaleH, str)
        self.__checkParamType(currentAst, fctLabel, 'HEIGHT-UNIT', unitScaleV, str)

        self.__checkParamDomain(currentAst, fctLabel, 'WIDTH-UNIT', unitScaleH in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")
        self.__checkParamDomain(currentAst, fctLabel, 'HEIGHT-UNIT', unitScaleV in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        return (scaleH, unitScaleH, scaleV, unitScaleV)

    def __executeActionDrawMiscFillCanvasFromImageOptionOffset(self, currentAst):
        """with offset

        Return optional offset option for draw fill image action
        Returned value is a tuple(float, str, float, str)

        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with offset***'
        self.__checkParamNumber(currentAst, fctLabel, 2,3,4)

        offsetH=self.__evaluate(currentAst.node(0))
        p2=self.__evaluate(currentAst.node(1))
        p3=self.__evaluate(currentAst.node(2))
        p4=self.__evaluate(currentAst.node(3))

        if len(currentAst.nodes())==2:
            # second parameter is v offset
            offsetV=p2
            unitOffsetH=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            unitOffsetV=unitOffsetH
        elif len(currentAst.nodes())==3:
            if isinstance(p2, str):
                # a unit
                unitOffsetH=p2
                # third parameter is v offset
                offsetV=p3
                unitOffsetV=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
            elif isinstance(p2, (int, float)):
                # second parameter is v offset
                offsetV=p2
                unitOffsetH=self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')
                unitOffsetV=p3
        elif len(currentAst.nodes())==4:
                unitOffsetH=p2
                offsetV=p3
                unitOffsetV=p4

        self.__checkParamType(currentAst, fctLabel, 'ABSISSA', offsetH, int, float)
        self.__checkParamType(currentAst, fctLabel, 'ORDINATE', offsetV, int, float)
        self.__checkParamType(currentAst, fctLabel, 'ABSISSA-UNIT', unitOffsetH, str)
        self.__checkParamType(currentAst, fctLabel, 'ORDINATE-UNIT', unitOffsetV, str)

        self.__checkParamDomain(currentAst, fctLabel, 'ABSISSA-UNIT', unitOffsetH in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")
        self.__checkParamDomain(currentAst, fctLabel, 'ORDINATE-UNIT', unitOffsetV in BSInterpreter.CONST_MEASURE_UNIT_RPCT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT_RPCT)}")

        return (offsetH, unitOffsetH, offsetV, unitOffsetV)

    def __executeActionDrawMiscFillCanvasFromImageOptionRotation(self, currentAst, direction):
        """with rotation

        Return optional rotation option for draw fill image action
        Returned value is a tuple(float, str)

        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with rotation***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        rotation=self.__evaluate(currentAst.node(0))
        angle=self.__evaluate(currentAst.node(1))

        if angle is None:
            angle=self.__scriptBlockStack.current().variable(':unit.rotation', 'PX')

        self.__checkParamType(currentAst, fctLabel, 'ANGLE', rotation, int, float)
        self.__checkParamType(currentAst, fctLabel, 'ANGLE-UNIT', angle, str)

        if direction=='L':
            rotation=-rotation

        self.__checkParamDomain(currentAst, fctLabel, 'ORDINATE-UNIT', angle in BSInterpreter.CONST_ROTATION_UNIT, f"unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        return (rotation, angle)

    def __executeActionDrawShapeStart(self, currentAst):
        """Start to draw shape

        :draw.shape.status
        """
        fctLabel='Action ***start to draw shape***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"start to draw shape", currentAst)

        self.__setDrawShapeStatus(True)

        self.__delay()
        return None

    def __executeActionDrawShapeStop(self, currentAst):
        """Stop to draw shape

        :draw.shape.status
        """
        fctLabel='Action ***stop to draw shape***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"stop to draw shape", currentAst)

        self.__setDrawShapeStatus(False)

        self.__delay()
        return None

    def __executeActionDrawFillActivate(self, currentAst):
        """Activate fill mode

        :fill.status
        """
        fctLabel='Action ***activate fill***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"activate fill", currentAst)

        self.__scriptBlockStack.setVariable(':fill.status', True, BSVariableScope.CURRENT)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawFillDeactivate(self, currentAst):
        """Deactivate fill mode

        :fill.status
        """
        fctLabel='Action ***deactivate fill***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"deactivate fill", currentAst)

        self.__scriptBlockStack.setVariable(':fill.status', False, BSVariableScope.CURRENT)
        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawPenUp(self, currentAst):
        """Pen up

        :pen.status
        """
        fctLabel='Action ***pen up***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"pen up", currentAst)

        self.__scriptBlockStack.setVariable(':pen.status', False, BSVariableScope.CURRENT)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawPenDown(self, currentAst):
        """Pen down

        :pen.status
        """
        fctLabel='Action ***pen down***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"pen down", currentAst)

        self.__scriptBlockStack.setVariable(':pen.status', True, BSVariableScope.CURRENT)
        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveHome(self, currentAst):
        """Move home"""
        fctLabel='Action ***move home***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"move home", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveForward(self, currentAst):
        """Move forward"""
        fctLabel='Action ***move forward***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"move forward {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveBackward(self, currentAst):
        """Move backward"""
        fctLabel='Action ***move backward***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"move backward {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveLeft(self, currentAst):
        """Move left"""
        fctLabel='Action ***move left***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"move left {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveRight(self, currentAst):
        """Move right"""
        fctLabel='Action ***move right***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"move right {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawMoveTo(self, currentAst):
        """Move to"""
        fctLabel='Action ***move to***'
        self.__checkParamNumber(currentAst, fctLabel, 2, 3)

        valueX=self.__evaluate(currentAst.node(0))
        valueY=self.__evaluate(currentAst.node(1))
        unit=self.__evaluate(currentAst.node(2, self.__scriptBlockStack.current().variable(':unit.canvas', 'PX')))

        self.__checkParamType(currentAst, fctLabel, 'X', valueX, int, float)
        self.__checkParamType(currentAst, fctLabel, 'Y', valueY, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_MEASURE_UNIT, f"unit value can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.verbose(f"move to {self.__strValue(valueX)} {self.__strValue(valueY)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnLeft(self, currentAst):
        """Turn left"""
        fctLabel='Action ***turn left***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.verbose(f"turn left {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnRight(self, currentAst):
        """Turn right"""
        fctLabel='Action ***turn right***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.verbose(f"turn right {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionDrawTurnTo(self, currentAst):
        """Turn to"""
        fctLabel='Action ***turn to***'
        self.__checkParamNumber(currentAst, fctLabel, 1, 2)

        value=self.__evaluate(currentAst.node(0))
        unit=self.__evaluate(currentAst.node(1, self.__scriptBlockStack.current().variable(':unit.rotation', 'DEGREE')))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

        self.__checkParamDomain(currentAst, fctLabel, 'UNIT', unit in BSInterpreter.CONST_ROTATION_UNIT, f"value unit value can be: {', '.join(BSInterpreter.CONST_ROTATION_UNIT)}")

        self.verbose(f"turn to {self.__strValue(value)} {self.__strValue(unit)}", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionStatePush(self, currentAst):
        """Push state"""
        fctLabel='Action ***push state***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"push state", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionStatePop(self, currentAst):
        """Push state"""
        fctLabel='Action ***pop state***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"pop state", currentAst)

        # TODO: implement canvas render

        self.__delay()
        return None

    def __executeActionCanvasShowGrid(self, currentAst):
        """Show canvas grid

        :canvas.grid.visibility
        """
        fctLabel='Action ***show canvas grid***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"show canvas grid", currentAst)

        self.__setCanvasGridVisible(True)

        self.__delay()
        return None

    def __executeActionCanvasHideGrid(self, currentAst):
        """Hide canvas grid

        :canvas.grid.visibility
        """
        fctLabel='Action ***hide canvas grid***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"hide canvas grid", currentAst)

        self.__setCanvasGridVisible(False)

        self.__delay()
        return None

    def __executeActionCanvasShowOrigin(self, currentAst):
        """Show canvas origin

        :canvas.origin.visibility
        """
        fctLabel='Action ***show canvas origin***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"show canvas origin", currentAst)

        self.__setCanvasOriginVisible(True)

        self.__delay()
        return None

    def __executeActionCanvasHideOrigin(self, currentAst):
        """Hide canvas origin

        :canvas.origin.visibility
        """
        fctLabel='Action ***hide canvas origin***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"hide canvas origin", currentAst)

        self.__setCanvasOriginVisible(False)

        self.__delay()
        return None

    def __executeActionCanvasShowPosition(self, currentAst):
        """Show canvas position

        :canvas.position.visibility
        """
        fctLabel='Action ***show canvas position***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"show canvas position", currentAst)

        self.__setCanvasPositionVisible(True)

        self.__delay()
        return None

    def __executeActionCanvasHidePosition(self, currentAst):
        """Hide canvas position

        :canvas.position.visibility
        """
        fctLabel='Action ***hide canvas position***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"hide canvas position", currentAst)

        self.__setCanvasPositionVisible(False)

        self.__delay()
        return None

    def __executeActionCanvasShowBackground(self, currentAst):
        """Show canvas background

        :canvas.background.visibility
        """
        fctLabel='Action ***show canvas background***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"show canvas background", currentAst)

        self.__setCanvasBackgroundVisible(True)

        self.__delay()
        return None

    def __executeActionCanvasHideBackground(self, currentAst):
        """Hide canvas background

        :canvas.background.visibility
        """
        fctLabel='Action ***hide canvas background***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"hide canvas background", currentAst)

        self.__setCanvasBackgroundVisible(False)

        self.__delay()
        return None

    def __executeActionCanvasShowRulers(self, currentAst):
        """Show canvas rulers

        :canvas.rulers.visibility
        """
        fctLabel='Action ***show canvas rulers***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"show canvas rulers", currentAst)

        self.__setCanvasRulersVisible(True)

        self.__delay()
        return None

    def __executeActionCanvasHideRulers(self, currentAst):
        """Hide canvas rulers

        :canvas.rulers.visibility
        """
        fctLabel='Action ***hide canvas rulers***'
        self.__checkParamNumber(currentAst, fctLabel, 0)

        self.verbose(f"hide canvas rulers", currentAst)

        self.__setCanvasRulersVisible(False)

        self.__delay()
        return None

    def __executeActionUIConsolePrint(self, currentAst, formatted=False, consoleType=WConsoleType.NORMAL):
        """Print"""
        fctLabel='Action ***print***'

        if len(currentAst.nodes())<1:
            # at least need one parameter
            self.__checkParamNumber(currentAst, fctLabel, 1)

        printed=[]
        for node in currentAst.nodes():
            value=self.__evaluate(node)
            if not formatted and isinstance(value, str):
                value=WConsole.escape(value)
            printed.append(str(self.__strValue(value)))

        self.print(' '.join(printed), consoleType)

        #self.__delay()
        return None

    def __executeActionUIDialogOptionWithMessage(self, currentAst):
        """with message

        Return optional message for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with message***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'TEXT', text, str)

        return text

    def __executeActionUIDialogOptionWithTitle(self, currentAst):
        """with title

        Return optional title for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with title***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        text=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'TEXT', text, str)

        return text

    def __executeActionUIDialogOptionWithDefaultValue(self, currentAst, type):
        """with default value

        Return optional default for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with default value***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, type)

        return value

    def __executeActionUIDialogOptionWithMinimumValue(self, currentAst, type):
        """with minimum value

        Return optional minimum value for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with minimum value***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, type)

        return value

    def __executeActionUIDialogOptionWithMaximumValue(self, currentAst, type):
        """with maximum value

        Return optional minimum value for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with maximum value***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, type)

        return value

    def __executeActionUIDialogOptionWithDefaultIndex(self, currentAst, type):
        """with default index

        Return optional default index for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with default index***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, type)

        return value

    def __executeActionUIDialogOptionWithChoices(self, currentAst):
        """with default combobox choices

        Return optional list of choices for a dialog box
        Not aimed to be called directly from __executeAst() method
        """
        fctLabel='Option ***with combobox choices***'
        self.__checkParamNumber(currentAst, fctLabel, 1)

        value=self.__evaluate(currentAst.node(0))

        self.__checkParamType(currentAst, fctLabel, 'VALUE', value, list)
        value=[str(item) for item in value]

        return value

    def __executeActionUIDialogMessage(self, currentAst):
        """Open dialog for message"""
        fctLabel='Action ***open dialog for message***'

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
        fctLabel='Action ***open dialog for boolean input***'

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
        scriptBlock.setVariable(variableName, WDialogBooleanInput.display(title, message), BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogStringInput(self, currentAst):
        """Open dialog for string input"""
        fctLabel='Action ***open dialog for string input***'

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
        scriptBlock.setVariable(variableName, WDialogStrInput.display(title, message, defaultValue=defaultValue), BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogIntegerInput(self, currentAst):
        """Open dialog for integer input"""
        fctLabel='Action ***open dialog for integer input***'

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
        scriptBlock.setVariable(variableName, WDialogIntInput.display(title, message, defaultValue=defaultValue, minValue=minimumValue, maxValue=maximumValue), BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogDecimalInput(self, currentAst):
        """Open dialog for decimal input"""
        fctLabel='Action ***open dialog for decimal input***'

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
        scriptBlock.setVariable(variableName, WDialogFloatInput.display(title, message, defaultValue=defaultValue, minValue=minimumValue, maxValue=maximumValue), BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogColorInput(self, currentAst):
        """Open dialog for color input"""
        fctLabel='Action ***open dialog for color input***'

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
                                minSize=minSize), BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogSingleChoiceInput(self, currentAst):
        """Open dialog for single choice input"""
        fctLabel='Action ***open dialog for single choice input***'

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
        scriptBlock.setVariable(variableName, value, BSVariableScope.CURRENT)

        #self.__delay()
        return None

    def __executeActionUIDialogMultipleChoiceInput(self, currentAst):
        """Open dialog for multiple choice input"""
        fctLabel='Action ***open dialog for multiple choice input***'

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
        scriptBlock.setVariable(variableName, value, BSVariableScope.CURRENT)

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

                self.__checkParamType(currentAst, fctLabel, 'MIN', minValue, int, float)
                self.__checkParamType(currentAst, fctLabel, 'MAX', maxValue, int, float)

                if minValue>maxValue:
                    # switch values
                    minValue, maxValue=maxValue, minValue

                if isinstance(minValue, int) and isinstance(maxValue, int):
                    # both bound value are integer, return integer
                    return random.randrange(minValue, maxValue)
                else:
                    # at least one decimal value, return decimal value
                    return random.uniform(minValue, maxValue)

        elif fctName=='math.absolute':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return abs(value)
        elif fctName=='math.even':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return (value%2)==0
        elif fctName=='math.odd':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return (value%2)==1
        elif fctName=='math.sign':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

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

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.exp(value)
        elif fctName=='math.power':
            self.__checkFctParamNumber(currentAst, fctLabel, 2)
            value=self.__evaluate(currentAst.node(1))
            power=self.__evaluate(currentAst.node(2))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamType(currentAst, fctLabel, 'POWER', power, int, float)

            return math.pow(value, power)
        elif fctName=='math.squareroot':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>=0, f'must be a zero or positive numeric value (current={value})')


            return math.sqrt(value)
        elif fctName=='math.logn':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>0, f'must be a positive numeric value (current={value})')

            return math.log(value)
        elif fctName=='math.log':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            base=self.__evaluate(currentAst.node(2, 10))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamType(currentAst, fctLabel, 'BASE', value, int, float)

            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>0, f'must be a positive numeric value (current={value})')
            self.__checkParamDomain(currentAst, fctLabel, 'BASE', base>0 and base!=1, f'must be a positive numeric value not equal to 1  (current={base})')

            return math.log(value, base)
        elif fctName=='math.convert':
            self.__checkFctParamNumber(currentAst, fctLabel, 3,4)

            value=self.__evaluate(currentAst.node(1))
            convertFrom=self.__evaluate(currentAst.node(2))
            convertTo=self.__evaluate(currentAst.node(3))
            refPct=self.__evaluate(currentAst.node(4))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamType(currentAst, fctLabel, 'F-UNIT', convertFrom, str)
            self.__checkParamType(currentAst, fctLabel, 'T-UNIT', convertTo, str)

            # need to check consistency convertFrom->convertTo
            if convertFrom in ['PX', 'PCT', 'MM', 'INCH']:
                self.__checkParamDomain(currentAst, fctLabel, 'T-UNIT', convertTo in ['PX', 'PCT', 'MM', 'INCH'], 'conversion of a measure unit can only be converted to another measure unit (PC, PCT, MM, INCH)')

                if not refPct is None:
                    self.__checkParamType(currentAst, fctLabel, 'PCT-REF', refPct, str)
                    self.__checkParamDomain(currentAst, refPct, 'PCT-REF', refPct in 'WH', 'percentage reference can only be: "W" or "H", use default WIDTH as reference', False)

                returned=BSConvertUnits.convertMeasure(value, convertFrom, convertTo, refPct)
            elif convertFrom in ['DEGREE','RADIAN']:
                self.__checkParamDomain(currentAst, fctLabel, 'T-UNIT', convertTo in ['DEGREE','RADIAN'], 'conversion of an angle unit can only be converted to another angle unit (DEGREE, RADIAN)')
                if not refPct is None:
                    self.warning(f"Percentage reference is ignored for ANGLE conversion", currentAst)
                returned=BSConvertUnits.convertAngle(value, convertFrom, convertTo)
            else:
                self.__checkParamDomain(currentAst, fctLabel, 'F-UNIT', False, 'can only convert measures and angles units')

            return returned
        elif fctName=='math.minimum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'VALUE[{index}]', value, int, float)

            return min(values)
        elif fctName=='math.maximum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'VALUE[{index}]', value, int, float)

            return max(values)
        elif fctName=='math.sum':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'VALUE[{index}]', value, int, float)

            return sum(values)
        elif fctName=='math.average':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'VALUE[{index}]', value, int, float)

            nbItems=len(values)
            if nbItems>0:
                return sum(values)/nbItems
            return 0
        elif fctName=='math.product':
            # no minimum  arguments
            values=flatten(map(self.__evaluate, currentAst.nodes()[1:]))
            for index, value in enumerate(values):
                self.__checkParamType(currentAst, fctLabel, f'VALUE[{index}]', value, int, float)

            nbItems=len(values)
            if nbItems>0:
                return math.prod(values)
            return 0
        elif fctName=='math.ceil':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.ceil(value)
        elif fctName=='math.floor':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.floor(value)
        elif fctName=='math.round':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            roundValue=self.__evaluate(currentAst.node(2, 0))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamType(currentAst, fctLabel, 'DECIMALS', roundValue, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'DECIMALS', roundValue>=0 and isinstance(roundValue, int), f"must be a zero or positive integer value (current={roundValue})")

            if roundValue==0:
                # because math.floor(x, 0) return a float
                # and here we want an integer if rounded to 0 decimal
                return round(value)
            else:
                return round(value, roundValue)
        elif fctName=='math.cos':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.cos(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.sin':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.sin(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.tan':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.tan(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.acos':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>=-1 and value<=1 , f"must be a numeric value in range [-1.0;1.0] (current={value})")

            return math.acos(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.asin':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>=-1 and value<=1 , f"must be a numeric value in range [-1.0;1.0] (current={value})")

            return math.asin(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.atan':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.atan(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.cosh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.cosh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.sinh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.sinh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.tanh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.tanh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.acosh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>=1, f"must be a numeric value in range [1.0;infinite[ (current={value})")

            return math.acosh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.asinh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)

            return math.asinh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='math.atanh':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'VALUE', value, int, float)
            self.__checkParamDomain(currentAst, fctLabel, 'VALUE', value>-1 and value<1 , f"must be a numeric value in range ]-1.0;1.0[ (current={value})")

            return math.atanh(BSConvertUnits.convertAngle(value, self.__scriptBlockStack.current().variable(':unit.rotation'), 'RADIAN'))
        elif fctName=='string.length':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'TEXT', value, str)

            return len(value)
        elif fctName=='string.upper':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'TEXT', value, str)

            return value.upper()
        elif fctName=='string.lower':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'TEXT', value, str)

            return value.lower()
        elif fctName=='string.substring':
            self.__checkFctParamNumber(currentAst, fctLabel, 2,3)

            value=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'TEXT', value, str)

            nbChar=len(value)
            if value=='':
                # empty string, return result immediately
                return ''


            fromIndex=self.__evaluate(currentAst.node(2))
            self.__checkParamType(currentAst, fctLabel, 'INDEX', fromIndex, int)
            if fromIndex==0 or abs(fromIndex)>nbChar:
                # invalid index, return empty string immediately
                return ''

            countChar=self.__evaluate(currentAst.node(3))
            if countChar:
                self.__checkParamType(currentAst, fctLabel, 'COUNT', countChar, int)

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
        elif fctName=='string.format':
            if len(currentAst.nodes())<1:
                # at least need one parameter
                self.__checkParamNumber(currentAst, fctLabel, 1)

            formatStr=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'FORMAT', formatStr, str)

            values=[]
            for index, node in enumerate(currentAst.nodes()):
                if index>1:
                    # 0 = function name
                    # 1 = format str
                    # 2+ = values
                    values.append(str(self.__strValue(self.__evaluate(node))))

            returned=formatStr.format(*values)

            return returned
        elif fctName=='color.rgb':
            self.__checkFctParamNumber(currentAst, fctLabel, 3)

            rValue=self.__evaluate(currentAst.node(1))
            gValue=self.__evaluate(currentAst.node(2))
            bValue=self.__evaluate(currentAst.node(3))


            self.__checkParamType(currentAst, fctLabel, 'R-VALUE', rValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'G-VALUE', gValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'B-VALUE', bValue, int, float)

            if isinstance(rValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'R-VALUE', rValue>=0 and rValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={rValue})", False):
                    rValue=min(255, max(0, rValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'R-VALUE', rValue>=0.0 and rValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={rValue})", False):
                    rValue=min(1.0, max(0.0, rValue))

            if isinstance(gValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'G-VALUE', gValue>=0 and gValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={gValue})", False):
                    gValue=min(255, max(0, gValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'G-VALUE', gValue>=0.0 and gValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={gValue})", False):
                    gValue=min(1.0, max(0.0, gValue))

            if isinstance(bValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'B-VALUE', bValue>=0 and bValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={bValue})", False):
                    bValue=min(255, max(0, bValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'B-VALUE', bValue>=0.0 and bValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={bValue})", False):
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


            self.__checkParamType(currentAst, fctLabel, 'R-VALUE', rValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'G-VALUE', gValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'B-VALUE', bValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'O-VALUE', aValue, int, float)

            if isinstance(rValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'R-VALUE', rValue>=0 and rValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={rValue})", False):
                    rValue=min(255, max(0, rValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'R-VALUE', rValue>=0.0 and rValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={rValue})", False):
                    rValue=min(1.0, max(0.0, rValue))

            if isinstance(gValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'G-VALUE', gValue>=0 and gValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={gValue})", False):
                    gValue=min(255, max(0, gValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'G-VALUE', gValue>=0.0 and gValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={gValue})", False):
                    gValue=min(1.0, max(0.0, gValue))

            if isinstance(bValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'B-VALUE', bValue>=0 and bValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={bValue})", False):
                    bValue=min(255, max(0, bValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'B-VALUE', bValue>=0.0 and bValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={bValue})", False):
                    bValue=min(1.0, max(0.0, bValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
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

            self.__checkParamType(currentAst, fctLabel, 'H-VALUE', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'S-VALUE', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'L-VALUE', lValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(lValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'L-VALUE', lValue>=0 and lValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={lValue})", False):
                    lValue=min(255, max(0, lValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'L-VALUE', lValue>=0.0 and lValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={lValue})", False):
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


            self.__checkParamType(currentAst, fctLabel, 'H-VALUE', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'S-VALUE', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'L-VALUE', lValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'O-VALUE', aValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(lValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'L-VALUE', lValue>=0 and lValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={lValue})", False):
                    lValue=min(255, max(0, lValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'L-VALUE', lValue>=0.0 and lValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={lValue})", False):
                    lValue=min(1.0, max(0.0, lValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
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

            self.__checkParamType(currentAst, fctLabel, 'H-VALUE', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'S-VALUE', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'V-VALUE', vValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(vValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'V-VALUE', vValue>=0 and vValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={vValue})", False):
                    vValue=min(255, max(0, vValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'V-VALUE', vValue>=0.0 and vValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={vValue})", False):
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

            self.__checkParamType(currentAst, fctLabel, 'H-VALUE', hValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'S-VALUE', sValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'V-VALUE', vValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'O-VALUE', aValue, int, float)

            if isinstance(sValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0 and sValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={sValue})", False):
                    sValue=min(255, max(0, sValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'S-VALUE', sValue>=0.0 and sValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={sValue})", False):
                    sValue=min(1.0, max(0.0, sValue))

            if isinstance(vValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'V-VALUE', vValue>=0 and vValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={vValue})", False):
                    vValue=min(255, max(0, vValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'V-VALUE', vValue>=0.0 and vValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={vValue})", False):
                    vValue=min(1.0, max(0.0, vValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
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


            self.__checkParamType(currentAst, fctLabel, 'C-VALUE', cValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'M-VALUE', mValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'Y-VALUE', yValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'K-VALUE', kValue, int, float)

            if isinstance(cValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'C-VALUE', cValue>=0 and cValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={cValue})", False):
                    cValue=min(255, max(0, cValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'C-VALUE', cValue>=0.0 and cValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={cValue})", False):
                    cValue=min(1.0, max(0.0, cValue))

            if isinstance(mValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'M-VALUE', mValue>=0 and mValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={mValue})", False):
                    mValue=min(255, max(0, mValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'M-VALUE', mValue>=0.0 and mValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={mValue})", False):
                    mValue=min(1.0, max(0.0, mValue))

            if isinstance(yValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'Y-VALUE', yValue>=0 and yValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={yValue})", False):
                    yValue=min(255, max(0, yValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'Y-VALUE', yValue>=0.0 and yValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={yValue})", False):
                    yValue=min(1.0, max(0.0, yValue))

            if isinstance(kValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'K-VALUE', kValue>=0 and kValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={kValue})", False):
                    kValue=min(255, max(0, kValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'K-VALUE', kValue>=0.0 and kValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={kValue})", False):
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


            self.__checkParamType(currentAst, fctLabel, 'C-VALUE', cValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'M-VALUE', mValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'Y-VALUE', yValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'K-VALUE', kValue, int, float)
            self.__checkParamType(currentAst, fctLabel, 'O-VALUE', aValue, int, float)

            if isinstance(cValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'C-VALUE', cValue>=0 and cValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={cValue})", False):
                    cValue=min(255, max(0, cValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'C-VALUE', cValue>=0.0 and cValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={cValue})", False):
                    cValue=min(1.0, max(0.0, cValue))

            if isinstance(mValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'M-VALUE', mValue>=0 and mValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={mValue})", False):
                    mValue=min(255, max(0, mValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'M-VALUE', mValue>=0.0 and mValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={mValue})", False):
                    mValue=min(1.0, max(0.0, mValue))

            if isinstance(yValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'Y-VALUE', yValue>=0 and yValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={yValue})", False):
                    yValue=min(255, max(0, yValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'Y-VALUE', yValue>=0.0 and yValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={yValue})", False):
                    yValue=min(1.0, max(0.0, yValue))

            if isinstance(kValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'K-VALUE', kValue>=0 and kValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={kValue})", False):
                    kValue=min(255, max(0, kValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'K-VALUE', kValue>=0.0 and kValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={kValue})", False):
                    kValue=min(1.0, max(0.0, kValue))

            if isinstance(aValue, int):
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0 and aValue<=255, f"allowed value when provided as an integer number is range [0;255] (current={aValue})", False):
                    aValue=min(255, max(0, aValue))
            else:
                if not self.__checkParamDomain(currentAst, fctLabel, 'O-VALUE', aValue>=0.0 and aValue<=1.0, f"allowed value when provided as a decimal number is range [0.0;1.0] (current={aValue})", False):
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
        elif fctName=='color.red':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.red()
        elif fctName=='color.green':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.green()
        elif fctName=='color.blue':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.blue()
        elif fctName=='color.cyan':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.cyan()
        elif fctName=='color.magenta':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.magenta()
        elif fctName=='color.yellow':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.yellow()
        elif fctName=='color.black':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.black()
        elif fctName=='color.hue':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.hue()
        elif fctName=='color.saturation':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.saturation()
        elif fctName=='color.lightness':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.lightness()
        elif fctName=='color.value':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.value()
        elif fctName=='color.opacity':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            color=self.__evaluate(currentAst.node(1))
            self.__checkParamType(currentAst, fctLabel, 'COLOR', color, QColor)
            return color.alpha()
        elif fctName=='list.length':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)

            return len(value)
        elif fctName=='list.join':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            sepChar=self.__evaluate(currentAst.node(2, ','))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)
            self.__checkParamType(currentAst, fctLabel, 'SEPARATOR', sepChar, str)

            # do join; force string conversion of items
            return sepChar.join([item.name() if isinstance(item, QColor) and item.alpha()==255
                                 else item.name(QColor.HexArgb) if isinstance(item, QColor)
                                 else str(item)
                                 for item in value])
        elif fctName=='string.split':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            sepChar=self.__evaluate(currentAst.node(2, ','))

            self.__checkParamType(currentAst, fctLabel, 'TEXT', value, str)
            self.__checkParamType(currentAst, fctLabel, 'SEPARATOR', sepChar, str)

            return value.split(sepChar)
        elif fctName=='list.rotate':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            shiftValue=self.__evaluate(currentAst.node(2, 1))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)
            self.__checkParamType(currentAst, fctLabel, 'VALUE', shiftValue, int)

            return rotate(value, shiftValue)
        elif fctName=='list.sort':
            self.__checkFctParamNumber(currentAst, fctLabel, 1,2)

            value=self.__evaluate(currentAst.node(1))
            ascending=self.__evaluate(currentAst.node(2, True))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)
            self.__checkParamType(currentAst, fctLabel, 'ASCENDING', ascending, bool)

            return sorted(value, key=sortKey, reverse=not ascending)
        elif fctName=='list.revert':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)

            return value[::-1]
        elif fctName=='list.unique':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)

            return unique(value)
        elif fctName=='list.shuffle':
            self.__checkFctParamNumber(currentAst, fctLabel, 1)

            value=self.__evaluate(currentAst.node(1))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)

            return random.sample(value, len(value))
        elif fctName=='list.index':
            self.__checkFctParamNumber(currentAst, fctLabel, 2,3)

            value=self.__evaluate(currentAst.node(1))
            index=self.__evaluate(currentAst.node(2))
            default=self.__evaluate(currentAst.node(3, 0))

            self.__checkParamType(currentAst, fctLabel, 'LIST', value, list)
            self.__checkParamType(currentAst, fctLabel, 'INDEX', index, int)

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

    def __executeListIndexExpression(self, currentAst):
        """return index value"""
        return self.__evaluate(currentAst.node(0))

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

        def raiseException(e, operator):
            """Reformat operator/operand exception for interpeter"""
            if isinstance(e, TypeError):
                result=re.search("'([^']+)'\sand\s'([^']+)'", str(e))
                if not result is None:
                    operator=re.sub(r"'([^']+)'", r"'***\1***'", operator)
                    raise EInterpreter(f"Unsupported operand types ***{self.__valueTypeFromName(result.groups()[0])}*** and ***{self.__valueTypeFromName(result.groups()[1])}*** for {operator}", currentAst)
            raise EInterpreter(str(e), currentAst)

        def applyAnd(leftValue, rightValue):
            # Logical operator can be applied
            # - between 2 boolean values
            # - between 2 integer values
            # - between boolean value and List
            # - between integer value and List
            if isinstance(leftValue, bool) and isinstance(rightValue, bool):
                return leftValue and rightValue
            elif isinstance(rightValue, list):
                return [applyAnd(leftValue, x) for x in rightValue]
            elif isinstance(leftValue, list):
                return [applyAnd(x, rightValue) for x in leftValue]
            else:
                return leftValue & rightValue

        def applyOr(leftValue, rightValue):
            # Logical operator can be applied
            # - between 2 boolean values
            # - between 2 integer values
            # - between boolean value and List
            # - between integer value and List
            if isinstance(leftValue, bool) and isinstance(rightValue, bool):
                return leftValue or rightValue
            elif isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyOr(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyOr(x, rightValue) for x in leftValue]
            else:
                return leftValue | rightValue

        def applyXOr(leftValue, rightValue):
            # Logical operator can be applied
            # - between 2 boolean values
            # - between 2 integer values
            # - between boolean value and List
            # - between integer value and List
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyXOr(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyXOr(x, rightValue) for x in leftValue]
            else:
                return leftValue ^ rightValue

        def applyMultiply(leftValue, rightValue):
            # product operator can be applied
            # - between 2 numeric values
            # - between 1 numeric value and 1 string
            # - between 1 numeric value and 1 list of (int, float)
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyMultiply(x, leftValue) for x in rightValue]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyMultiply(x, rightValue) for x in leftValue]
            else:
                return leftValue * rightValue

        def applyDivide(leftValue, rightValue):
            # divide operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue / rightValue
                raise EInterpreter(f"Division by zero", currentAst)
            elif isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyDivide(leftValue, x) for x in rightValue ]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyDivide(x, rightValue) for x in leftValue]
            else:
                return leftValue / rightValue

        def applyFloorDivide(leftValue, rightValue):
            # Floor division operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue // rightValue
                raise EInterpreter(f"Division by zero", currentAst)
            elif isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyFloorDivide(leftValue, x) for x in rightValue ]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyFloorDivide(x, rightValue) for x in leftValue]
            else:
                return leftValue // rightValue

        def applyModulus(leftValue, rightValue):
            # Modulus operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)):
                if rightValue!=0:
                    return leftValue % rightValue
                raise EInterpreter(f"Division by zero", currentAst)
            elif isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyModulus(leftValue, x) for x in rightValue ]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyModulus(x, rightValue) for x in leftValue]
            else:
                return leftValue % rightValue

        def applyAddition(leftValue, rightValue):
            # addition operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between a string and a numeric value
            # - between a string and a color value
            if (isinstance(leftValue, (int, float)) and isinstance(rightValue, (int, float)) or
                isinstance(leftValue, str) and isinstance(rightValue, str)):
                return leftValue + rightValue
            elif isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applyAddition(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applyAddition(x, rightValue) for x in leftValue]
            elif isinstance(leftValue, str) and isinstance(rightValue, list):
                return [applyAddition(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, str) and isinstance(leftValue, list):
                return [applyAddition(x, rightValue) for x in leftValue]
            elif (isinstance(leftValue, str) and isinstance(rightValue, (int, float)) or
                  isinstance(leftValue, (int, float)) and isinstance(rightValue, str)):
                return f"{leftValue}{rightValue}"
            elif isinstance(leftValue, str) and isinstance(rightValue, QColor):
                return leftValue+self.__strValue(rightValue)
            elif isinstance(leftValue, QColor) and isinstance(rightValue, str):
                return self.__strValue(leftValue)+rightValue
            else:
                return leftValue+rightValue

        def applySubstraction(leftValue, rightValue):
            # Subtraction operator can be applied
            # - between 2 numeric values
            if isinstance(leftValue, (int, float)) and isinstance(rightValue, list):
                return [applySubstraction(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float)) and isinstance(leftValue, list):
                return [applySubstraction(x, rightValue) for x in leftValue]
            else:
                return leftValue - rightValue

        def applyCmpGT(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpGT(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpGT(x, rightValue) for x in leftValue]
            else:
                return leftValue > rightValue

        def applyCmpGE(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpGE(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpGE(x, rightValue) for x in leftValue]
            else:
                return leftValue >= rightValue

        def applyCmpLT(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpLT(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpLT(x, rightValue) for x in leftValue]
            else:
                return leftValue < rightValue

        def applyCmpLE(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpLE(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpLE(x, rightValue) for x in leftValue]
            else:
                return leftValue <= rightValue

        def applyCmpEQ(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpEQ(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpEQ(x, rightValue) for x in leftValue]
            else:
                return leftValue==rightValue

        def applyCmpNE(leftValue, rightValue):
            # Comparison operator can be applied
            # - between 2 numeric values
            # - between 2 string values
            # - between 2 boolean values
            if isinstance(leftValue, (int, float, str, bool)) and isinstance(rightValue, list):
                return [applyCmpNE(leftValue, x) for x in rightValue]
            elif isinstance(rightValue, (int, float, str, bool)) and isinstance(leftValue, list):
                return [applyCmpNE(x, rightValue) for x in leftValue]
            else:
                return leftValue!=rightValue

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
            try:
                return applyMultiply(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "multiply operator '*'")
        elif operator=='/':
            try:
                return applyDivide(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "divide operator '/'")
        elif operator=='//':
            try:
                return applyFloorDivide(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "floor division operator '//'")
        elif operator=='%':
            try:
                return applyModulus(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "modulus operator '%'")
        elif operator=='+':
            try:
                return applyAddition(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "addition operator '+'")
        elif operator=='-':
            try:
                return applySubstraction(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "substraction operator '-'")
        elif operator=='<':
            try:
                return applyCmpLT(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '<'")
        elif operator=='<=':
            try:
                return applyCmpLE(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '<='")
        elif operator=='>':
            try:
                return applyCmpGT(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '>'")
        elif operator=='>=':
            try:
                return applyCmpGE(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '>='")
        elif operator=='=':
            try:
                return applyCmpEQ(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '='")
        elif operator=='<>':
            try:
                return applyCmpNE(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "comparison operator '<>'")
        elif operator=='in':
            # Comparison operator can be applied
            # - between any value and a list
            if isinstance(rightValue, list):
                return leftValue in rightValue

            # not a valid operation, raise an error
            raise EInterpreter(f"In list operator 'in' can only be applied to a list", currentAst)
        elif operator=='and':
            try:
                return applyAnd(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "logical operator 'AND'")
        elif operator=='or':
            try:
                return applyOr(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "logical operator 'OR'")
        elif operator=='xor':
            try:
                return applyXOr(leftValue, rightValue)
            except Exception as e:
                raiseException(e, "logical operator 'XOR'")

        # should not occurs
        raise EInterpreter(f"Unknown operator: {operator}", currentAst)

    def __executeIndexOperator(self, currentAst):
        """return unary operation result"""
        fctLabel='list[index]'
        # defined by 2 nodes (ASTItem)
        # - 1st node= index value
        # - 2nd node = list or string

        indexValue=self.__evaluate(currentAst.node(0))
        listValue=self.__evaluate(currentAst.node(1))

        self.__checkParamType(currentAst, fctLabel, 'INDEX', indexValue, int)
        self.__checkParamType(currentAst, fctLabel, 'LIST', listValue, list, str)

        if isinstance(listValue, str):
            lenOf='string'
        else:
            lenOf='list'

        if not self.__checkParamDomain(currentAst, fctLabel, 'INDEX', abs(indexValue)>=1 and abs(indexValue)<=len(listValue), f"given index must be in range [1; length of {lenOf}] (current={indexValue})", False):
            # if value<=0, exit
            return None

        if indexValue>0:
            returned=listValue[indexValue - 1]
        else:
            returned=listValue[indexValue]

        return returned

    # --------------------------------------------------------------------------
    # Internal -- can be called directly without AST definition
    # --------------------------------------------------------------------------

    def __updateGeometry(self):
        """Update geometry according to document bounds and origin position"""
        self.__scriptBlockStack.setVariable(':canvas.geometry.resolution', self.__currentDocumentResolution, BSVariableScope.GLOBAL)
        # width & height always match to document dimension
        self.__scriptBlockStack.setVariable(':canvas.geometry.width', self.__currentDocumentBounds.width(), BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.geometry.height', self.__currentDocumentBounds.height(), BSVariableScope.GLOBAL)

        # letft, right, top and bottom are relative to origin
        absissa=self.__scriptBlockStack.variable(':canvas.origin.position.absissa', 'CENTER')
        ordinate=self.__scriptBlockStack.variable(':canvas.origin.position.ordinate', 'MIDDLE')

        if absissa=='CENTER':
            halfWidth=self.__currentDocumentBounds.width()/2
            self.__currentDocumentGeometry.setLeft(-halfWidth)
            self.__currentDocumentGeometry.setRight(halfWidth)

            self.__scriptBlockStack.setVariable(':canvas.geometry.left', -halfWidth, BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.right', halfWidth, BSVariableScope.GLOBAL)
        elif absissa=='LEFT':
            self.__currentDocumentGeometry.setLeft(0)
            self.__currentDocumentGeometry.setRight(self.__currentDocumentBounds.width())

            self.__scriptBlockStack.setVariable(':canvas.geometry.left', 0, BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.right', self.__currentDocumentBounds.width(), BSVariableScope.GLOBAL)
        elif absissa=='RIGHT':
            self.__currentDocumentGeometry.setLeft(self.__currentDocumentBounds.width())
            self.__currentDocumentGeometry.setRight(0)

            self.__scriptBlockStack.setVariable(':canvas.geometry.left', self.__currentDocumentBounds.width(), BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.right', 0, BSVariableScope.GLOBAL)

        if ordinate=='MIDDLE':
            halfHeight=self.__currentDocumentBounds.height()/2
            self.__currentDocumentGeometry.setTop(halfHeight)
            self.__currentDocumentGeometry.setBottom(-halfHeight)

            self.__scriptBlockStack.setVariable(':canvas.geometry.top', halfHeight, BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.bottom', -halfHeight, BSVariableScope.GLOBAL)
        elif ordinate=='TOP':
            self.__currentDocumentGeometry.setTop(0)
            self.__currentDocumentGeometry.setBottom(self.__currentDocumentBounds.height())

            self.__scriptBlockStack.setVariable(':canvas.geometry.top', 0, BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.bottom', self.__currentDocumentBounds.height(), BSVariableScope.GLOBAL)
        elif ordinate=='BOTTOM':
            self.__currentDocumentGeometry.setTop(self.__currentDocumentBounds.height())
            self.__currentDocumentGeometry.setBottom(0)

            self.__scriptBlockStack.setVariable(':canvas.geometry.top', self.__currentDocumentBounds.height(), BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.geometry.bottom', 0, BSVariableScope.GLOBAL)

        BSConvertUnits.initMeasures(self.__currentDocumentGeometry, self.__currentDocumentResolution)


    def __setUnitCanvas(self, value):
        """Set canvas unit

        :unit.canvas
        """
        self.warning("to finalize: __setUnitCanvas")
        self.__scriptBlockStack.setVariable(':unit.canvas', value, BSVariableScope.CURRENT)

    def __setUnitRotation(self, value):
        """Set canvas unit

        :unit.rotation
        """
        self.warning("to finalize: __setUnitRotation")
        self.__scriptBlockStack.setVariable(':unit.rotation', value, BSVariableScope.CURRENT)

    def __setPenColor(self, value):
        """Set pen color

        :pen.color
        """
        self.warning("to finalize: __setPenColor")
        color=self.__scriptBlockStack.current().variable(':pen.color', QColor(0,0,0))
        value.setAlpha(color.alpha())
        self.__scriptBlockStack.setVariable(':pen.color', value, BSVariableScope.CURRENT)

    def __setPenSize(self, value, unit=None):
        """Set pen size

        :pen.size
        """
        self.warning("to finalize: __setPenSize")
        self.__scriptBlockStack.setVariable(':pen.size', value, BSVariableScope.CURRENT)

    def __setPenStyle(self, value):
        """Set pen style

        :pen.style
        """
        self.warning("to finalize: __setPenStyle")
        self.__scriptBlockStack.setVariable(':pen.style', value, BSVariableScope.CURRENT)

    def __setPenCap(self, value):
        """Set pen cap

        :pen.cap
        """
        self.warning("to finalize: __setPenCap")
        self.__scriptBlockStack.setVariable(':pen.cap', value, BSVariableScope.CURRENT)

    def __setPenJoin(self, value):
        """Set pen join

        :pen.join
        """
        self.warning("to finalize: __setPenJoin")
        self.__scriptBlockStack.setVariable(':pen.join', value, BSVariableScope.CURRENT)

    def __setPenOpacity(self, value):
        """Set pen opacity

        :pen.color
        """
        self.warning("to finalize: __setPenOpacity")
        color=self.__scriptBlockStack.current().variable(':pen.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.setVariable(':pen.color', color, BSVariableScope.CURRENT)

    def __setFillColor(self, value):
        """Set fill color

        :fill.color
        """
        self.warning("to finalize: __setFillColor")
        color=self.__scriptBlockStack.current().variable(':fill.color', QColor(0,0,0))
        value.setAlpha(color.alpha())
        self.__scriptBlockStack.setVariable(':fill.color', color, BSVariableScope.CURRENT)

    def __setFillRule(self, value):
        """Set fill rule

        :fill.rule
        """
        self.warning("to finalize: __setFillRule")
        self.__scriptBlockStack.setVariable(':fill.rule', value, BSVariableScope.CURRENT)

    def __setFillOpacity(self, value):
        """Set fill opacity

        :fill.color
        """
        self.warning("to finalize: __setFillOpacity")
        color=self.__scriptBlockStack.current().variable(':fill.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)
        self.__scriptBlockStack.setVariable(':fill.color', color, BSVariableScope.CURRENT)

    def __setTextColor(self, value):
        """Set text color

        :text.color
        """
        self.warning("to finalize: __setTextColor")
        color=self.__scriptBlockStack.current().variable(':text.color', QColor(0,0,0))
        value.setAlpha(color.alpha())
        self.__scriptBlockStack.setVariable(':text.color', value, BSVariableScope.CURRENT)

    def __setTextOpacity(self, value):
        """Set text opacity

        :text.color
        """
        self.warning("to finalize: __setTextOpacity")
        color=self.__scriptBlockStack.current().variable(':text.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)
        self.__scriptBlockStack.setVariable(':text.color', color, BSVariableScope.CURRENT)

    def __setTextFont(self, value):
        """Set text font

        :text.font
        """
        self.warning("to finalize: __setTextFont")
        self.__scriptBlockStack.setVariable(':text.font', value, BSVariableScope.CURRENT)

    def __setTextSize(self, value, unit=None):
        """Set text size

        :text.size
        """
        self.warning("to finalize: __setTextSize")
        self.__scriptBlockStack.setVariable(':text.size', value, BSVariableScope.CURRENT)

    def __setTextBold(self, value):
        """Set text bold

        :text.bold
        """
        self.warning("to finalize: __setTextBold")
        self.__scriptBlockStack.setVariable(':text.bold', value, BSVariableScope.CURRENT)

    def __setTextItalic(self, value):
        """Set text italic

        :text.italic
        """
        self.warning("to finalize: __setTextItalic")
        self.__scriptBlockStack.setVariable(':text.italic', value, BSVariableScope.CURRENT)

    def __setTextLetterSpacing(self, value, unit='PCT'):
        """Set text letter spacing

        :text.letterSpacing.spacing
        :text.letterSpacing.unit
        """
        self.warning("to finalize: __setTextLetterSpacing")
        self.__scriptBlockStack.setVariable(':text.letterspacing.spacing', value, BSVariableScope.CURRENT)
        self.__scriptBlockStack.setVariable(':text.letterspacing.unit', unit, BSVariableScope.CURRENT)

    def __setTextStretch(self, value):
        """Set text stretch

        :text.stretch
        """
        self.warning("to finalize: __setTextStretch")
        self.__scriptBlockStack.setVariable(':text.stretch', value, BSVariableScope.CURRENT)

    def __setTextHAlignment(self, value):
        """Set text horizontal alignment

        :text.alignment.horizontal
        """
        self.warning("to finalize: __setTextHAlignment")
        self.__scriptBlockStack.setVariable(':text.alignment.horizontal', value, BSVariableScope.CURRENT)

    def __setTextVAlignment(self, value):
        """Set text vertical alignment

        :text.alignment.vertical
        """
        self.warning("to finalize: __setTextVAlignment")
        self.__scriptBlockStack.setVariable(':text.alignment.vertical', value, BSVariableScope.CURRENT)

    def __setDrawAntialiasing(self, value):
        """Set draw antialiasing

        :draw.antialiasing
        """
        self.warning("to finalize: __setDrawAntialiasing")
        self.__scriptBlockStack.setVariable(':draw.antialiasing', value, BSVariableScope.CURRENT)

    def __setDrawBlending(self, value):
        """Set draw blending mode

        :draw.blendingMode
        """
        self.warning("to finalize: __setDrawBlending")
        self.__scriptBlockStack.setVariable(':draw.blendingmode', value, BSVariableScope.CURRENT)

    def __setDrawFillStatus(self, value):
        """Set if brush is activated or not

        :fill.status
        """
        self.__scriptBlockStack.setVariable(':fill.status', value, BSVariableScope.CURRENT)
    def __setDrawOpacity(self, value):
        """Set global drawing opacity

        :draw.opacity
        """
        self.__scriptBlockStack.setVariable(':draw.opacity', value, BSVariableScope.CURRENT)

    def __setCanvasGridColor(self, value):
        """Set canvas grid color

        :canvas.grid.color
        """
        self.__scriptBlockStack.setVariable(':canvas.grid.color', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridPenColor(value)

    def __setCanvasGridBgColor(self, value):
        """Set canvas grid color

        :canvas.grid.bgColor
        """
        self.__scriptBlockStack.setVariable(':canvas.grid.bgColor', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridBrushColor(value)

    def __setCanvasGridStyleMain(self, value):
        """Set canvas grid style

        :canvas.grid.style.main
        """
        self.__scriptBlockStack.setVariable(':canvas.grid.style.main', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridPenStyleMain(BSInterpreter.__CONV_PEN_STYLE[value])

    def __setCanvasGridStyleSecondary(self, value):
        """Set canvas grid style

        :canvas.grid.style.secondary
        """
        self.__scriptBlockStack.setVariable(':canvas.grid.style.secondary', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridPenStyleSecondary(BSInterpreter.__CONV_PEN_STYLE[value])

    def __setCanvasGridOpacity(self, value):
        """Set canvas grid opacity

        :canvas.grid.color
        """
        color=self.__scriptBlockStack.current().variable(':canvas.grid.color', QColor(0,0,0))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.setVariable(':canvas.grid.color', color, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridPenOpacity(color.alphaF())

    def __setCanvasGridSize(self, width, main, unit=None):
        """Set canvas grid size

        :canvas.grid.size.width
        :canvas.grid.size.main
        """
        self.warning("to finalize: __setCanvasGridSize")
        self.__scriptBlockStack.setVariable(':canvas.grid.size.width', width, BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.grid.size.main', main, BSVariableScope.GLOBAL)

        self.__renderedScene.setGridSize(width, main)

    def __setCanvasRulersColor(self, value):
        """Set canvas rulers color

        :canvas.rulers.color
        """
        self.__scriptBlockStack.setVariable(':canvas.rulers.color', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridPenRulerColor(value)

    def __setCanvasRulersBgColor(self, value):
        """Set canvas rulers color

        :canvas.rulers.bgColor
        """
        self.__scriptBlockStack.setVariable(':canvas.rulers.bgColor', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridBrushRulerColor(value)

    def __setCanvasOriginColor(self, value):
        """Set canvas origin color

        :canvas.origin.color
        """
        self.__scriptBlockStack.setVariable(':canvas.origin.color', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginPenColor(value)

    def __setCanvasOriginStyle(self, value):
        """Set canvas origin style

        :canvas.origin.style
        """
        self.__scriptBlockStack.setVariable(':canvas.origin.style', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginPenStyle(BSInterpreter.__CONV_PEN_STYLE[value])

    def __setCanvasOriginOpacity(self, value):
        """Set canvas origin opacity

        :canvas.origin.color
        """
        color=self.__scriptBlockStack.current().variable(':canvas.origin.color', QColor(60,60,128))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.setVariable(':canvas.origin.color', color, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginPenOpacity(color.alphaF())

    def __setCanvasOriginSize(self, value, unit=None):
        """Set canvas origin size

        :canvas.origin.size
        """
        self.warning("to finalize: __setCanvasOriginSize")
        self.__scriptBlockStack.setVariable(':canvas.origin.size', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginSize(value)

    def __setCanvasOriginPosition(self, absissa, ordinate):
        """Set canvas origin position

        :canvas.origin.position.absissa
        :canvas.origin.position.ordinate
        """
        self.warning("to finalize: __setCanvasOriginPosition")
        self.__scriptBlockStack.setVariable(':canvas.origin.position.absissa', absissa, BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.origin.position.ordinate', ordinate, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginPosition(BSInterpreter.__CONST_HALIGN[absissa], BSInterpreter.__CONST_VALIGN[ordinate])
        self.__updateGeometry()

    def __setCanvasPositionColor(self, value):
        """Set canvas position color

        :canvas.position.color
        """
        self.__scriptBlockStack.setVariable(':canvas.position.color', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setPositionPenColor(value)

    def __setCanvasPositionOpacity(self, value):
        """Set canvas position opacity

        :canvas.position.color
        """
        color=self.__scriptBlockStack.current().variable(':canvas.position.color', QColor(60,60,128))
        if isinstance(value, int):
            color.setAlpha(value)
        else:
            color.setAlphaF(value)

        self.__scriptBlockStack.setVariable(':canvas.position.color', color, BSVariableScope.GLOBAL)
        self.__renderedScene.setPositionPenOpacity(color.alphaF())

    def __setCanvasPositionSize(self, value, unit=None):
        """Set canvas position size

        :canvas.position.size
        """
        self.warning("to finalize: __setCanvasPositionSize")
        self.__scriptBlockStack.setVariable(':canvas.position.size', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setPositionSize(value)

    def __setCanvasPositionFulfill(self, value):
        """Set canvas position fulfilled

        :canvas.position.fulfill
        """
        self.__scriptBlockStack.setVariable(':canvas.position.fulfill', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setPositionFulfill(value)

    def __setCanvasPositionAxis(self, value):
        """Set canvas position axis

        :canvas.position.axis
        """
        self.__scriptBlockStack.setVariable(':canvas.position.axis', value, BSVariableScope.GLOBAL)

    def __setCanvasPositionModel(self, value):
        """Set canvas position model

        :canvas.position.model
        """
        self.__scriptBlockStack.setVariable(':canvas.position.model', value, BSVariableScope.GLOBAL)

    def __setCanvasBackgroundOpacity(self, value):
        """Set canvas background opacity

        :canvas.background.opacity
        """
        self.__scriptBlockStack.setVariable(':canvas.background.opacity', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setBackgroundOpacity(value)

    def __setCanvasBackgroundFromColor(self, value):
        """Set canvas background from color

        :canvas.background.source.type
        :canvas.background.source.value
        """
        self.__scriptBlockStack.setVariable(':canvas.background.source.type', 'color', BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.background.source.value', value, BSVariableScope.GLOBAL)

        pixmap=QPixmap(self.__currentDocumentBounds.size())
        pixmap.fill(value)

        self.__renderedScene.setBackgroundImage(pixmap, self.__currentDocumentBounds)

    def __setCanvasBackgroundFromDocument(self):
        """Set canvas background from document

        :canvas.background.source.type
        :canvas.background.source.value
        """
        self.__scriptBlockStack.setVariable(':canvas.background.source.type', 'document', BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.background.source.value', self.__currentDocument.fileName(), BSVariableScope.GLOBAL)

        self.__currentDocument.refreshProjection()
        pixmap=QPixmap.fromImage(self.__currentDocument.projection(self.__currentDocumentBounds.left(), self.__currentDocumentBounds.top(), self.__currentDocumentBounds.width(), self.__currentDocumentBounds.height()))

        self.__renderedScene.setBackgroundImage(pixmap, self.__currentDocumentBounds)

    def __setCanvasBackgroundFromLayerActive(self):
        """Set canvas background from layer active

        :canvas.background.source.type
        :canvas.background.source.value
        """
        self.__scriptBlockStack.setVariable(':canvas.background.source.type', 'layer active', BSVariableScope.GLOBAL)
        self.__scriptBlockStack.setVariable(':canvas.background.source.value', self.__currentLayer.name(), BSVariableScope.GLOBAL)

        pixmap=EKritaNode.toQPixmap(self.__currentLayer)
        self.__renderedScene.setBackgroundImage(pixmap, self.__currentLayerBounds)
        return ('layer active', self.__currentLayer.name())

    def __setCanvasBackgroundFromLayerName(self, value):
        """Set canvas background from layer name

        :canvas.background.source.type
        :canvas.background.source.value
        """
        node=EKritaDocument.findFirstLayerByName(self.__currentDocument, value)
        if node is None:
            return self.__setCanvasBackgroundFromLayerActive()
        else:
            self.__scriptBlockStack.setVariable(':canvas.background.source.type', 'layer name', BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.background.source.value', value, BSVariableScope.GLOBAL)

        pixmap=EKritaNode.toQPixmap(node)
        self.__renderedScene.setBackgroundImage(pixmap, node.bounds())
        return ('layer name', value)

    def __setCanvasBackgroundFromLayerId(self, value):
        """Set canvas background from layer id

        :canvas.background.source.type
        :canvas.background.source.value
        """
        try:
            uuid=QUuid(value)
            node=EKritaDocument.findLayerById(self.__currentDocument, uuid)
        except Exception as e:
            node=None

        if node is None:
            return self.__setCanvasBackgroundFromLayerActive()
        else:
            self.__scriptBlockStack.setVariable(':canvas.background.source.type', 'layer id', BSVariableScope.GLOBAL)
            self.__scriptBlockStack.setVariable(':canvas.background.source.value', str(node.uniqueId()), BSVariableScope.GLOBAL)

        pixmap=EKritaNode.toQPixmap(node)
        self.__renderedScene.setBackgroundImage(pixmap, node.bounds())
        return ('layer id', str(node.uniqueId()))

    def __setExecutionVerbose(self, value):
        """Set script execution verbose

        :script.execution.verbose
        """
        self.__scriptBlockStack.setVariable(':script.execution.verbose', value, BSVariableScope.CURRENT)
        self.__optionVerboseMode=value

    def __setRandomizeSeed(self, value=None):
        """Set script randomize seed

        :script.randomize.seed
        """
        if value is None or isinstance(value, int) and value<0:
            random.seed()
            randSeed=random.randint(0,999999999)
        else:
            randSeed=value
        random.seed(randSeed)

        self.__scriptBlockStack.setVariable(':script.randomize.seed', randSeed, BSVariableScope.GLOBAL)

    def __setCanvasGridVisible(self, value):
        """Show canvas grid

        :canvas.grid.visibility
        """
        self.__scriptBlockStack.setVariable(':canvas.grid.visibility', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridVisible(value)

    def __setCanvasOriginVisible(self, value):
        """Show canvas origin

        :canvas.origin.visibility
        """
        self.__scriptBlockStack.setVariable(':canvas.origin.visibility', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setOriginVisible(value)

    def __setCanvasPositionVisible(self, value):
        """Show canvas position

        :canvas.position.visibility
        """
        self.__scriptBlockStack.setVariable(':canvas.position.visibility', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setPositionVisible(value)

    def __setCanvasBackgroundVisible(self, value):
        """Show canvas background

        :canvas.background.visibility
        """
        self.__scriptBlockStack.setVariable(':canvas.background.visibility', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setBackgroundVisible(value)

    def __setCanvasRulersVisible(self, value):
        """Show canvas rulers

        :canvas.rulers.visibility
        """
        self.__scriptBlockStack.setVariable(':canvas.rulers.visibility', value, BSVariableScope.GLOBAL)
        self.__renderedScene.setGridRulerVisible(value)

    def __setDrawShapeStatus(self, value):
        """Start to draw shape

        :draw.shape.status
        """
        self.warning("to finalize: __setDrawShapeStatus")
        self.__scriptBlockStack.setVariable(':draw.shape.status', value, BSVariableScope.CURRENT)


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

        totalTime=None

        self.valid("**Parse script** ")
        if script!=self.__script:
            startTime=time.time()
            self.__script=script
            self.__astRoot=self.__parser.parse(self.__script)
            totalTime=round(time.time()-startTime,4)

        #Debug.print('setScript/AST: {0}', self.__astRoot)

        if len(self.__parser.errors())>0:
            errMsgList=[]

            for error in self.__parser.errors():
                errMsgList.append(f"#r#{error.errorMessage()}#, *line* #y#***{error.errorToken().row()}***# ")

                if error.errorGrammarRule():
                    pass
                if error.errorAst():
                    pass

            errMsg='\n'.join(errMsgList)

            raise EInterpreter(f"Can't parse*#, {errMsg}*#w#", self.__astRoot)

        if totalTime:
            self.print(f"#w#[Parsed in# #lw#*{totalTime}s*##w#]#", cReturn=False)
        else:
            self.print(f"#w#[Already parsed]#", cReturn=False)

    def execute(self, reset=True):
        """Execute script

        If `reset` is True, all execution environment is reseted to default values:
        - Default configuration for canvas, position, pen, ...
        - Stack, Variables, Macro definition are cleaned

        If False, all informations from last execution are kept
        """
        if self.__isRunning:
            # can't execute while previous execution is not yet finished
            raise EInterpreterInternalError("Interpreter is already running", None)

        self.__isRunning=True
        self.executionStarted.emit()

        try:
            returned=self.__executeStart(reset)
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

    # --------------------------------------------------------------------------
    # options
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



class BSVariableScope(Enum):
    CURRENT = 0
    LOCAL = 1
    GLOBAL = 2


class BSScriptBlockProperties:
    """Define current script block properties"""

    def __init__(self, parent, ast, allowLocalVariable, id, rootStack):
        if not(parent is None or isinstance(parent, BSScriptBlockProperties)):
            raise EInvalidType("Given `parent` must be None or a <BSScriptBlockProperties>")

        # keep a pointer to first stack block (root, used for global variables)
        self.__rootStack=rootStack

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

    def setVariable(self, name, value, scope):
        """Set `value` for variable designed by given `name`

        Given `scope` can be:
        - BSVariableScope.CURRENT: if current scope allows local variable, set to current scope otherwise et to parent scope
        - BSVariableScope.LOCAL:   force to be local even if local variables are not allowed
        - BSVariableScope.GLOBAL:  force to be at global scope

        If variable doesn't exist in script block, create it
        """
        name=name.lower()
        if scope==BSVariableScope.GLOBAL:
            if self.__rootStack:
                self.__rootStack.setVariable(name, value, BSVariableScope.GLOBAL)
            else:
                # occurs if current block is already root stack
                self.__variables[name]=value
        elif scope==BSVariableScope.LOCAL:
            self.__variables[name]=value
        else:
            # current
            if self.__allowLocalVariable:
                self.__variables[name]=value
            elif not self.__parent is None:
                self.__parent.setVariable(name, value, scope)
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
        self.__current=None
        self.clear()

    def push(self, ast, allowLocalVariable, name=None):
        if len(self.__stack)>0:
            parent=self.__stack[-1]
        else:
            parent=None

        if len(self.__stack)<self.__maxStackSize:
            self.__stack.append(BSScriptBlockProperties(parent, ast, allowLocalVariable, name, self.__stack[0] if len(self.__stack)>0 else None))
            self.__current=self.__stack[-1]
        else:
            raise EInvalidStatus(f"Current stack size limit ({self.__maxStackSize}) reached!")

    def pop(self):
        """Pop current script block stack"""
        # do not control if there's something to pop
        # normally this method is called only if stack is not empty
        # if called on an empty stack, must raise an error because it must never occurs
        returned=self.__stack.pop()

        if len(self.__stack)>0:
            self.__current=self.__stack[-1]
        else:
            self.__current=None

        return returned

    def current(self):
        """Return current script block

        If nothing in stack, return None
        """
        return self.__current

    def count(self):
        """Return number of script block in stack"""
        return len(self.__stack)

    def clear(self):
        """Clear stack"""
        self.__stack.clear()
        self.push(ASTItem("<STACK.GLOBAL.VARIABLES>"), True, "<STACK.GLOBAL.VARIABLES>")

    def variable(self, name, default=None):
        """Shortcut to get variable from current block in stack"""
        if self.__current:
            return self.__current.variable(name, default)
        else:
            return default

    def setVariable(self, name, value, scope):
        """Shortcut to set variable from current block in stack"""
        if self.__current:
            self.__current.setVariable(name, value, scope)


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
    """Convert unit class provide simple methods to convert a unit to another one
    - Angle (Radian, Degree)
    - Measures (Pixels, Millimeters, Inches, Percentage)
        => measures take in account current document geometry (size, resolution) for calculation
    """

    __CONV_TABLE={}

    @staticmethod
    def initMeasures(documentGeometry, documentResolution):
        """Initialise conversion table using:
        - document size (width, height)
        - document resolution
        """
        if documentResolution<=0:
            documentResolution=1.0

        BSConvertUnits.__CONV_TABLE={
                'PXMM':         25.4/documentResolution,
                'PXINCH':       1/documentResolution,
                'PXPCTW':       100/documentGeometry.width(),
                'PXPCTH':       100/documentGeometry.height(),

                'MMPX':         documentResolution/25.4,
                'MMINCH':       1/25.4,
                'MMPCTW':       (100*documentResolution)/(documentGeometry.width()*25.4),
                'MMPCTH':       (100*documentResolution)/(documentGeometry.height()*25.4),

                'INCHPX':       documentResolution,
                'INCHMM':       25.4,
                'INCHPCTW':     documentResolution*100/documentGeometry.width(),
                'INCHPCTH':     documentResolution*100/documentGeometry.height(),

                'PCTPXW':       documentGeometry.width()/100,
                'PCTPXH':       documentGeometry.height()/100,
                'PCTMMW':       0.254*documentGeometry.width()/documentResolution,
                'PCTMMH':       0.254*documentGeometry.height()/documentResolution,
                'PCTINCHW':     documentGeometry.width()/(100*documentResolution),
                'PCTINCHH':     documentGeometry.height()/(100*documentResolution),

                'DEGREERADIAN': math.pi/180,
                'RADIANDEGREE': 180/math.pi
            }

    @staticmethod
    def convertAngle(value, fromUnit, toUnit):
        if fromUnit!=toUnit:
            key=fromUnit+toUnit
            if key in BSConvertUnits.__CONV_TABLE:
                return value*BSConvertUnits.__CONV_TABLE[key]
        return value

    @staticmethod
    def convertMeasure(value, fromUnit, toUnit, refPct='W'):
        if fromUnit!=toUnit:
            key=fromUnit+toUnit
            if refPct and refPct in 'WH':
                key+=refPct
            if key in BSConvertUnits.__CONV_TABLE:
                return value*BSConvertUnits.__CONV_TABLE[key]
        return value



Debug.setEnabled(True)
