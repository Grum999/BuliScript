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

                for position in rulerProperties['hPos']:
                    if checkWidth and (position/delta)%modulo!=0:
                        continue
                    pt1.setX(position-textWidthH)
                    pt2.setX(position+textWidthH)
                    painter.drawText(QRectF(pt1, pt2), Qt.AlignCenter, str(position))


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
                    painter.drawText(QRectF(-rect.height()/2, -rect.width()/2, rect.height(), rect.width()), Qt.AlignCenter, str(position))
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
            self.centerOn(0,0)

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

    __SECONDARY_FACTOR_OPACITY = 0.5    # define opacity of secondary grid relative to main grid
    __FULFILL_FACTOR_OPACITY = 0.75     # define opacity of position fulfill
    __RULER_FONT_SIZE = 7               # in PT
    __ARROW_SIZE = 4                    # in PX, height of arrows drawn for origin

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
        self.__viewZoom=1.0

        self.__rulerSize=0
        self.__rulerFontHeight=0
        self.__rulerFontWidth=0

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

        self.__positionPoints=[
                QPoint(0, -size),
                QPoint(size*math.cos(-angle), -size*math.sin(-angle)),
                QPoint(size*math.cos(math.pi+angle), -size*math.sin(math.pi+angle))
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
            painter.setPen(self.__positionPen)
            if self.__positionFulfill:
                painter.setBrush(self.__positionBrush)
            else:
                painter.setBrush(QBrush(Qt.NoBrush))
            painter.drawPolygon(*self.__positionPoints)
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
                'visible': self.__gridRulerVisible
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
