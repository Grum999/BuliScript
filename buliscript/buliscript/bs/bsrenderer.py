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
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


from buliscript.pktk.modules.imgutils import checkerBoardBrush


from buliscript.pktk.pktk import (
        EInvalidType,
        EInvalidValue,
        EInvalidStatus
    )

class BSWRendererView(QGraphicsView):
    """A graphic view dedicated to render scene"""

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

    def mousePressEvent(self, event):
        """On left button pressed, start to pan scene"""
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event:QMouseEvent):
        """On left button released, stop to pan scene"""
        if event.button() == Qt.LeftButton:
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

    __MINOR_FACTOR_OPACITY = 0.5        # define opacity of minor grid relatvie to major grid
    __FULFILL_FACTOR_OPACITY = 0.75     # define opacity of position fulfill
    __RULER_SIZE = 28                   # in PX
    __RULER_FONT_SIZE = 16              # in PX

    def __init__(self, parent=None):
        super(BSWRendererScene, self).__init__(parent)

        # settings
        self.__gridSizeWidth = 20
        self.__gridSizeMajor = 5
        self.__gridBrush=QBrush(QColor("#393939"))
        self.__gridPenMajor=QPen(QColor("#FF292929"))
        self.__gridPenMinor=QPen(QColor("#80292929"))
        self.__gridPenRuler=QPen(QColor("#000000"))
        self.__gridBrushRuler=QBrush(QColor("#ffffff"))
        self.__gridFontRuler=QFont("Monospace")
        self.__gridVisible=True

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

        # rendered image
        self.__renderedImage=None


        # internal data for rendering
        self.__gridStrokesRect=QRect()
        self.__gridStrokesMajor=[]
        self.__gridStrokesMinor=[]
        self.__gridStrokesRuler=[]
        self.__gridTextRulerH=[]
        self.__gridTextRulerV=[]
        self.__originStrokes=[]
        self.__positionPoints=[]
        self.__viewZoom=1.0

        self.initialise()
        self.setBackgroundBrush(self.__gridBrush)


    def __generateGridStrokes(self, rect):
        """Generate grid strokes (avoid to regenerate them on each update)"""
        if rect==self.__gridStrokesRect:
            # viewport is the same, keep current gris definition
            return

        self.__gridStrokesMinor=[]
        self.__gridStrokesMajor=[]
        self.__gridStrokesRuler=[]
        self.__gridTextRulerH=[]
        self.__gridTextRulerV=[]

        if not self.__gridVisible:
            return

        # bounds
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        # ruler bounds
        rulerSizeMinor=BSWRendererScene.__RULER_SIZE - (BSWRendererScene.__RULER_SIZE - BSWRendererScene.__RULER_FONT_SIZE)//2

        rulerHFromMajor=top+BSWRendererScene.__RULER_FONT_SIZE
        rulerHFromMinor=top+rulerSizeMinor
        rulerHToMajor=top+BSWRendererScene.__RULER_SIZE
        rulerHToMinor=top+BSWRendererScene.__RULER_SIZE

        rulerVFromMajor=left+BSWRendererScene.__RULER_FONT_SIZE
        rulerVFromMinor=left+rulerSizeMinor
        rulerVToMajor=left+BSWRendererScene.__RULER_SIZE
        rulerVToMinor=left+BSWRendererScene.__RULER_SIZE


        firstLeftStroke = left - (left % self.__gridSizeWidth)
        firstTopStroke = top - (top % self.__gridSizeWidth)

        # frequency of major strokes
        majorStroke=max(1, self.__gridSizeWidth * self.__gridSizeMajor)

        # generate vertical grid lines
        for positionX in range(firstLeftStroke, right, self.__gridSizeWidth):
            if (positionX % majorStroke != 0):
                self.__gridStrokesMinor.append(QLine(positionX, top, positionX, bottom))
                if positionX>rulerVToMajor:
                    self.__gridStrokesRuler.append(QLine(positionX, rulerHFromMinor, positionX, rulerHToMinor))
            else:
                self.__gridStrokesMajor.append(QLine(positionX, top, positionX, bottom))
                if positionX>rulerVToMajor:
                    self.__gridStrokesRuler.append(QLine(positionX, rulerHFromMajor, positionX, rulerHToMajor))
                    self.__gridTextRulerH.append((QRect(positionX-24, top, 48, BSWRendererScene.__RULER_FONT_SIZE), str(positionX)))

        # generate horizontal grid lines
        for positionY in range(firstTopStroke, bottom, self.__gridSizeWidth):
            if (positionY % majorStroke != 0):
                self.__gridStrokesMinor.append(QLine(left, positionY, right, positionY))
                if positionY>rulerHToMajor:
                    self.__gridStrokesRuler.append(QLine(rulerVFromMinor, positionY, rulerVToMinor, positionY))
            else:
                self.__gridStrokesMajor.append(QLine(left, positionY, right, positionY))
                if positionY>rulerHToMajor:
                    self.__gridStrokesRuler.append(QLine(rulerVFromMajor, positionY, rulerVToMajor, positionY))
                    self.__gridTextRulerV.append((QRect(left, positionY-24, BSWRendererScene.__RULER_FONT_SIZE, 48), str(positionY)))

    def __generateOriginStrokes(self):
        """Generate grid strokes (avoid to regenerate them on each update)"""
        if len(self.__originStrokes)>0:
            # strokes are already generated, does nothing
            return

        size=self.__originSize/2

        # absissa, ordinate
        self.__originStrokes=[
                QLine(-size, 0, size, 0),
                QLine(0, -size, 0, size)
            ]

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
        """Calculate scene size according to current document & background bounds"""
        if self.__documentBounds is None:
            size=5000
        else:
            size=max(self.__documentBounds.width(), self.__documentBounds.height())

        if not self.__backgroundBounds is None:
            size=max(size, self.__backgroundBounds.right()+abs(min(0, self.__backgroundBounds.left())))
            size=max(size, self.__backgroundBounds.bottom()+abs(min(0, self.__backgroundBounds.top())))

        size*=2

        self.setSize(size, size)


    def initialise(self):
        """Initialize render scene"""
        self.__gridPenMajor.setWidth(0)
        self.__gridPenMinor.setWidth(0)
        self.__gridPenRuler.setWidth(0)
        self.__originPen.setWidth(0)
        self.__positionPen.setWidth(0)

        self.__gridFontRuler.setPixelSize(BSWRendererScene.__RULER_FONT_SIZE-2)


    def drawBackground(self, painter, rect):
        """Draw background (defined layer, checker board)"""
        super(BSWRendererScene, self).drawForeground(painter, rect)

        if self.__documentBounds:
            painter.save()
            painter.translate(self.__originPx, self.__originPy)

            painter.fillRect(self.__documentBounds, self.__backgroundCBBrush)
            if self.__backgroundImage:
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

        # generate grid lines
        self.__generateGridStrokes(rect)

        # draw the lines
        if len(self.__gridStrokesMinor)>0:
            painter.setPen(self.__gridPenMinor)
            painter.drawLines(*self.__gridStrokesMinor)

        if len(self.__gridStrokesMajor)>0:
            painter.setPen(self.__gridPenMajor)
            painter.drawLines(*self.__gridStrokesMajor)

        # generate origin
        self.__generateOriginStrokes()

        # draw origin
        if len(self.__originStrokes):
            painter.setPen(self.__originPen)
            painter.drawLines(*self.__originStrokes)


        # generate position
        self.__generatePositionPoints()

        # draw position
        if len(self.__positionPoints):
            painter.save()
            painter.setPen(self.__positionPen)
            if self.__positionFulfill:
                painter.setBrush(self.__positionBrush)
            else:
                painter.setBrush(QBrush(Qt.NoBrush))
            painter.drawPolygon(*self.__positionPoints)
            painter.restore()

        # draw the rulers
        if len(self.__gridStrokesRuler)>0:
            # ruler BG
            painter.fillRect(rect.left(), rect.top(), BSWRendererScene.__RULER_SIZE, rect.height(), self.__gridBrushRuler)
            painter.fillRect(rect.left(), rect.top(), rect.width(), BSWRendererScene.__RULER_SIZE, self.__gridBrushRuler)

            # ruler ticks
            painter.setPen(self.__gridPenRuler)
            painter.drawLines(*self.__gridStrokesRuler)

            # ruler numbers
            painter.setFont(self.__gridFontRuler)
            for text in self.__gridTextRulerH:
                painter.drawText(text[0], Qt.AlignCenter, text[1])

            for text in self.__gridTextRulerV:
                # rotated text...
                # 1) Translate canvas origin to center of boudning rect
                # 2) Do rotation
                # 3) Draw text
                #    . position must be relative new center, (then 0,0 with offset to bound rect)
                #    . as a 90° rotation has been made, need to switch width&height
                painter.save()
                painter.translate(text[0].center().x(), text[0].center().y())
                painter.rotate(-90)
                painter.drawText(-text[0].height()//2, -text[0].width()//2, text[0].height(), text[0].width(), Qt.AlignCenter, text[1])
                painter.restore()



    def setSize(self, width, height):
        """Define size of scene with given `width` and `height`

        Note: they must be greater than painted area
        """
        self.setSceneRect(-width // 2, -height // 2, width, height)

    # --------------------------------------------------------------------------
    # getters
    # --------------------------------------------------------------------------
    def gridVisible(self):
        """Return if grid is visible"""
        return self.__gridVisible

    def gridSize(self):
        """Return a tuple (grid size width, major grid frequency) in PX"""
        return (self.__gridSizeWidth, self.__gridSizeMajor)

    def gridPenMajor(self):
        """Return pen used to render major grid"""
        return self.__gridPenMajor

    def gridPenMinor(self):
        """Return pen used to render minor grid"""
        return self.__gridPenMinor

    def gridFontRuler(self):
        """Return font used to render grid ruler"""
        return self.__gridFontRuler

    def gridBrushRuler(self):
        """Return brush used to render grid ruler"""
        return self.__gridBrushRuler

    def gridPenRuler(self):
        """Return pen used used to render grid ruler"""
        return self.__gridPenMinor



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

    def setGridVisible(self, value):
        """Set if grid is visible"""
        if isinstance(value, bool) and value!=self.__gridVisible:
            self.__gridVisible=value
            update()

    def setGridSize(self, width, major=0):
        """Set grid size, given `width` is in PX
        Given `major` is an integer that define to draw a major line everything `major` line
        """
        if width!=self.__gridSizeWidth or major!=self.__gridSizeMajor:
            # force grid to be recalculated
            self.__gridStrokesRect=QRect()
            self.__gridSizeWidth=max(2, round(width))
            self.__gridSizeMajor=max(0, major)
            self.update()

    def setGridBrush(self, value):
        """Set color for grid background"""
        color=QColor(value)
        color.setAlpha(255)
        self.__gridBrush.setColor(color)
        self.setBackgroundBrush(self.__gridBrush)

    def setGridPenColor(self, value):
        """Set color for grid"""
        # get current opacity
        alphaF=self.__gridPenMajor.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
        color.setAlphaF(alphaF)
        self.__gridPenMajor.setColor(color)

        # apply current color and keep opacity
        color=QColor(value)
        color.setAlphaF(alphaF*BSWRendererScene.__MINOR_FACTOR_OPACITY)
        self.__gridPenMinor.setColor(color)
        self.update()

    def setGridPenStyleMajor(self, value):
        """Set stroke style for major grid"""
        self.__gridPenMajor.setStyle(value)
        self.update()

    def setGridPenStyleMinor(self, value):
        """Set stroke style for minor grid"""
        self.__gridPenMinor.setStyle(value)
        self.update()

    def setGridPenOpacity(self, value):
        """Set opacity for grid"""
        color=self.__gridPenMajor.color()
        color.setAlphaF(value)
        self.__gridPenMajor.setColor(QColor(color))

        color.setAlphaF(value*BSWRendererScene.__MINOR_FACTOR_OPACITY)
        self.__gridPenMinor.setColor(QColor(color))
        self.update()

    def setGridPenRulerColor(self, value):
        """Set color for grid ruler ticks"""
        color=QColor(value)
        color.setAlpha(255)
        self.__gridPenRuler.setColor(color)
        self.update()

    def setGridBrushRulerColor(self, value):
        """Set color for grid ruler background"""
        color=QColor(value)
        color.setAlphaF(1.0)
        self.__gridBrushRuler.setColor(color)
        self.update()


    def setOriginVisible(self, value):
        """Set if origin is visible"""
        if isinstance(value, bool) and value!=self.__originVisible:
            self.__originVisible=value
            update()

    def setOriginPenColor(self, value):
        """Set color for origin"""
        # get current opacity
        alphaF=self.__gridPenMajor.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
        color.setAlphaF(alphaF)
        self.__originPen.setColor(color)
        self.update()

    def setOriginPenStyle(self, value):
        """Set stroke style for origin"""
        self.__originPen.setStyle(value)
        self.update()

    def setOriginPenOpacity(self, value):
        """Set opacity for grid"""
        color=self.__originPen.color()
        color.setAlphaF(value)
        self.__originPen.setColor(QColor(color))
        self.update()

    def setOriginSize(self, size):
        """Set size in PX used to render origin"""
        if size!=self.__originSize:
            self.__originStrokes=[]
            self.__originSize=max(5, round(size))
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

        self.update()


    def setPositionVisible(self, value):
        """Set if position is visible"""
        if isinstance(value, bool) and value!=self.__positionVisible:
            self.__positionVisible=value
            update()

    def setPositionPenColor(self, value):
        """Set color for origin"""
        # get current opacity
        alphaF=self.__positionPen.color().alphaF()

        # apply current color and keep opacity
        color=QColor(value)
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
        self.update()

    def setPositionSize(self, size):
        """Set size in PX used to render origin"""
        if size!=self.__positionSize:
            self.__positionPoints=[]
            self.__positionSize=max(5, round(size))
            self.update()

    def setPositionFulfill(self, value):
        """Set settings used to define if position is fulfill or not"""
        if self.__positionFulfill!=value:
            self.__positionFulfill=value
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
            self.update()
