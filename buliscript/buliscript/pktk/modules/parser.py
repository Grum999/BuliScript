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


import hashlib
from enum import Enum

from PyQt5.Qt import *
from PyQt5.QtCore import qDebug

from .elist import EList
from .tokenizer import (
        Token,
        Tokenizer,
        TokenizerRule,
        TokenType
    )

from ..pktk import *



class Parser:
    """Generic language parser"""

    def __init__(self, tokenizer, grammarRules):
        """Initialise parser

        Given `tokens` is a EList of tokens (from Tokenizer.tokenize() method)
        """
        if not isinstance(tokenizer, Tokenizer):
            raise EInvalidType("Given `tokenizer` must be a <Tokenizer>")
        if not isinstance(grammarRules, GrammarRules):
            raise EInvalidType('Given `grammarRules` must be a <GrammarRules>')

        # tokenizer is use to tokenize text and retrieve tokens
        self.__tokenizer=tokenizer
        # tokenized text
        self.__tokens=None

        # list of token that are ignored during parsing (usually, spaces & comments)
        self.__ignoredTokens=[]


        # contain SHA1 value for last parsed text
        # allows to avoid parsing of text if last parsed text was exactly the same
        self.__hashText=None


        # grammar is used to buimld AST from tokens
        self.__grammarRules=grammarRules

        # stored AST (Abstract Syntax Tree)
        # by default is None is nothing has been parsed
        self.__ast=None

        # store errors encountered during parsing (syntax not match grammar)
        self.__errors=[]


    def __parse(self):
        """Parse given tokens:
            - check grammar according defined GrammarRule rules
            - build AST (Abstract Syntax Tree)
        """
        def checkGrammarRule(id):
            # retrieve current token
            token=self.__tokens.value()

            # get current grammar rule for given `id`
            currentGrammarRule=self.__grammarRules.get(id)

            for grammarObject in currentGrammarRule.grammarList():
                checked=grammarObject.check(self.__tokens, self.__ignoredTokens)
                self.__ast.add(checked)
                if checked.status()==ASTStatus.END:
                    break
                elif checked.status()!=ASTStatus.MATCH:
                    self.__ast.setStatus(ASTStatus.INVALID)
                    self.__errors.append(ParserError(i18n("Invalid syntax"), self.__tokens.value(), grammarObject, checked))
                    return

                #if checked.countNodes()>0:
                # only take in account AST for which nodes have been found,
                # even if valid (example: optional can be valid, because nothing found)
                #self.__ast.add(checked)

            if self.__tokens.value() is None:
                # All tokens have been parsed!
                self.__ast.setStatus(ASTStatus.MATCH)
            else:
                # All tokens have not been parsed, that's not a normal case
                self.__ast.setStatus(ASTStatus.INVALID)
                self.__errors.append(ParserError(i18n("Some tokens have not been parsed"), self.__tokens.value()))

        # result errors list
        self.__errors=[]

        # intialise empty AST
        self.__ast=ASTItem(ASTSpecialItemType.ROOT)

        # rewind tokens list to first position
        token=self.__tokens.first()
        while not token is None:
            #Debug.print(token)
            token=self.__tokens.next()

        self.__tokens.first()

        # start to check grammar rules for tokens
        checkGrammarRule(self.__grammarRules.idFirst())
        #Debug.print(self.__ast)


    def grammarRules(self):
        """Return GrammarRules used by parser"""
        return self.__grammarRules


    def tokenizer(self):
        """Return tokenizer used by parser"""
        return self.__tokenizer


    def ignoredTokens(self):
        """Return list of tokens ignored during parsing"""
        return self.__ignoredTokens


    def setIgnoredTokens(self, tokens):
        """Return list of tokens ignored during parsing"""
        if not (isinstance(tokens, list) or isinstance(tokens, tuple)):
            raise EInvalidType("Given `tokens` must be <list> or <tuple>")

        self.__ignoredTokens=[]
        for token in tokens:
            if not isinstance(token, TokenType):
                raise EInvalidType("Given `tokens` items must be <TokenType>")
            self.__ignoredTokens.append(token)


    def parse(self, text):
        """Parse given text and build AST (Abstract Syntax Tree)

        Once parsed, can be 'executed'
        """
        if not isinstance(text, str):
            raise EInvalidType("Given `text` must be a <str>")
        elif self.__grammarRules.count()==0:
            raise EInvalidStatus("There's no rules defined for given Grammar rules!")

        checkResult=self.__grammarRules.check()
        if len(checkResult)>0:
            # grammar is not correct?
            print(checkResult)
            raise EInvalidStatus("Current grammar is not complete, some referenced grammar rule are missing")

        if self.__grammarRules.idFirst() is None:
            raise EInvalidStatus(f"Current grammar is not valid: first grammar rule hasn't been defined")


        textHash=hashlib.sha1()
        textHash.update(text.encode())
        hashText=textHash.hexdigest()

        if self.__hashText is None or hashText!=self.__hashText:
            # if given text hasn't been already parsed
            # - tokenize
            # - parse
            self.__hashText=hashText
            self.__tokens=self.__tokenizer.tokenize(text)
            self.__parse()

        return self.__ast


    def errors(self):
        """Return error found by parser"""
        return self.__errors


class ParserError:
    """Define an error"""

    def __init__(self, errorMsg, token, grammarRule=None, ast=None):
        self.__errorMsg=errorMsg
        self.__errorToken=token
        self.__errorGrammarRule=grammarRule
        self.__errorAst=ast

    def __repr__(self):
        return f"<ParserError(Message='{self.__errorMsg}',\nToken={self.__errorToken},\nGrammarRule={self.__errorGrammarRule},\nAST={self.__errorAst})>"

    def errorMessage(self):
        """Return error message"""
        return self.__errorMsg

    def errorToken(self):
        """Return token on which error occured"""
        return self.__errorToken

    def errorGrammarRule(self):
        """Return grammar rule on which error occured"""
        return self.__errorGrammarRule

    def errorAst(self):
        """Return ast item on which error occured"""
        return self.__errorAst


class ASTStatus(Enum):
    NOMATCH=    0
    MATCH=      1
    INVALID=    2
    END=        3



class ASTSpecialItemType(Enum):
    ROOT='<Root>'
    BINARY_OPERATOR='<BinaryOperator>'
    UNARY_OPERATOR='<UnaryOperator>'



class ASTItem:
    """AST item represent a node of Abstract Syntax Tree

    AST is defined by an ID:
    - as a string=a reference to a GrammarRule
    - as a ASTSpecialItemType (root or a binary operator)

    AST item status define if current node/sub-nodes are valid or not

    And AST item can have zero to N nodes
    """
    # optionAst=True, optionOperatorPrecedence=False
    def __init__(self, id, grammarRule=None):
        """Initialise AST item

        Given `id` allows to determinate which type of of AST item we're currently
        prcessing; it's not a unique Id

        If given, `grammarRule` must be a <GrammarRule>
        """
        if not(grammarRule is None or isinstance(grammarRule, GrammarRule)):
            raise EInvalidType('Given `grammarRule` must be None or <GrammarRule>')

        self.__id=id
        self.__nodes=[]
        self.__tokens=[]
        self.__status=ASTStatus.NOMATCH
        self.__grammarRule=grammarRule

        self.__checkOperatorPrecedenceEnabled=True

    def __repr__(self):
        returned=[f'<ASTItem({self.__id}, {len(self.__nodes)}, {self.__status}, {self.position()})>']
        if len(self.__nodes)>0:
            for node in self.__nodes:
                if isinstance(node, Token):
                    returned.append(f'. . <Token({node.type()}, `{node.text()}`)>')
                else:
                    returned.append('. . '+str(node).replace('\n', '\n. . '))
        return "\n".join(returned)

    def id(self):
        """Return identifier of AST item"""
        return self.__id

    def setId(self, id):
        """Set identifier of AST item"""
        self.__id=id

    def add(self, item, addToNodes=True):
        """Add an item to AST item

        Given `item` can be:
        - a token
        - an AST Item
        - a GrammarRule or GRObject

        If option `addToNodes` is set to True, item is added as a sub node
        Otherwise, if `item` is a token, only token is added in token list
        """
        if addToNodes:
            # need to add node in Node list
            # if True, means:
            # - it's a GrammarRule for which we explicitely need to get it in sub-nodes
            # - it's another GRObject
            # - it's an AST item
            if isinstance(item, ASTItem):
                # need to check if grammar rule is concerned by operator and need to be converted to a AST
                item.checkOperatorPrecedence()

                # we got an AST Item (ie, some already parsed tokens converted to a valid abstract syntax tree)
                if (isinstance(item.id(), str) or isinstance(item.id(), ASTSpecialItemType)) and item.optionAst():
                    # AST item is refering to a grammar rule or a specital item type (probaly a binary operator)
                    # and it's designed optionAst() to be stored as a node
                    self.__nodes.append(item)
                else:
                    # AST item is refering to a grammar rule or a specital item type (probaly a binary operator)
                    # and it's NOT designed optionAst() to be stored as a node
                    #
                    # or
                    #
                    # AST probably referring to a GRObject (GROne, GROptional, ...)
                    #
                    #
                    # To simplify AST sub-nodes, we don't add item directly as a node,
                    # but all nodes of item are directly added to current AST nodes
                    for subItem in item.nodes():
                        self.add(subItem)

                    if item.countNodes()==0:
                        # no nodes???
                        # means we only have tokens, add them as nodes
                        for subItem in item.tokens():
                            self.add(subItem, False)
            else:
                # might be a grammar rule or GRObject
                self.__nodes.append(item)

        if isinstance(item, Token):
            # in all case, a token is added to token list
            self.__tokens.append(item)

    def nodes(self):
        """Return nodes list"""
        return self.__nodes

    def node(self, index, default=None):
        """Return node for given `index`

        If `index` is invalid, return `default` value
        """
        try:
            return self.__nodes[index]
        except Exception as e:
            return default

    def tokens(self):
        """Return tokens list"""
        return self.__tokens

    def countNodes(self):
        """Return number of nodes in list"""
        return len(self.__nodes)

    def countTokens(self):
        """Return number of tokens in list"""
        return len(self.__tokens)

    def status(self):
        """Return current status AST (MATCH, NOMATCH, INVALID)"""
        return self.__status

    def setStatus(self, value):
        """Return current status for AST (MATCH, NOMATCH, INVALID)"""
        if isinstance(value, ASTStatus):
            self.__status=value
        else:
            raise EInvalidType("Given `value` must be an <ASTStatus>")
        return self

    def grammarRule(self):
        """Return GrammarRule for AST item, if current AST refers to a GrammarRule
        (otherwise return None)
        """
        return self.__grammarRule

    def optionAst(self):
        """Return if current AST item can be added as a Node to another AST item

        If AST item refers to a GrammarRule, use GrammarRule option value
        Otherwise return True
        """
        if not isinstance(self.__grammarRule, GrammarRule):
            return True
        else:
            return self.__grammarRule.optionAst()

    def optionOperatorPrecedence(self):
        """Return if current AST item must manage operator precedence

        If AST item refers to a GrammarRule, use GrammarRule option value
        Otherwise return False
        """
        if not isinstance(self.__grammarRule, GrammarRule):
            return False
        else:
            return self.__grammarRule.optionOperatorPrecedence()

    def checkOperatorPrecedence(self):
        """Check if curent AST item is concerned by opertor precedence rules

        If yes, do a conversion of current AST item to a BinaryOperator AST
        """
        def lookahead(nodes):
            left=nodes.value()

            if isinstance(left, Token) and self.__grammarRule.grammarRules().operatorType(left)==1:
                # an unary operator
                left=None
            else:
                returned=left
                # current token is not an operator
                # go to next token to be on operator
                nodes.next()

            while nodes.value():
                node=nodes.value()

                # get priority of current operator
                priority=self.__grammarRule.grammarRules().operatorPrecedence(node)

                # need to analyse lookahead, to get next operator and compare priority

                for laIndex in range(1,3):
                    nodeLA=nodes.relativeValue(laIndex)
                    if nodeLA:
                        right=None
                        if self.__grammarRule.grammarRules().operatorType(nodeLA)>0:
                            # there's a node in list, get priority
                            priorityLA=self.__grammarRule.grammarRules().operatorPrecedence(nodeLA)

                            # get default right value for operator
                            right=nodes.next()

                            # if priority==priorityLA:
                            #       same priority, then we don't care
                            #       example:
                            #         a + b + c
                            #           ^   ^
                            #           |   +-- priorityLA=10     [node.relativeValue(2)]
                            #           +------ priority=10       [node]
                            #
                            # else if priority>priorityLA:
                            #       current operator priority is higher
                            #       example:
                            #         a * b + c
                            #           ^   ^
                            #           |   +-- priorityLA=10     [node.relativeValue(2)]
                            #           +------ priority=20       [node]
                            #
                            #       in this case need to build
                            #              +
                            #           *     c
                            #          a b
                            #

                            if priority<=priorityLA:
                                # current operator priority is lower
                                # example:
                                #   a + b * c
                                #     ^   ^
                                #     |   +-- priorityLA=20     [node.relativeValue(2)]
                                #     +------ priority=10       [node]
                                #
                                # in this case need to build
                                #        +
                                #     a    *
                                #         b c
                                #
                                # get next look head as right value
                                right=lookahead(nodes)

                            break
                    else:
                        # there's no token anymore to analyse; set last token as right value
                        #
                        right=nodes.next()
                        break


                # create AST for current operator
                if left is None:
                    operator=ASTItem(ASTSpecialItemType.UNARY_OPERATOR)
                    operator.add(node)
                    operator.add(right)
                else:
                    operator=ASTItem(ASTSpecialItemType.BINARY_OPERATOR)
                    operator.add(node)
                    operator.add(left)
                    operator.add(right)
                operator.setStatus(ASTStatus.MATCH)

                # left value for next operator will be current operator created
                left=operator

                # and return last operator from current lookahead (if exit loop)
                returned=operator

                # continue with next token
                # if no more token, loop will be exited and last operator returned as hed of AST
                nodes.next()

            return returned

        if self.__checkOperatorPrecedenceEnabled and self.optionOperatorPrecedence():
            # need to reorganise items
            #
            nodes=EList(self.__nodes)
            nodes.first()
            self.__nodes=[lookahead(nodes)]

            # AST item has been processed, ensure that it won't be processed anymore
            self.__checkOperatorPrecedenceEnabled=False

    def position(self):
        """Return position column/rows of starting/ending tokens for current AST"""
        if len(self.__tokens)>0:
            return {'from': {'column': self.__tokens[0].column(),
                             'row': self.__tokens[0].row()
                        },
                    'to': {'column': self.__tokens[-1].column() + self.__tokens[-1].length(),
                           'row': self.__tokens[0].row()
                        }
                }
        else:
            return {'from': {'column': 0,
                             'row': 0
                        },
                    'to': {'column': 0,
                           'row': 0
                        }
                }



class GROperatorPrecedence:
    """Define a grammar rule for operator precedence"""

    def __init__(self, priority, tokenType, binary, *values):
        """Initialise rule according

        Given `priority` determine which operator has precedence over another operator
        The higher value gives a higer priority

        Given `tokenType` is a TokenType, and define which token is considered to works as operator precedence

        Given `binary` is a boolean which define if operator is unary (False) or binary (True) operator

        Given `*values` is optional list of values for token:
        - if not provided, all values for given `token` are used to define rule
        - if provided, only values for given `token` are used to define rule
        """
        if not isinstance(priority, int):
            raise EInvalidType("Given `priority` must be <int>")

        if not isinstance(tokenType, TokenType):
            raise EInvalidType("Given `tokenType` must be <TokenType>")

        if not isinstance(binary, bool):
            raise EInvalidType("Given `binary` must be <boolean>")

        self.__priority=priority
        self.__binary=binary
        self.__tokenType=tokenType
        self.__tokenValues=[]

        for value in values:
            if isinstance(value, str):
                self.__tokenValues.append(value)
            else:
                raise EInvalidType('Optional arguments for GROperatorPrecedence must be <str>')

    def priority(self):
        """Return priority for current token operator precedence definition"""
        return self.__priority

    def tokenType(self):
        """Return token type for current token operator precedence definition"""
        return self.__tokenType

    def tokenValues(self):
        """Return defined token values for current token operator precedence definition"""
        return self.__tokenValues

    def binary(self):
        """Return if operator is a binary operator"""
        return self.__binary



class GrammarRules:
    """A pool of grammar rules"""

    def __init__(self):
        self.__rules={}
        self.__firstRule=None
        self.__operatorPrecedence=[]

    def get(self, id):
        """Return GrammarRule object referenced by given `id` if found, otherwise return None"""
        if id in self.__rules:
            return self.__rules[id]
        return None

    def set(self, id, grammarRule):
        """Set grammar rule for given `id`"""
        if not isinstance(grammarRule, GrammarRule):
            raise EInvalidType("Given `grammarRule` must be <GrammarRule>")
        self.__rules[id]=grammarRule

    def remove(self, id):
        """Remove GrammarRule referenced by given `id` if found, otherwise do nothing"""
        if id in self.__rules:
            self.__rules.pop(id)

    def clear(self):
        """Remove all GrammarRule"""
        self.__rules={}

    def check(self):
        """Check all references to Grammar rules

        Resolve links, and return missing declarations if any
        """
        def recursiveCheck(list):
            returned=[]
            for item in list:
                # check all links for rule
                if isinstance(item, GRRule):
                    if self.get(item.id()) is None:
                        # Grammar rule doesn't exist...
                        # return error
                        returned.append(item.id())
                    else:
                        item.updateGrammarRuleReference(self)
                else:
                    returned+=recursiveCheck(item.grammarList())
            return returned

        missingDeclaration=[]
        for rule in self.__rules:
            # process all rules
            missingDeclaration+=recursiveCheck(self.__rules[rule].grammarList())

        # remove duplicates
        missingDeclaration=list(set(missingDeclaration))

        return missingDeclaration

    def count(self):
        """Return number of rules"""
        return len(self.__rules)

    def idList(self):
        """Return list of rules identifiers"""
        return list(self.__rules.keys())

    def idFirst(self):
        """Return first rule identifiers"""
        return self.__firstRule

    def setIdFirst(self, id):
        """Set first rule identifiers"""
        if self.get(id) is None:
            self.__firstRule=None
            raise EInvalidValue("Rule `id` designed to be first rule doesn't exists")
        self.__firstRule=id

    def setOperatorPrecedence(self, *rules):
        """Define precedence for operators

        Example:
            setOperatorPrecedence(  GROperatorPrecedence(20, BSLanguageDef.ITokenType.OPERATOR, '*', '/', '//', '%'),
                                    GROperatorPrecedence(10, BSLanguageDef.ITokenType.OPERATOR, '+', '-'),
                                    GROperatorPrecedence(5,  BSLanguageDef.ITokenType.OPERATOR, '<', '>', '<=', '>=', '=', '!=')
                                )
        """
        self.__operatorPrecedence=[]

        for rule in rules:
            if not isinstance(rule, GROperatorPrecedence):
                raise EInvalidType("Given `rules` must be <GROperatorPrecedence>")
            self.__operatorPrecedence.append(rule)

    def operatorPrecedence(self, token=None):
        """Return defined operator precedence rules

        If no `token` is provided, return all rules
        If a `token` is provided, must be a <Token>
            If a precedence rule is found for `token`, return priority value, otherwsise return 0 (lower priority)
        """
        if token is None:
            return self.__operatorPrecedence
        elif isinstance(token, Token):
            for rule in self.__operatorPrecedence:
                if rule.tokenType()==token.type():
                    values=rule.tokenValues()
                    if len(values)>0:
                        if token.equal(values):
                            return rule.priority()
                    else:
                        return rule.priority()
            return 0
        else:
            # print(token)
            raise EInvalidType('When provided `token` must be a <Token>')

    def operatorType(self, token):
        """Return:
            - 2 if token is a binary operator
            - 1 if token is an unary operator
            - 0 if token is not an operator
        """
        if isinstance(token, Token):
            for rule in self.__operatorPrecedence:
                if rule.tokenType()==token.type():
                    values=rule.tokenValues()
                    if len(values)>0:
                        if token.equal(values):
                            if rule.binary():
                                return 2
                            return 1
                    else:
                        if rule.binary():
                            return 2
                        return 1
        return 0



class GrammarRule:
    """A grammar rule define sequence of tokens and is referenced by given id

    All rules are stored in a static dictionnary
    """

    OPTION_FIRST =                  0b00000001      # last Grammar Rule defined with this options is designed as the first Grammar Rule
    OPTION_AST   =                  0b00000010      # By default, Grammar Rules are not returned in AST, only nodes are returned
                                                    # When option is defined on Grammar Rule, AST is built with Grammar Rule instead of only nodes
    OPTION_OPERATOR_PRECEDENCE =    0b00000100      # If set, an operator precedence analysis is made for AST build (otherwise not)


    __GRAMMAR_RULES_OBJECT=None

    @staticmethod
    def setGrammarRules(grammarRules=None):
        """If no `grammarRules` is provided (None value) then instanciate a new
        GrammarRules object and return it.
        The returned GrammarRules is used when a new GrammarRule is instanciated

        If a `grammarRules` is provided (a GrammarRules object) then it will be
        used when a new GrammarRule is instanciated
        """
        if grammarRules is None:
            GrammarRule.__GRAMMAR_RULES_OBJECT=GrammarRules()
            return GrammarRule.__GRAMMAR_RULES_OBJECT
        elif isinstance(grammarRules, GrammarRules):
            GrammarRule.__GRAMMAR_RULES_OBJECT=grammarRules
            return GrammarRule.__GRAMMAR_RULES_OBJECT
        else:
            raise EInvalidType("When provided, given `grammarRules` must be a <GrammarRules>")

    @staticmethod
    def grammarRules():
        """Return current GrammarRules object used"""
        return GrammarRule.__GRAMMAR_RULES_OBJECT

    def __init__(self, id, *grObjects):
        """Given `id` must but be a string
        All items, if provided, are:
        - String (refers to a GrammarRule identifier)
        - A GrammarRule
        - A GRObject

        If first `grObjects` is boolean value and TRue, the current GrammarRule
        is defined as First GrammarRule
        """
        if GrammarRule.__GRAMMAR_RULES_OBJECT is None:
            # no grammar rule object has been instancied...
            # do a default instanciation
            GrammarRule.setGrammarRules()

        self.__grammarRules=GrammarRule.__GRAMMAR_RULES_OBJECT

        if not isinstance(id, str):
            raise EInvalidType('Given `id` must be a <str>')
        elif not self.__grammarRules.get(id) is None:
            raise EInvalidValue(f'A GrammarRule already exists for given `id`: {id}')

        if len(grObjects)==0:
            raise EInvalidValue('At least one argument must be provided to GrammarRule')

        self.__id=id
        self._grObjects=[]

        isFirstId=False
        self.__optionAst=False
        self.__optionOperatorPrecedence=False

        for index, grObject in enumerate(grObjects):
            if index==0 and isinstance(grObject, int):
                # first parameter as integer=options
                if grObject&GrammarRule.OPTION_FIRST==GrammarRule.OPTION_FIRST:
                    isFirstId=True
                if grObject&GrammarRule.OPTION_AST==GrammarRule.OPTION_AST:
                    self.__optionAst=True
                if grObject&GrammarRule.OPTION_OPERATOR_PRECEDENCE==GrammarRule.OPTION_OPERATOR_PRECEDENCE:
                    self.__optionOperatorPrecedence=True
            elif isinstance(grObject, str) or isinstance(grObject, GrammarRule):
                self._grObjects.append(GRRule(grObject))
            elif isinstance(grObject, GRObject):
                self._grObjects.append(grObject)
            else:
                raise EInvalidType('Arguments for GrammarRule must be <str>, <GRObject>, <GrammarRule>')

        self.__grammarRules.set(id, self)

        if isFirstId:
            self.__grammarRules.setIdFirst(id)

    def id(self):
        """Return identifier of grammr rule"""
        return self.__id

    def grammarRules(self):
        """Return grammar rules owner of current grammar rule"""
        return self.__grammarRules

    def grammarList(self):
        """Return list of GRObjects that define grammar for current rule"""
        return self._grObjects

    def optionAst(self):
        """Return if grammar rule is returned in AST or not

        When False, sub nodes are returned in AST
        """
        return self.__optionAst

    def optionOperatorPrecedence(self):
        """Return if grammar rule use operator precedence in AST"""
        return self.__optionOperatorPrecedence




class GRObject:
    """Base class for GrammarRule objects"""


    def __init__(self):
        self._grObjects=[]

    def grammarList(self):
        """Return list of GRObjects that define grammar for current rule"""
        return self._grObjects

    def check(self, tokens, ignoredTokens=[]):
        """Virtual method, must be overrided"""
        raise EInvalidStatus("Method can't be called from GRObject and must be overrided")



class GROne(GRObject):
    """One object from given list"""

    def __init__(self, *grObjects):
        super(GROne, self).__init__()

        if len(grObjects)==0:
            raise EInvalidValue('At least one argument must be provided to GROne')

        for grObject in grObjects:
            if isinstance(grObject, str) or isinstance(grObject, GrammarRule):
                self._grObjects.append(GRRule(grObject))
            elif isinstance(grObject, GRObject):
                self._grObjects.append(grObject)
            else:
                raise EInvalidType(f'Arguments for GROne must be <str>, <GRObject>, <GrammarRule>: {grObject}')

    def __repr__(self):
        return f"<GROne({len(self._grObjects)}, {self._grObjects})>"

    def check(self, tokens, ignoredTokens=[]):
        """Check if One and only one grammar rule match current token"""
        # loop over GRObjects list
        # if one is matching expected value, exit and return True
        # if none is matching expected value, exit and return False
        ast=ASTItem(self.__class__)

        if tokens.eol():
            return ast.setStatus(ASTStatus.END)

        index=tokens.index()

        for grObject in self._grObjects:
            #print('Check GROne', grObject)
            checked=grObject.check(tokens, ignoredTokens)
            if checked.status()==ASTStatus.END:
                ast.add(checked)
                return ast.setStatus(ASTStatus.END)
            elif checked.status()==ASTStatus.MATCH:
                # match and valid grammar
                ast.add(checked)
                return ast.setStatus(ASTStatus.MATCH)
            else:
                tokens.setIndex(index)

        # here, nothing valid has been found, then invalid
        return ast.setStatus(ASTStatus.NOMATCH)



class GROptional(GRObject):
    """Zero or one object from given list"""

    def __init__(self, *grObjects):
        super(GROptional, self).__init__()

        if len(grObjects)==0:
            raise EInvalidValue('At least one argument must be provided to GROptional')

        for grObject in grObjects:
            if isinstance(grObject, str) or isinstance(grObject, GrammarRule):
                self._grObjects.append(GRRule(grObject))
            elif isinstance(grObject, GRObject):
                self._grObjects.append(grObject)
            else:
                raise EInvalidType(f'Arguments for GROptional must be <str>, <GRObject>, <GrammarRule>: {grObject}')

    def __repr__(self):
        return f"<GROptional({len(self._grObjects)}, {self._grObjects})>"

    def check(self, tokens, ignoredTokens=[]):
        """Check if Zero or One grammar rule match current token"""
        # loop over GRObjects list
        # if one is matching expected value, exit and return True
        # if none is matching expected value, exit return True
        # if more than one is matching expected value, exit and return True
        ast=ASTItem(self.__class__)

        if tokens.eol():
            return ast.setStatus(ASTStatus.MATCH)

        index=tokens.index()

        matchCount=0
        for grObject in self._grObjects:
            #print('Check GROptional', grObject)
            checked=grObject.check(tokens, ignoredTokens)

            if checked.status()==ASTStatus.END:
                ast.add(checked)
                return ast.setStatus(ASTStatus.MATCH)
            elif checked.status()==ASTStatus.MATCH:
                # match and valid grammar
                # found
                ast.add(checked)
                return ast.setStatus(ASTStatus.MATCH)

        # here, nothing or one valid has been found, then valid
        tokens.setIndex(index)
        return ast.setStatus(ASTStatus.MATCH)



class GRNoneOrMore(GRObject):
    """Zero or N objects from given list"""

    def __init__(self, *grObjects):
        super(GRNoneOrMore, self).__init__()

        if len(grObjects)==0:
            raise EInvalidValue('At least one argument must be provided to GRNoneOrMore')

        for grObject in grObjects:
            if isinstance(grObject, str) or isinstance(grObject, GrammarRule):
                self._grObjects.append(GRRule(grObject))
            elif isinstance(grObject, GRObject):
                self._grObjects.append(grObject)
            else:
                raise EInvalidType(f'Arguments for GRNoneOrMore must be <str>, <GRObject>, <GrammarRule>: {grObject}')

    def __repr__(self):
        return f"<GRNoneOrMore({len(self._grObjects)}, {self._grObjects})>"

    def check(self, tokens, ignoredTokens=[]):
        """Check if Zero or More grammar rules match current token"""
        # loop over GRObjects list
        # if one is matching expected value, exit and return True
        # if none is matching expected value, exit return True
        # if more than one is matching expected value, exit and return True
        ast=ASTItem(self.__class__)

        if tokens.eol():
            return ast.setStatus(ASTStatus.MATCH)

        totalMatchCount=0
        while True:
            index=tokens.index()
            matchCount=0
            for grObject in self._grObjects:
                #print('Check GRNoneOrMore', grObject)
                checked=grObject.check(tokens, ignoredTokens)

                if checked.status()==ASTStatus.END:
                    ast.add(checked)
                    return ast.setStatus(ASTStatus.MATCH)
                elif checked.status()==ASTStatus.MATCH:
                    matchCount+=1
                    ast.add(checked)
                    break

            if matchCount>=1:
                # more => continue loop
                totalMatchCount+=matchCount
            else:
                # no more => exit loop
                tokens.setIndex(index)
                return ast.setStatus(ASTStatus.MATCH)



class GROneOrMore(GRObject):
    """Zero or N objects from given list"""

    def __init__(self, *grObjects):
        super(GROneOrMore, self).__init__()

        if len(grObjects)==0:
            raise EInvalidValue('At least one argument must be provided to GROneOrMore')

        for grObject in grObjects:
            if isinstance(grObject, str) or isinstance(grObject, GrammarRule):
                self._grObjects.append(GRRule(grObject))
            elif isinstance(grObject, GRObject):
                self._grObjects.append(grObject)
            else:
                raise EInvalidType(f'Arguments for GROneOrMore must be <str>, <GRObject>, <GrammarRule>: {grObject}')

    def __repr__(self):
        return f"<GROneOrMore({len(self._grObjects)}, {self._grObjects})>"

    def check(self, tokens, ignoredTokens=[]):
        """Check if One or More grammar rules match current token"""
        # loop over GRObjects list
        # if one is matching expected value, exit and return True
        # if none is matching expected value, exit return True
        # if more than one is matching expected value, exit and return True
        ast=ASTItem(self.__class__)

        if tokens.eol():
            return ast.setStatus(ASTStatus.END)

        totalMatchCount=0
        while True:
            index=tokens.index()
            matchCount=0
            for grObject in self._grObjects:
                #print('Check GROneOrMore', grObject)
                checked=grObject.check(tokens, ignoredTokens)

                if checked.status()==ASTStatus.END:
                    ast.add(checked)
                    if totalMatchCount>=1:
                        return ast.setStatus(ASTStatus.MATCH)
                    else:
                        return ast.setStatus(ASTStatus.END)
                elif checked.status()==ASTStatus.MATCH:
                    #print('Check GROneOrMore==>match!', checked)
                    matchCount+=1
                    ast.add(checked)
                    break

            if matchCount>=1:
                # more => continue loop
                totalMatchCount+=matchCount
            elif totalMatchCount>=1:
                # no more but at least one found => exit loop
                tokens.setIndex(index)
                return ast.setStatus(ASTStatus.MATCH)
            else:
                # no more and nothing found => exit loop
                tokens.setIndex(index)
                return ast.setStatus(ASTStatus.NOMATCH)



class GRToken(GRObject):
    """One token"""

    def __init__(self, tokenType, *possibleValues):
        super(GRToken, self).__init__()

        if not isinstance(tokenType, TokenType):
            raise EInvalidType(f'Given `tokenType` must be <TokenType>: {tokenType}')

        self.__tokenType=tokenType
        self.__possibleValues=[]
        self.__optionAst=True
        for possibleValue in possibleValues:
            if isinstance(possibleValue, str):
                self.__possibleValues.append(possibleValue)
            elif isinstance(possibleValue, bool):
                # consider it as option...
                self.__optionAst=possibleValue
            else:
                raise EInvalidType('Possibles values must be <str>')

        self.__checkPossibleValue=len(self.__possibleValues)>0

    def __repr__(self):
        return f"<GRToken({self.__tokenType}, {self.__possibleValues})>"

    def check(self, tokens, ignoredTokens=[]):
        """Check if current token match expected token"""
        ast=ASTItem(self.__class__)

        if tokens.eol():
            return ast.setStatus(ASTStatus.END)

        token=tokens.value()

        while (not token is None) and (token.type() in ignoredTokens):
            # if there's token to ignore (like spaces, comments, ...)
            # continue to next token
            token=tokens.next()

        if token is None:
            return ast.setStatus(ASTStatus.END)

        if token.type()==self.__tokenType:
            #print('Check GRToken', self.__tokenType, self.__possibleValues, token)
            # current token is expected token type
            if self.__checkPossibleValue:
                # need to check if token value match one of expected value
                if not token.equal(self.__possibleValues):
                    # doesn't match: that's an error
                    return ast.setStatus(ASTStatus.NOMATCH)

            ast.add(token, self.__optionAst)

            # move to next token, to continue parsing
            token=tokens.next()

            while (not token is None) and (token.type() in ignoredTokens):
                # if there's token to ignore (like spaces, comments, ...)
                # continue to next token
                token=tokens.next()

            #print('GRToken: Next ', token)

            return ast.setStatus(ASTStatus.MATCH)
        return ast.setStatus(ASTStatus.NOMATCH)

    def optionAst(self):
        """Return if token have to be returned in AST"""
        return self.__optionAst



class GRRule(GRObject):
    """One GrammarRule"""

    def __init__(self, id):
        super(GRRule, self).__init__()

        if not (isinstance(id, str) or isinstance(id, GrammarRule)):
            raise EInvalidType(f'Given `id` must be <str> or <GrammarRule>: {id}')

        self.__grammarRule=id

    def __repr__(self):
        return f"<GRRule({self.__grammarRule.id()})>"

    def id(self):
        """Return identifier for GrammarRule"""
        if isinstance(self.__grammarRule, str):
            return self.__grammarRule
        else:
            # is a GrammarRule
            return self.__grammarRule.id()

    def updateGrammarRuleReference(self, grammarRules):
        """Update grammar rule object, using given `grammarRules`

        If current __grammarRule is a string reference, replace it with GrammarRule object
        """
        if isinstance(self.__grammarRule, str) and isinstance(grammarRules, GrammarRules):
            object=grammarRules.get(self.__grammarRule)
            if not object is None:
                self.__grammarRule=object

    def check(self, tokens, ignoredTokens=[]):
        """Check if One or More grammar rules match current token"""
        # loop over GRObjects list
        # if one is matching expected value, exit and return True
        # if none is matching expected value, exit return True
        # if more than one is matching expected value, exit and return True
        #print('Check GRRule', self.id())

        ast=ASTItem(self.id(), self.__grammarRule)

        if tokens.eol():
            return ast.setStatus(ASTStatus.END)

        for grObject in self.__grammarRule.grammarList():
            checked=grObject.check(tokens, ignoredTokens)

            # test

            if checked.status()==ASTStatus.END:
                #print('Check GRRule: END', self.id(), checked)
                ast.add(checked)
                return ast.setStatus(ASTStatus.END)
            elif checked.status()==ASTStatus.NOMATCH:
                return ast.setStatus(ASTStatus.NOMATCH)
            ast.add(checked)

        #print('Check GRRule: MATCH', self.id())
        return ast.setStatus(ASTStatus.MATCH)
