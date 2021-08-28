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

from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )


class EInterpreter(Exception):
    """An error occured during execution"""
    def __init__(self, message, ast):
        super(EInterpreter, self).__init__(message)
        self.__ast=ast

    def ast(self):
        return self.__ast

class EInterpreterInternalError(EInterpreter):
    """An error occured during execution"""
    def __init__(self, message, ast):
        super(EInterpreterInternalError, self).__init__(f"Internal error: <<{message}>>", ast)


class BSInterpreter(QObject):
    """The interpreter execute provided BuliScript script"""
    actionExecuted = Signal(str)
    executionStarted = Signal()
    executionFinished = Signal()

    CONST_MEASURE_UNIT=['PX', 'PCT', 'MM', 'INCH']
    CONST_ROTATION_UNIT=['DEGREE', 'RADIAN']
    CONST_PEN_STYLE=['SOLID','DASH','DOT','DASHDOT','NONE']
    CONST_PEN_CAP=['SQUARE','FLAT','ROUNDCAP']
    CONST_PEN_JOIN=['BEVEL','MITTER','ROUNDJOIN']

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
        print(msg)

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
        print(msg)

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
        print(msg)



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
        """raise an exception is number of provided parameters is not expected (used for functions)"""
        if not len(currentAst.nodes())-1 in values:
            raise EInterpreter(f"{fctLabel}: invalid number of provided arguments", currentAst)

    def __checkParamNumber(self, currentAst, fctLabel, *values):
        """raise an exception is number of provided parameters is not expected (used for others)"""
        if not len(currentAst.nodes()) in values:
            raise EInterpreter(f"{fctLabel}: invalid number of provided arguments", currentAst)

    def __checkParamType(self, currentAst, fctLabel, name, value, *types):
        """raise an exception is value if not of given type"""
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
        elif currentAst.id() == 'Flow_Set_Variable':
            return self.__executeFlowSetVariable(currentAst)
        elif currentAst.id() == 'Flow_Define_Macro':
            return self.__executeFlowDefineMacro(currentAst)

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

    def __executeScriptBlock(self, currentAst, allowLocalVariable, name):
        """Execute a script block

        Each script block:
        - is defined by a UUID
        - keep is own local variables
        - can access to parent variables
        """
        self.__verbose(f"Enter scriptblock: '{name}'", currentAst)
        self.__scriptBlockStack.push(currentAst, allowLocalVariable, name)

        for ast in currentAst.nodes():
            # execute all instructions from current script block
            if currentAst.id()==ASTSpecialItemType.ROOT and ast.id()=='ScriptBlock':
                # we are in a special case, still in main script block
                for subAst in ast.nodes():
                    self.__executeAst(subAst)
            else:
                self.__executeAst(ast)

        Debug.print("Variables: {0}", self.__scriptBlockStack.current().variables(True))
        self.__scriptBlockStack.pop()
        self.__verbose(f"Exit scriptblock: '{name}'", currentAst)


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


    # --------------------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------------------
    def __executeActionSetUnitCanvas(self, currentAst):
        """Set canvas unit

        :unit.coordinates
        """
        fctLabel='Action `set unit canvas`'
        self.__checkParamNumber(currentAst, fctLabel, 1)
        value=self.__evaluate(currentAst.node(0))

        self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', value in BSInterpreter.CONST_MEASURE_UNIT, f"measure unit value for canvas can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")

        self.__verbose(f"set unit canvas {self.__strValue(value)}      => :unit.coordinates", currentAst)

        self.__scriptBlockStack.current().setVariable(':unit.coordinates', value, True)

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
            self.__checkParamDomain(currentAst, fctLabel, '<UNIT>', unit in BSInterpreter.CONST_MEASURE_UNIT, f"measure unit value for canvas can be: {', '.join(BSInterpreter.CONST_MEASURE_UNIT)}")
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
        if name in self.__variables:
            return self.__variables[name]
        elif not self.__parent is None:
            return self.__parent.variable(name, default)
        else:
            return default

    def setVariable(self, name, value, localVariable):
        """Set `value` for variable designed by given `name`

        If variable doesn't exist in script block, create it
        """
        if localVariable and self.__allowLocalVariable or not localVariable:
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
