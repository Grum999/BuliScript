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

import math

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

try:
    from PyQt5.QtSvg import *
    QTSVG_AVAILABLE = True
except:
    # vector render mode won't be an option...
    QTSVG_AVAILABLE = False


from buliscript.pktk.modules.imgutils import checkerBoardBrush


from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )

class BSWRendererView(QGraphicsView):
    """A graphic view dedicated to render scene"""
    zoomChanged=Signal(float)

    def __init__(self, parent=None):
        super(BSWRendererView, self).__init__(parent)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHint(QPainter.TextAntialiasing)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self.__currentZoomFactor = 1.0
        self.__zoomStep=0.25

    def drawForeground(self, painter, rect):
        """Draw foreground on view will just draw rulers

        Rulers are not drawn directly on scene because we need to keep a constant
        size whatever the curent scale is

        """
        super(BSWRendererView, self).drawForeground(painter, rect)

        # retrieve ruler properties from scene
        rulerProperties=self.scene().rulerProperties()

        if rulerProperties['visible'] and len(rulerProperties['hPos'])>0:
            # there's something to render

            # -- convert "view position" to "scene position"
            # origin 0,0 (from top/left position of rulers)
            ptZero=self.mapToScene(QPoint(0,0))
            # Horizontal ruler bottom/right position
            ptH=self.mapToScene(QPoint(self.width(), rulerProperties['ruler_size']))
            # Vertical ruler bottom/right position
            ptV=self.mapToScene(QPoint(rulerProperties['ruler_size'], self.height()))
            # top/left corner
            ptC=self.mapToScene(QPoint(rulerProperties['ruler_size']+1, rulerProperties['ruler_size']+1))

            # calculate size for secondary ticks
            secondarySize=rulerProperties['ruler_size']-(rulerProperties['ruler_size']-rulerProperties['ruler_font_height'])/2

            # generate ticks lines
            lines=[]
            # -- horizontal ruler ticks
            ptTo=self.mapToScene(QPoint(0, rulerProperties['ruler_size']))
            ptFromMain=self.mapToScene(QPoint(0, rulerProperties['ruler_font_height']))
            ptFromSecondary=self.mapToScene(QPoint(0, secondarySize))
            for position in rulerProperties['hStrokes']:
                if position[0]:
                    # main line
                    ptFrom=ptFromMain
                else:
                    # secondary line
                    ptFrom=ptFromSecondary
                ptFrom.setX(position[1])
                ptTo.setX(position[1])
                lines.append(QLineF(ptFrom, ptTo))

            # -- vertical ruler ticks
            ptTo=self.mapToScene(QPoint(rulerProperties['ruler_size'], 0))
            ptFromMain=self.mapToScene(QPoint(rulerProperties['ruler_font_height'], 0))
            ptFromSecondary=self.mapToScene(QPoint(secondarySize, 0))
            for position in rulerProperties['vStrokes']:
                if position[0]:
                    # main line
                    ptFrom=ptFromMain
                else:
                    # secondary line
                    ptFrom=ptFromSecondary
                ptFrom.setY(position[1])
                ptTo.setY(position[1])
                lines.append(QLineF(ptFrom, ptTo))

            # draw rulers BG
            painter.fillRect(QRectF(ptZero, ptH), rulerProperties['brush'])
            painter.fillRect(QRectF(ptZero, ptV), rulerProperties['brush'])

            # draw ruler ticks
            painter.setPen(rulerProperties['pen'])
            painter.drawLines(*lines)


            # -- define font, scaled to current zoom
            font=QFont(rulerProperties['font'])
            font.setPointSizeF(font.pointSizeF()/self.__currentZoomFactor)
            painter.setFont(font)

            # -- calculate width/height of font on scene
            ptf=self.mapToScene(QPoint(rulerProperties['ruler_font_height'], rulerProperties['ruler_font_height']))

            # calculate/render numbers on horizontal ruler
            # -- bounding box
            pt1=self.mapToScene(QPoint(0, 1))
            pt2=self.mapToScene(QPoint(0, rulerProperties['ruler_font_height']-1))

            # draw rulers numbers
            nbChars=max(len(str(rulerProperties['hPos'][0])), len(str(rulerProperties['hPos'][-1])))-1
            textWidth=nbChars*rulerProperties['ruler_font_width']/self.__currentZoomFactor
            textWidthH=textWidth/2

            if len(rulerProperties['hPos'])>1:
                # -- delta is value between 2 numbers
                delta=rulerProperties['hPos'][1]-rulerProperties['hPos'][0]
                # -- we need to ensure, when scrolling, that number 0 is always visible
                #    and all numbers around are always the same
                modulo=math.ceil(textWidth/delta)

                # checkwidth define if we need to check width or not to display numbers
                checkWidth=textWidth>(delta/self.__currentZoomFactor)

                sign=1
                if rulerProperties['origin'][0]==1:
                    # H right origin; left direction is positive
                    sign=-1

                for position in rulerProperties['hPos']:
                    if checkWidth and (position/delta)%modulo!=0:
                        continue
                    pt1.setX(position-textWidthH)
                    pt2.setX(position+textWidthH)
                    painter.drawText(QRectF(pt1, pt2), Qt.AlignCenter, str(sign*position))


                # calculate/render numbers on vertical ruler
                # -- bounding box
                pt1=self.mapToScene(QPoint(1, 0))
                pt2=self.mapToScene(QPoint(rulerProperties['ruler_font_height']-1, 0))

                # draw rulers numbers
                nbChars=max(len(str(rulerProperties['hPos'][0])), len(str(rulerProperties['hPos'][-1])))-1
                textWidth=nbChars*rulerProperties['ruler_font_width']/self.__currentZoomFactor
                textWidthH=textWidth/2

            if len(rulerProperties['vPos'])>1:
                # -- delta is value between 2 numbers
                delta=rulerProperties['vPos'][1]-rulerProperties['vPos'][0]
                # -- we need to ensure, when scrolling, that number 0 is always visible
                #    and all numbers around are always the same
                modulo=math.ceil(textWidth/delta)

                # checkwidth define if we need to check width or not to display numbers
                checkWidth=textWidth>(delta/self.__currentZoomFactor)

                # inverted, because QT default positive direction is top to bottom and for us, it bottom to top
                sign=-1
                if rulerProperties['origin'][1]==-1:
                    # V top origin; bottom direction is positive
                    sign=1

                for position in rulerProperties['vPos']:
                    if checkWidth and (position/delta)%modulo!=0:
                        continue
                    # rotated text...
                    # 1) Translate canvas origin to center of boudning rect
                    # 2) Do rotation
                    # 3) Draw text
                    #    . position must be relative new center, (then 0,0 with offset to bound rect)
                    #    . as a 90° rotation has been made, need to switch width&height
                    pt1.setY(position-textWidthH)
                    pt2.setY(position+textWidthH)

                    rect=QRectF(pt1, pt2)

                    painter.save()
                    painter.translate(rect.center().x(), rect.center().y())
                    painter.rotate(-90)
                    painter.drawText(QRectF(-rect.height()/2, -rect.width()/2, rect.height(), rect.width()), Qt.AlignCenter, str(sign*position))
                    painter.restore()

            # erase top/left part
            painter.setOpacity(0.75)
            painter.fillRect(QRectF(ptZero, ptC), rulerProperties['brush'])

    def mousePressEvent(self, event):
        """On left button pressed, start to pan scene"""
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif event.button() == Qt.MidButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            # it seems Qt manage pan only with left button
            # so emulate leftbutton event when middle button is used for panning
            event=QMouseEvent(event.type(), event.localPos(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
        elif event.button() == Qt.RightButton:
            self.centerOn(self.sceneRect().center())

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event:QMouseEvent):
        """On left button released, stop to pan scene"""
        if event.button() in (Qt.LeftButton, Qt.MidButton):
            self.setDragMode(QGraphicsView.NoDrag)

        QGraphicsView.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reset zoom"""
        if event.button() == Qt.LeftButton:
            self.setZoom(1.0)
        QGraphicsView.mouseDoubleClickEvent(self, event)

    def wheelEvent(self, event:QWheelEvent):
        """Manage to zoom with wheel"""

        if event.angleDelta().y() > 0:
            self.setZoom(self.__currentZoomFactor + self.__zoomStep)
        else:
            self.setZoom(self.__currentZoomFactor - self.__zoomStep)

    def zoom(self):
        """Return current zoom property

        returned value is a tuple (ratio, QRectF) or None if there's no image
        """
        return self.__currentZoomFactor

    def setZoom(self, value=0.0):
        """Set current zoom value"""
        if value > 0:
            isIncreased=(value>self.__currentZoomFactor)

            self.__currentZoomFactor = round(value, 2)
            self.scene().setViewZoom(self.__currentZoomFactor)
            self.resetTransform()
            self.scale(self.__currentZoomFactor, self.__currentZoomFactor)

            self.zoomChanged.emit(self.__currentZoomFactor)

            if isIncreased:
                if self.__currentZoomFactor>=0.25:
                    self.__zoomStep=0.25
                elif self.__currentZoomFactor>=0.1:
                    self.__zoomStep=0.05
                else:
                    self.__zoomStep=0.01
            else:
                if self.__currentZoomFactor<=0.1:
                    self.__zoomStep=0.01
                elif self.__currentZoomFactor<=0.25:
                    self.__zoomStep=0.05
                else:
                    self.__zoomStep=0.25


class BSWRendererScene(QGraphicsScene):
    """Render canvas scene: grid, origin, bounds, background, rendered graphics...."""
    propertyChanged=Signal(tuple)       # tuple is defined by (<variable name>, <value)
                                        # => <variable name> is the same than one used in BuliScript language
    sceneUpdated=Signal(dict)           # scene has been updated

    __SECONDARY_FACTOR_OPACITY = 0.5    # define opacity of secondary grid relative to main grid
    __FULFILL_FACTOR_OPACITY = 0.75     # define opacity of position fulfill
    __RULER_FONT_SIZE = 7               # in PT
    __ARROW_SIZE = 4                    # in PX, height of arrows drawn for origin


    POSITION_MODEL_BASIC='BASIC'
    POSITION_MODEL_ARROWHEAD='ARROWHEAD'
    POSITION_MODEL_UPWARD='UPWARD'

    def __init__(self, parent=None):
        super(BSWRendererScene, self).__init__(parent)

        # settings
        self.__gridSizeWidth = 20
        self.__gridSizeMain = 5
        self.__gridBrush=QBrush(QColor("#393939"))
        self.__gridPenMain=QPen(QColor("#FF292929"))
        self.__gridPenSecondary=QPen(QColor("#80292929"))
        self.__gridVisible=True

        self.__gridPenRuler=QPen(QColor("#000000"))
        self.__gridBrushRuler=QBrush(QColor("#ffffff"))
        self.__gridFontRuler=QFont("Monospace")
        self.__gridRulerVisible=True

        self.__originPen=QPen(QColor("#0080FF"))
        self.__originSize = 20
        self.__originPosition = (0, 0)          # centerH, centerV
        self.__originVisible=True
        self.__originPx=0
        self.__originPy=0

        self.__positionPen=QPen(QColor("#8000FF"))
        self.__positionBrush=QBrush(QColor("#808000FF"))
        self.__positionSize = 20
        self.__positionFulfill = False
        self.__positionPosition=QPoint()
        self.__positionAngle=0
        self.__positionVisible=True
        self.__positionAxis=False
        self.__positionModel=BSWRendererScene.POSITION_MODEL_BASIC
        self.__positionAxisLength=0
        self.__positionAxisClip=0

        # document dimension in PX
        self.__documentBounds=None
        self.__backgroundBounds=None
        self.__backgroundImage=None
        self.__backgroundOpacity=1.0
        self.__backgroundCBBrush=checkerBoardBrush()
        self.__backgroundVisible=True

        # rendered image
        self.__renderedImage=None

        # internal data for rendering
        self.__gridStrokesRect=QRect()
        self.__gridStrokesMain=[]
        self.__gridStrokesSecondary=[]
        self.__gridStrokesRulerH=[]
        self.__gridStrokesRulerV=[]
        self.__gridTextRulerH=[]
        self.__gridTextRulerV=[]
        self.__originStrokes=[]
        self.__originStrokesArrows=[]
        self.__positionPoints=[]
        self.__positionStrokes=[]
        self.__viewZoom=1.0

        self.__rulerSize=0
        self.__rulerFontHeight=0
        self.__rulerFontWidth=0

        self.__rendererPositionX=0
        self.__rendererPositionY=0
        self.__rendererRotation=0
        self.__rendererGeometry=BSGeometry()


        self.initialise()
        self.setBackgroundBrush(self.__gridBrush)

    def __propertyChanged(self, name, value):
        """Emit signal for variable name"""
        self.propertyChanged.emit((name, value))

    def __generateGridStrokes(self, rect):
        """Generate grid strokes (avoid to regenerate them on each update)"""
        if rect==self.__gridStrokesRect:
            # viewport is the same, keep current grid definition
            return

        self.__gridStrokesSecondary=[]
        self.__gridStrokesMain=[]
        self.__gridStrokesRulerH=[]
        self.__gridStrokesRulerV=[]

        # bounds
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        firstLeftStroke = left - (left % self.__gridSizeWidth)
        firstTopStroke = top - (top % self.__gridSizeWidth)

        # frequency of main strokes
        mainStroke=max(1, self.__gridSizeWidth * self.__gridSizeMain)

        # generate vertical grid lines
        for positionX in range(firstLeftStroke, right, self.__gridSizeWidth):
            if (positionX % mainStroke != 0):
                self.__gridStrokesSecondary.append(QLine(positionX, top, positionX, bottom))
                self.__gridStrokesRulerH.append((False, positionX))
            else:
                self.__gridStrokesMain.append(QLine(positionX, top, positionX, bottom))
                self.__gridStrokesRulerH.append((True, positionX))

        # generate horizontal grid lines
        for positionY in range(firstTopStroke, bottom, self.__gridSizeWidth):
            if (positionY % mainStroke != 0):
                self.__gridStrokesSecondary.append(QLine(left, positionY, right, positionY))
                self.__gridStrokesRulerV.append((False, positionY))
            else:
                self.__gridStrokesMain.append(QLine(left, positionY, right, positionY))
                self.__gridStrokesRulerV.append((True, positionY))

    def __generateGridRulerNumbers(self, rect):
        """Generate ruler numbers (avoid to regenerate them on each update)"""
        if rect==self.__gridStrokesRect:
            # viewport is the same, keep current grid definition
            return

        self.__gridTextRulerH=[]
        self.__gridTextRulerV=[]

        # bounds
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        firstLeftStroke = left - (left % self.__gridSizeWidth)
        firstTopStroke = top - (top % self.__gridSizeWidth)

        # frequency of main strokes
        mainStroke=max(1, self.__gridSizeWidth * self.__gridSizeMain)

        # generate vertical grid lines
        for positionX in range(firstLeftStroke, right, self.__gridSizeWidth):
            if (positionX % mainStroke == 0):
                self.__gridTextRulerH.append(positionX)

        # generate horizontal grid lines
        for positionY in range(firstTopStroke, bottom, self.__gridSizeWidth):
            if (positionY % mainStroke == 0):
                self.__gridTextRulerV.append(positionY)

    def __generateOriginStrokes(self):
        """Generate grid strokes (avoid to regenerate them on each update)"""
        def arrow(direction, size):
            # append arrow
            points=[]

            if direction=='L':
                size=-size
                points.append(QPoint(size-BSWRendererScene.__ARROW_SIZE, 0))
                points.append(QPoint(size, BSWRendererScene.__ARROW_SIZE))
                points.append(QPoint(size, -BSWRendererScene.__ARROW_SIZE))
            elif direction=='R':
                points.append(QPoint(size+BSWRendererScene.__ARROW_SIZE, 0))
                points.append(QPoint(size, BSWRendererScene.__ARROW_SIZE))
                points.append(QPoint(size, -BSWRendererScene.__ARROW_SIZE))
            elif direction=='T':
                size=-size
                points.append(QPoint(0, size-BSWRendererScene.__ARROW_SIZE))
                points.append(QPoint(BSWRendererScene.__ARROW_SIZE, size))
                points.append(QPoint(-BSWRendererScene.__ARROW_SIZE, size))
            elif direction=='B':
                points.append(QPoint(0, size+BSWRendererScene.__ARROW_SIZE))
                points.append(QPoint(BSWRendererScene.__ARROW_SIZE, size))
                points.append(QPoint(-BSWRendererScene.__ARROW_SIZE, size))

            return QPolygon(points)

        if len(self.__originStrokes)>0:
            # strokes are already generated, does nothing
            return

        self.__originStrokesArrows=[]
        size=self.__originSize/2

        # absissa, ordinate
        self.__originStrokes=[
                QLine(-size, 0, size, 0),
                QLine(0, -size, 0, size)
            ]

        # absissa
        if self.__originPosition[0]==1:
            # right ==> arrow to left direction
            self.__originStrokesArrows.append(arrow('L', size))
        else:
            # center or left ==> arrow to right direction
            self.__originStrokesArrows.append(arrow('R', size))

        # ordinate
        if self.__originPosition[1]==-1:
            # top ==> arrow to bottom direction
            self.__originStrokesArrows.append(arrow('B', size))
        else:
            # center or bottom ==> arrow to top direction
            self.__originStrokesArrows.append(arrow('T', size))

    def __generatePositionPoints(self):
        """Generate position strokes (avoid to regenerate them on each update)"""
        if len(self.__positionPoints)>0:
            # strokes are already generated, does nothing
            return


        # position is a simple triangle
        #
        #         /\
        #        /  \
        #       /____\
        #

        size=self.__positionSize/2
        angle=math.pi/4

        if self.__positionModel==BSWRendererScene.POSITION_MODEL_ARROWHEAD:
            self.__positionPoints=[
                    QPoint(0, size),
                    QPoint(size*math.cos(-angle), size*math.sin(-angle)),
                    QPoint(0, -size*0.25),
                    QPoint(size*math.cos(math.pi+angle), size*math.sin(math.pi+angle))
                ]
        elif self.__positionModel==BSWRendererScene.POSITION_MODEL_UPWARD:
            self.__positionPoints=[
                    QPoint(0, size),
                    QPoint(size*math.cos(-angle), size*math.sin(-angle)),
                    QPoint(size*math.cos(-angle)/2, size*math.sin(-angle)),
                    QPoint(size*math.cos(-angle)/2, -1.25*size),
                    QPoint(size*math.cos(math.pi+angle)/2, -1.25*size),
                    QPoint(size*math.cos(math.pi+angle)/2, size*math.sin(math.pi+angle)),
                    QPoint(size*math.cos(math.pi+angle), size*math.sin(math.pi+angle))
                ]
        else:
            # BASIC
            self.__positionPoints=[
                    QPoint(0, size),
                    QPoint(size*math.cos(-angle), size*math.sin(-angle)),
                    QPoint(size*math.cos(math.pi+angle), size*math.sin(math.pi+angle))
                ]


        # axis
        self.__positionStrokes=[
                QLine(0, self.__positionAxisLength, 0, -self.__positionAxisLength),
                QLine(-self.__positionAxisLength, 0, self.__positionAxisLength, 0)
            ]


    def __calculateSceneSize(self):
        """Calculate scene size/rect according to current document & background bounds"""
        if self.__documentBounds is None:
            size=5000
        else:
            size=max(self.__documentBounds.width(), self.__documentBounds.height())

        if not self.__backgroundBounds is None:
            size=max(size, self.__backgroundBounds.right()+abs(min(0, self.__backgroundBounds.left())))
            size=max(size, self.__backgroundBounds.bottom()+abs(min(0, self.__backgroundBounds.top())))

        rulerSize=0
        if self.__gridRulerVisible:
            rulerSize=self.__rulerSize

        halfSize=size//2
        sceneSize=2*size+rulerSize

        if self.__originPosition[0]==0:
            # H centered
            xValue=-(size+rulerSize)
        elif self.__originPosition[0]==-1:
            # H left ----
            xValue=-(halfSize+rulerSize)
        elif self.__originPosition[0]==1:
            # H right
            xValue=-(size+halfSize+rulerSize)

        if self.__originPosition[1]==0:
            # V centered
            yValue=-(size+rulerSize)
        elif self.__originPosition[1]==-1:
            # V top ----
            yValue=-(halfSize+rulerSize)
        elif self.__originPosition[1]==1:
            # V bottom
            yValue=-(size+halfSize+rulerSize)

        self.setSceneRect(xValue, yValue, sceneSize, sceneSize)

        self.__positionAxisLength=math.ceil(math.sqrt(2*size*size)+10)


    def initialise(self):
        """Initialize render scene"""
        self.__gridPenMain.setWidth(0)
        self.__gridPenSecondary.setWidth(0)
        self.__gridPenRuler.setWidth(0)
        self.__originPen.setWidth(0)
        self.__positionPen.setWidth(0)

        fntMetrics=QFontMetrics(self.__gridFontRuler)

        self.__gridFontRuler.setPointSizeF(BSWRendererScene.__RULER_FONT_SIZE)
        self.__rulerFontHeight=fntMetrics.height()
        self.__rulerFontWidth=fntMetrics.averageCharWidth()
        self.__rulerSize = math.ceil(self.__rulerFontHeight*1.5)


    def drawBackground(self, painter, rect):
        """Draw background (defined layer, checker board)"""
        super(BSWRendererScene, self).drawBackground(painter, rect)

        if self.__documentBounds:
            painter.save()
            painter.translate(self.__originPx, self.__originPy)

            painter.fillRect(self.__documentBounds, self.__backgroundCBBrush)
            if self.__backgroundVisible and self.__backgroundImage:
                painter.save()
                painter.setOpacity(self.__backgroundOpacity)
                painter.drawPixmap(self.__backgroundBounds.left(), self.__backgroundBounds.top(), self.__backgroundImage)
                painter.restore()

            if self.__renderedImage:
                painter.drawPixmap(0, 0, self.__renderedImage)

            painter.restore()

    def drawForeground(self, painter, rect):
        """Draw grid, origin, bounds, ..."""
        super(BSWRendererScene, self).drawForeground(painter, rect)

        # generate ruler numbers
        # ==> ruler is drawn from Graphic View
        self.__generateGridRulerNumbers(rect)

        # generate grid lines
        self.__generateGridStrokes(rect)

        # draw the lines
        # -> if grid is not visible, there's no strokes generated
        if self.__gridVisible and len(self.__gridStrokesSecondary)>0:
            painter.setPen(self.__gridPenSecondary)
            painter.drawLines(*self.__gridStrokesSecondary)

        if self.__gridVisible and len(self.__gridStrokesMain)>0:
            painter.setPen(self.__gridPenMain)
            painter.drawLines(*self.__gridStrokesMain)

        # generate origin
        self.__generateOriginStrokes()

        # draw origin
        if self.__originVisible and len(self.__originStrokes):
            painter.setPen(self.__originPen)
            painter.drawLines(*self.__originStrokes)
            painter.save()
            painter.setBrush(QBrush(self.__originPen.color()))
            for polygon in self.__originStrokesArrows:
                painter.drawPolygon(polygon)
            painter.restore()


        # generate position
        self.__generatePositionPoints()

        # draw position
        if self.__positionVisible and len(self.__positionPoints):
            painter.save()
            painter.setRenderHints(QPainter.Antialiasing, True)
            painter.setPen(self.__positionPen)
            if self.__positionFulfill:
                painter.setBrush(self.__positionBrush)
            else:
                painter.setBrush(QBrush(Qt.NoBrush))

            transform=painter.transform()
            transform.translate(self.__rendererGeometry.hScale()*self.__rendererPositionX, self.__rendererGeometry.vScale()*self.__rendererPositionY)
            transform.rotate(-self.__rendererGeometry.hScale()*-self.__rendererGeometry.vScale()*self.__rendererRotation)
            transform.scale(-self.__rendererGeometry.hScale(), self.__rendererGeometry.vScale())
            painter.setTransform(transform)
            painter.drawPolygon(*self.__positionPoints)

            if self.__positionAxis and len(self.__positionStrokes):
                painter.setRenderHints(QPainter.Antialiasing, True)
                painter.drawLines(*self.__positionStrokes)
            else:
                painter.drawEllipse(QPoint(0, 0), self.__positionSize/10, self.__positionSize/10)
            painter.restore()

        self.__gridStrokesRect=rect


    def setSize(self, width, height):
        """Define size of scene with given `width` and `height`

        Note: they must be greater than painted area
        """
        self.setSceneRect(-width // 2, -height // 2, width, height)

    # --------------------------------------------------------------------------
    # getters
    # --------------------------------------------------------------------------
    def rulerProperties(self):
        """Return all needed properties to draw rulers"""
        return {
                'ruler_size': self.__rulerSize,
                'ruler_font_height': self.__rulerFontHeight,
                'ruler_font_width': self.__rulerFontWidth,
                'brush': self.__gridBrushRuler,
                'pen': self.__gridPenRuler,
                'font': self.__gridFontRuler,
                'hStrokes': self.__gridStrokesRulerH,
                'vStrokes': self.__gridStrokesRulerV,
                'hPos': self.__gridTextRulerH,
                'vPos': self.__gridTextRulerV,
                'visible': self.__gridRulerVisible,
                'origin': self.__originPosition
            }


    def gridVisible(self):
        """Return if grid is visible"""
        return self.__gridVisible

    def gridRulerVisible(self):
        """Return if grid is visible"""
        return self.__gridRulerVisible

    def gridSize(self):
        """Return a tuple (grid size width, main grid frequency) in PX"""
        return (self.__gridSizeWidth, self.__gridSizeMain)

    def gridBrush(self):
        """Return brush used to render background grid"""
        return self.__gridBrush

    def gridPenMain(self):
        """Return pen used to render main grid"""
        return self.__gridPenMain

    def gridPenSecondary(self):
        """Return pen used to render secondary grid"""
        return self.__gridPenSecondary

    def gridFontRuler(self):
        """Return font used to render grid ruler"""
        return self.__gridFontRuler

    def gridBrushRuler(self):
        """Return brush used to render grid ruler"""
        return self.__gridBrushRuler

    def gridPenRuler(self):
        """Return pen used used to render grid ruler"""
        return self.__gridPenRuler


    def originVisible(self):
        """Return if origin is visible"""
        return self.__originVisible

    def originPen(self):
        """Return pen used to render origin"""
        return self.__originPen

    def originSize(self):
        """Return size in PX used to render origin"""
        return self.__originSize

    def originPosition(self):
        """Return settings used to define position for origin

        Return value is a tuple (absissa, ordinate)

        Values for absissa:
            -1: left
             0: center horizontaly
             1: right

        Values for ordinate:
            -1: top
             0: center vertically
             1: bottom
        """
        return self.__originPosition


    def positionVisible(self):
        """Return if position is visible"""
        return self.__positionVisible

    def positionPen(self):
        """Return pen used to render position"""
        return self.__positionPen

    def positionBrush(self):
        """Return brush used to render position"""
        return self.__positionBrush

    def positionSize(self):
        """Return size in PX used to render position"""
        return self.__positionSize

    def positionFulfill(self):
        """Return settings used to define if position if fulfilled or not"""
        return self.__positionFulfill

    def positionAxis(self):
        """Return settings used to define if position axis is visible or not"""
        return self.__positionAxis

    def positionModel(self):
        """Return settings used to define which position model is used"""
        return self.__positionModel


    def documentBounds(self):
        """Return current document bounds"""
        return self.__documentBounds


    def backgroundVisible(self):
        """Return if background is visible"""
        return self.__backgroundVisible

    def backgroundBounds(self):
        """Return current background image bounds"""
        return self.__backgroundBounds

    def backgroundImage(self):
        """Return current background image"""
        return self.__backgroundImage

    def backgroundOpacity(self):
        """Return current background opacity"""
        return self.__backgroundOpacity

    # --------------------------------------------------------------------------
    # setters
    # --------------------------------------------------------------------------
    def setViewZoom(self, value):
        self.__viewZoom=value
        self.__backgroundCBBrush=checkerBoardBrush(math.ceil(32/self.__viewZoom), strictSize=False)

    def setGridVisible(self, value):
        """Set if grid is visible"""
        if isinstance(value, bool) and value!=self.__gridVisible:
            self.__gridVisible=value
            self.__propertyChanged(':canvas.grid.visibility', self.__gridVisible)
            self.update()

    def setGridRulerVisible(self, value):
        """Set if grid is visible"""
        if isinstance(value, bool) and value!=self.__gridRulerVisible:
            self.__gridRulerVisible=value
            self.__propertyChanged(':canvas.rulers.visibility', self.__gridRulerVisible)
            self.__calculateSceneSize() # ruler impact scene size because they have to be excluded from scene
            self.update()

    def setGridSize(self, width, main=0):
        """Set grid size, given `width` is in PX
        Given `main` is an integer that define to draw a main line everything `main` line
        """
        if width!=self.__gridSizeWidth or main!=self.__gridSizeMain:
            # force grid to be recalculated
            self.__gridStrokesRect=QRect()
            self.__gridSizeWidth=max(2, round(width))
            self.__gridSizeMain=max(0, main)
            self.__propertyChanged(':canvas.grid.size.main', self.__gridSizeMain)
            self.__propertyChanged(':canvas.grid.size.width', self.__gridSizeWidth)
            self.update()

    def setGridBrushColor(self, value):
        """Set color for grid background"""
        color=QColor(value)
        color.setAlpha(255)
        self.__gridBrush.setColor(color)
        self.setBackgroundBrush(self.__gridBrush)
        self.__propertyChanged(':canvas.grid.bgColor', color)
        self.update()

    def setGridPenColor(self, value):
        """Set color for grid"""
        # get current opacity
        alphaF=self.__gridPenMain.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
        self.__propertyChanged(':canvas.grid.color', color)

        color.setAlphaF(alphaF)
        self.__gridPenMain.setColor(color)

        # apply current color and keep opacity
        color=QColor(value)
        color.setAlphaF(alphaF*BSWRendererScene.__SECONDARY_FACTOR_OPACITY)
        self.__gridPenSecondary.setColor(color)
        self.update()

    def setGridPenStyleMain(self, value):
        """Set stroke style for main grid"""
        self.__gridPenMain.setStyle(value)

        self.__propertyChanged(':canvas.grid.style.main', value)
        self.update()

    def setGridPenStyleSecondary(self, value):
        """Set stroke style for secondary grid"""
        self.__gridPenSecondary.setStyle(value)
        self.__propertyChanged(':canvas.origin.style.secondary', value)
        self.update()

    def setGridPenOpacity(self, value):
        """Set opacity for grid"""
        color=self.__gridPenMain.color()
        color.setAlphaF(value)
        self.__gridPenMain.setColor(QColor(color))

        color.setAlphaF(value*BSWRendererScene.__SECONDARY_FACTOR_OPACITY)
        self.__gridPenSecondary.setColor(QColor(color))

        self.__propertyChanged(':canvas.grid.opacity', value)
        self.update()

    def setGridPenRulerColor(self, value):
        """Set color for grid ruler ticks"""
        color=QColor(value)
        color.setAlpha(255)
        self.__gridPenRuler.setColor(color)
        self.__propertyChanged(':canvas.rulers.color', color)
        self.update()

    def setGridBrushRulerColor(self, value):
        """Set color for grid ruler background"""
        color=QColor(value)
        color.setAlphaF(1.0)
        self.__gridBrushRuler.setColor(color)
        self.__propertyChanged(':canvas.rulers.bgColor', color)
        self.update()


    def setOriginVisible(self, value):
        """Set if origin is visible"""
        if isinstance(value, bool) and value!=self.__originVisible:
            self.__originVisible=value
            self.__propertyChanged(':canvas.origin.visibility', self.__originVisible)
            self.update()

    def setOriginPenColor(self, value):
        """Set color for origin"""
        # get current opacity
        alphaF=self.__gridPenMain.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
        self.__propertyChanged(':canvas.origin.color', color)
        color.setAlphaF(alphaF)
        self.__originPen.setColor(color)
        self.update()

    def setOriginPenStyle(self, value):
        """Set stroke style for origin"""
        self.__originPen.setStyle(value)
        self.__propertyChanged(':canvas.origin.style', value)
        self.update()

    def setOriginPenOpacity(self, value):
        """Set opacity for grid"""
        color=self.__originPen.color()
        color.setAlphaF(value)
        self.__originPen.setColor(QColor(color))
        self.__propertyChanged(':canvas.origin.opacity', value)
        self.update()

    def setOriginSize(self, size):
        """Set size in PX used to render origin"""
        if size!=self.__originSize:
            self.__originStrokes=[]
            self.__originSize=max(5, round(size))
            self.__propertyChanged(':canvas.origin.size', self.__originSize)
            self.update()

    def setOriginPosition(self, absissa=0, ordinate=0):
        """Set settings used to define position for origin

        Values for `absissa`:
            -1: left
             0: center horizontaly
             1: right

        Values for `ordinate`:
            -1: top
             0: center vertically
             1: bottom
        """
        # no need to update origin strokes as origin is always (0,0)
        # but for background, need to apply new position for background
        self.__originPosition=(absissa, ordinate)

        # need to recalculate strokes for arrows
        self.__originStrokes=[]

        # absissa
        if self.__originPosition[0]==-1:
            # left
            self.__originPx=0
        elif self.__originPosition[0]==1:
            # right
            self.__originPx=-self.__documentBounds.width()
        else:
            # center
            self.__originPx=-self.__documentBounds.width()//2

        # ordinate
        if self.__originPosition[1]==-1:
            # top
            self.__originPy=0
        elif self.__originPosition[1]==1:
            # bottom
            self.__originPy=-self.__documentBounds.height()
        else:
            # center
            self.__originPy=-self.__documentBounds.height()//2

        self.__propertyChanged(':canvas.origin.position.absissa', self.__originPosition[0])
        self.__propertyChanged(':canvas.origin.position.ordinate', self.__originPosition[1])
        self.__calculateSceneSize()
        self.update()


    def setPositionVisible(self, value):
        """Set if position is visible"""
        if isinstance(value, bool) and value!=self.__positionVisible:
            self.__positionVisible=value
            self.__propertyChanged(':canvas.position.visibility', self.__positionVisible)
            self.update()

    def setPositionPenColor(self, value):
        """Set color for origin"""
        # get current opacity
        alphaF=self.__positionPen.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
        self.__propertyChanged(':canvas.position.color', color)
        color.setAlphaF(alphaF)
        self.__positionPen.setColor(QColor(color))

        color.setAlphaF(alphaF*BSWRendererScene.__FULFILL_FACTOR_OPACITY)
        self.__positionBrush.setColor(color)
        self.update()

    def setPositionPenOpacity(self, value):
        """Set opacity for grid"""
        color=self.__positionPen.color()
        color.setAlphaF(value)
        self.__positionPen.setColor(QColor(color))

        color.setAlphaF(value*BSWRendererScene.__FULFILL_FACTOR_OPACITY)
        self.__positionBrush.setColor(QColor(color))

        self.__propertyChanged(':canvas.position.opacity', value)
        self.update()

    def setPositionSize(self, size):
        """Set size in PX used to render origin"""
        if size!=self.__positionSize:
            self.__positionPoints=[]
            self.__positionSize=max(5, round(size))
            self.__propertyChanged(':canvas.position.size', self.__positionSize)
            self.update()

    def setPositionFulfill(self, value):
        """Set settings used to define if position is fulfill or not"""
        if self.__positionFulfill!=value:
            self.__positionFulfill=value
            self.__propertyChanged(':canvas.position.fulfill', self.__positionFulfill)
            self.update()

    def setPositionAxis(self, value):
        """Set settings used to define if position axis are visible or not"""
        if self.__positionAxis!=value:
            self.__positionAxis=value
            self.__propertyChanged(':canvas.position.axis', self.__positionAxis)
            self.update()

    def setPositionModel(self, value):
        """Set settings used to define which position model to use"""
        if self.__positionModel!=value and self.__positionModel in [BSWRendererScene.POSITION_MODEL_BASIC, BSWRendererScene.POSITION_MODEL_UPWARD, BSWRendererScene.POSITION_MODEL_ARROWHEAD]:
            self.__positionPoints=[]
            self.__positionModel=value
            self.__propertyChanged(':canvas.position.model', self.__positionModel)
            self.update()


    def setDocumentBounds(self, bounds):
        """Set document size

        Given size is a QSize()
        """
        if not isinstance(bounds, QRect):
            raise EInvalidType("Given `bounds` must be a <QRect>")
        self.__documentBounds=bounds
        self.__calculateSceneSize()
        self.update()


    def setBackgroundVisible(self, value):
        """Set if background is visible"""
        if isinstance(value, bool) and value!=self.__backgroundVisible:
            self.__backgroundVisible=value
            self.__propertyChanged(':canvas.background.visibility', self.__backgroundVisible)
            self.update()

    def setBackgroundImage(self, pixmap, bounds=None):
        """Set current background image

        If `bounds` is provided, must be a <QRect>
        If not provided, bounds are defined automatically from image, with an offset set to (0,0)
        """
        if isinstance(pixmap, QPixmap):
            self.__backgroundImage=pixmap

            if isinstance(bounds, QRect):
                self.__backgroundBounds=bounds
            else:
                self.__backgroundBounds=QRect(0,0,self.__backgroundImage.width(), self.__backgroundImage.height())
        else:
            self.__backgroundImage=None
            self.__backgroundBounds=None
        self.__calculateSceneSize()
        self.update()

    def setBackgroundOpacity(self, value):
        """Set current background opacity"""
        if isinstance(value, float) and value!=self.__backgroundOpacity:
            self.__backgroundOpacity=max(0.0, min(1.0, value))
            self.__propertyChanged(':canvas.background.opacity', self.__backgroundOpacity)
            self.update()


    def setRenderedContent(self, pixmap, position=None):
        """Set current rendered result in scene"""
        self.__renderedImage=pixmap
        if not isinstance(position, dict):
            position={}
            self.__rendererPositionX=0
            self.__rendererPositionY=0
            self.__rendererRotation=0
            self.__rendererGeometry=BSGeometry()
        else:
            self.__rendererPositionX=position['x']
            self.__rendererPositionY=position['y']
            self.__rendererRotation=position['r']
            self.__rendererGeometry=position['g']

        self.update()
        self.sceneUpdated.emit(position)




class BSRenderer(QObject):
    """A class that allows to draw indifferently on a raster or vector painter

    Notes:
    - if QtSvg is not available, it's not possible to switch to vector painter mode
    - vector painter mode IS NOT IMPLEMENTED YET
        => only define generic access to simplify improvement later
    """
    OPTION_MODE_RASTER=1
    OPTION_MODE_VECTOR=2

    def __init__(self, parent=None):
        super(BSRenderer, self).__init__(parent)

        # current painter
        self.__painter=None

        # current geometry
        self.__documentGeometry=BSGeometry()
        self.__documentResolution=1.0

        # current render mode active
        self.__renderMode=None

        # in vector mode, SVG content is stored in a buffer; need to keep it available in class scope
        self.__vectorResult=None
        # in raster mode, drawn content is stored in a QPixmap
        self.__rasterResult=None

        self.__transformOrigin=QTransform()
        self.__transformPosition=QTransform()
        self.__transform=QTransform()


    def __initRenderer(self):
        """Initialiser renderer painter"""
        # if a painter is already initialised, need to be sure the painter is not active
        # before creating a new one
        self.__painter=self.finalize()

        if self.__renderMode==BSRenderer.OPTION_MODE_RASTER:
            # ensure no more vector data are kept in memory
            self.__vectorResult=None
            self.__rasterResult = QPixmap(int(self.__documentGeometry.width()), int(self.__documentGeometry.height()))
            self.__rasterResult.fill(Qt.transparent)
            self.__painter = QPainter(self.__rasterResult)
        else:
            # ensure no more raster data are kept in memory
            self.__rasterResult=None

            self.__vectorResult = QBuffer()
            svgGenerator = QSvgGenerator()
            svgGenerator.setOutputDevice(self.__vectorResult)
            svgGenerator.setResolution(int(self.__documentResolution))
            svgGenerator.setSize(QSize(int(self.__documentGeometry.width()), int(self.__documentGeometry.height())))
            svgGenerator.setViewBox(QRectF(0, 0, self.__documentGeometry.width(), self.__documentGeometry.height()))
            self.__painter = QPainter(svgGenerator)
        self.__updateOrigin()

    def __updateOrigin(self):
        """Update painter origin according to geometry"""
        self.__transformOrigin.reset()

        self.__transformOrigin.scale(self.__documentGeometry.hScale(), self.__documentGeometry.vScale())
        self.__transformOrigin.translate(self.__documentGeometry.hTranslate(), self.__documentGeometry.vTranslate())
        #self.__transformOrigin.rotate(rotation)
        self.__updateTransform()

    def __updateTransform(self):
        """Update all transformation into a single QTransform"""
        self.__transform=QTransform(self.__transformPosition)
        self.__transform*=self.__transformOrigin
        if self.__painter:
            self.__painter.setTransform(self.__transform, False)


    def vectorModeAvailable(self):
        """Return if vector mode is available or not"""
        return QTSVG_AVAILABLE

    def renderMode(self):
        """Return current render mode"""
        return self.__renderMode

    def geometry(self):
        """Return geometry of renderer"""
        return self.__documentGeometry

    def setGeometry(self, geometry):
        """Set geometry for renderer"""
        if not isinstance(geometry, (QRect, QRectF)):
            raise EInvalidType("Given `geometry` must be a <QRect> or <QRectF>")

        self.__documentGeometry.setGeometry(geometry.left(), geometry.top(), geometry.width(), geometry.height())
        self.__updateOrigin()

    def initialiseRender(self, mode, geometry, resolution):
        """Initialise current render mode

        Given `mode` can be:
        - BSRenderer.OPTION_MODE_RASTER
        - BSRenderer.OPTION_MODE_VECTOR

        If vector mode is not available, raster mode is applied

        Method return the render mode really applied
        """
        if not mode in (BSRenderer.OPTION_MODE_RASTER, BSRenderer.OPTION_MODE_VECTOR):
            raise EInvalidValue("Given `value` must be a valid mode")
        elif not isinstance(geometry, (QRect, QRectF)):
            raise EInvalidValue("Given `geometry` must be a <QRect> or <QRectF>")
        elif not isinstance(resolution, (int, float)) or resolution<1:
            raise EInvalidValue("Given `resolution` must be a <int> or <float> greateror equal than 1")

        if (mode==BSRenderer.OPTION_MODE_VECTOR and not QTSVG_AVAILABLE):
            # no svg mode available, force raster mode
            self.__renderMode=BSRenderer.OPTION_MODE_RASTER
        else:
            self.__renderMode=mode

        self.__transformOrigin.reset()
        self.__transformPosition.reset()
        self.__documentGeometry=BSGeometry()
        self.__documentResolution=resolution
        self.setGeometry(geometry)

        # do technical stuff in private method
        self.__initRenderer()

        return self.__renderMode

    def result(self):
        """Return rendered result

        According to render mode:
        - OPTION_MODE_RASTER: return a QPixmap
        - OPTION_MODE_VECTOR: return SVG content as bytes[] array
        """
        if self.__renderMode==BSRenderer.OPTION_MODE_RASTER:
            return self.__rasterResult
        else:
            return bytes(self.__vectorResult.buffer())

    def painter(self):
        """Return current painter"""
        return self.__painter

    def finalize(self):
        """Finalize painter"""
        if self.__painter and self.__painter.isActive():
            self.__painter.end()
        self.__painter=None
        return None

    def transform(self):
        """Return QTransform for current position/rotation"""
        return self.__transformPosition

    def setRotation(self, angle, absolute=False):
        """Rotate position to given angle (in degree)

        Given `angle` is in degree
        If `absolute` is true, do an absolute rotation to given angle
        (otherwise, it's a relative rotation)

        Note: angle=0 if Y+ direction
        """
        if absolute:
            # absolute rotation
            #
            # need to reset rotation to be in default 0° rotation
            # then do a rotation of -currentRotationAngle
            rotationRadian=math.atan2(self.__transformPosition.m12(), self.__transformPosition.m11())
            self.__transformPosition.rotateRadians(-rotationRadian)

        # add rotation to current rotation transform
        self.__transformPosition.rotate(angle)
        self.__updateTransform()

    def setTranslation(self, x, y, absolute=False):
        """Translate position (in pixels)

        Given `x` and `y` define translation coordinate
        If `absolute` is true, do an absolute translation to coordinate
        (otherwise, it's a relative translation)
        """
        if absolute:
            # absolute translation
            #
            # need to reset rotation before doing translation
            # then do a rotation of -currentRotationAngle
            rotationRadian=math.atan2(self.__transformPosition.m12(), self.__transformPosition.m11())
            self.__transformPosition.rotateRadians(-rotationRadian)
            # and also need to go back to origin (0,0) then made a translation of -currentPositionX,-currentPositionY
            self.__transformPosition.translate(-self.__transformPosition.dx(), -self.__transformPosition.dy())

        # add rotation to current rotation transform
        self.__transformPosition.translate(x, y)

        if absolute:
            # for absolute translation, as rotation has been reseted to 0, need to restore it
            self.__transformPosition.rotateRadians(rotationRadian)

        self.__updateTransform()

    def position(self):
        """Return a tuple about position information
        (x, y, rotation)

        Position is in Pixels, rotation in degree
        """
        #print([self.__transformPosition.m11(), self.__transformPosition.m12(), self.__transformPosition.m13()], '\n',
        #      [self.__transformPosition.m21(), self.__transformPosition.m22(), self.__transformPosition.m23()], '\n',
        #      [self.__transformPosition.m31(), self.__transformPosition.m32(), self.__transformPosition.m33()])
        return {
                'x': self.__transformPosition.dx(),   # m31()
                'y': self.__transformPosition.dy(),   # m32()
                'r': math.atan2(self.__transformPosition.m12(), self.__transformPosition.m11()) * 180/math.pi,
                'g': self.__documentGeometry
            }

    def point(self, x, y):
        return self.__transformPosition.map(QPointF(x, y))


    def pushState(self):
        """Push current painter state

        Do a QPainter.save()
        """
        if self.__painter:
            self.__painter.save()

    def popState(self):
        """Pop painter state

        Do a QPainter.restore()
        And reapply current transformation matrix
        """
        if self.__painter:
            self.__painter.restore()
            self.__painter.setTransform(self.__transform, False)


class BSGeometry:
    """QRect() was not able to manage 'absolute' width/height

    Then a the BSGeomtry is like a QRect but more easy to use for renderer
    Also provide scale/translation automatically according to left/right & top/bottom positions
    """
    
    def __init__(self):
        self.__left=0
        self.__right=0
        self.__top=0
        self.__bottom=0

        self.__width=0
        self.__height=0

        self.__hScale=1
        self.__vScale=1

        self.__hTranslate=0
        self.__vTranslate=0

    def __repr__(self):
        return f"<BSGeometry(Pos({self.__left}, {self.__top} - {self.__right}, {self.__bottom}), Size({self.__width}, {self.__height}), Scale({self.__hScale}, {self.__vScale}), Translate({self.__hTranslate}, {self.__vTranslate}))>"

    def setGeometry(self, left, top, width, height):
        self.__left=left
        self.__top=top

        self.__width=abs(width)
        self.__height=abs(height)

        self.__hTranslate=-self.__left
        if left>0:
            self.__right=self.__left-self.__width
            self.__hScale=-1
        else:
            self.__right=self.__left+self.__width
            self.__hScale=1

        if top>0:
            self.__bottom=self.__top-self.__height
            self.__vScale=-1
            self.__vTranslate=-self.__top
        else:
            self.__bottom=self.__top+self.__height
            self.__vScale=1
            self.__vTranslate=self.__top

    def width(self):
        return self.__width

    def height(self):
        return self.__height

    def left(self):
        return self.__left

    def right(self):
        return self.__right

    def top(self):
        return self.__top

    def bottom(self):
        return self.__bottom

    def hScale(self):
        return self.__hScale

    def vScale(self):
        return self.__vScale

    def hTranslate(self):
        return self.__hTranslate

    def vTranslate(self):
        return self.__vTranslate

    def size(self):
        return QSize(self.__width, self.__height)
