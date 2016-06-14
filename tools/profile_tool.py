# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VDLTools
                                 A QGIS plugin for the Ville de Lausanne
                              -------------------
        begin                : 2016-05-09
        git sha              : $Format:%H$
        copyright            : (C) 2016 Ville de Lausanne
        author               : Christophe Gusthiot
        email                : christophe.gusthiot@lausanne.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import (QgsMapLayer,
                       QgsGeometry,
                       QGis,
                       QgsPoint,
                       QgsWKBTypes)
from qgis.gui import (QgsMapTool,
                      QgsMessageBar)
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMessageBox
from ..core.finder import Finder
from ..ui.profile_layers_dialog import ProfileLayersDialog
from ..ui.profile_dock_widget import ProfileDockWidget
from ..ui.profile_message_dialog import ProfileMessageDialog
from ..ui.profile_confirm_dialog import ProfileConfirmDialog


class ProfileTool(QgsMapTool):

    def __init__(self, iface):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.__iface = iface
        self.__canvas = iface.mapCanvas()
        self.__icon_path = ':/plugins/VDLTools/icons/profile_icon.png'
        self.__text = 'Profile of a line'
        self.__oldTool = None
        self.__lineLayer = None
        self.setCursor(Qt.ArrowCursor)
        self.__isChoosed = False
        self.__lastFeatureId = None
        self.__selectedFeature = None
        self.__dockWdg = None
        self.__layDlg = None
        self.__msgDlg = None
        self.__confDlg = None
        self.__points = None
        self.__layers = None
        self.__features = None

    def icon_path(self):
        return self.__icon_path

    def text(self):
        return self.__text

    def setTool(self):
        self.__oldTool = self.__canvas.mapTool()
        self.__canvas.setMapTool(self)

    def activate(self):
        QgsMapTool.activate(self)
        self.__dockWdg = ProfileDockWidget(self.__iface)
        self.__iface.addDockWidget(Qt.BottomDockWidgetArea, self.__dockWdg)

    def deactivate(self):
        if self.__dockWdg is not None:
            self.__dockWdg.close()
        if QgsMapTool is not None:
            QgsMapTool.deactivate(self)

    def setEnable(self, layer):
        if layer is not None and layer.type() == QgsMapLayer.VectorLayer and \
                        QGis.fromOldWkbType(layer.wkbType()) == QgsWKBTypes.LineStringZ:
            self.__lineLayer = layer
            self.action().setEnabled(True)
            return
        self.action().setEnabled(False)
        if self.__canvas.mapTool == self:
            self.__canvas.setMapTool(self.__oldTool)
        if self.__dockWdg is not None:
            self.__dockWdg.close()
        self.__lineLayer = None

    def __setLayerDialog(self, pointLayers):
        self.__layDlg = ProfileLayersDialog(pointLayers)
        self.__layDlg.okButton().clicked.connect(self.__layOk)
        self.__layDlg.cancelButton().clicked.connect(self.__layCancel)

    def __closeLayerDialog(self):
        self.__layDlg.close()
        self.__layDlg.okButton().clicked.disconnect()
        self.__layDlg.cancelButton().clicked.disconnect()

    def __setMessageDialog(self, situations, names):
        self.__msgDlg = ProfileMessageDialog(situations, names, self.__points)
        self.__msgDlg.passButton().clicked.connect(self.__msgPass)
        self.__msgDlg.onLineButton().clicked.connect(self.__onLine)
        self.__msgDlg.onPointsButton().clicked.connect(self.__onPoints)

    def __closeMessageDialog(self):
        self.__msgDlg.close()
        self.__msgDlg.passButton().clicked.disconnect(self.__msgPass)
        self.__msgDlg.onLineButton().clicked.disconnect(self.__onLine)
        self.__msgDlg.onPointsButton().clicked.disconnect(self.__onPoints)

    def __setConfirmDialog(self, origin):
        self.__confDlg = ProfileConfirmDialog()
        if origin == 0 and self.__lineLayer.isEditable is not True:
            self.__confDlg.setMessage("Do you really want to edit the LineString layer ?")
            self.__confDlg.okButton().clicked.connect(self.__onConfirmedLine)
            self.__confDlg.cancelButton().clicked.connect(self.__onCloseConfirm)
        elif origin != 0:
            situations = self.__msgDlg.getSituations()
            case = True
            for s in situations:
                layer = self.__layers[s['layer'] - 1]
                if layer.isEditable is not True:
                    case = False
                    break
            if case is not True:
                self.__confDlg.setMessage("Do you really want to edit the Point layer(s) ?")
                self.__confDlg.okButton().clicked.connect(self.__onConfirmedPoints)
                self.__confDlg.cancelButton().clicked.connect(self.__onCloseConfirm)
            else:
                self.__onConfirmedPoints()
        else:
            self.__onConfirmedLine()

    def __closeConfirmDialog(self):
        self.__confDlg.close()
        self.__confDlg.okButton().clicked.disconnect(self.__onConfirmedPoints)
        self.__confDlg.cancelButton().clicked.disconnect(self.__onCloseConfirm)

    def __getPointLayers(self):
        layerList = []
        for layer in self.__iface.mapCanvas().layers():
            if layer.type() == QgsMapLayer.VectorLayer and QGis.fromOldWkbType(layer.wkbType()) == QgsWKBTypes.PointZ:
                    layerList.append(layer)
        return layerList

    def __msgPass(self):
        self.__closeMessageDialog()

    def __onCloseConfirm(self):
        self.__closeConfirmDialog()

    def __onLine(self):
        self.__setConfirmDialog(0)
        self.__confDlg.show()

    def __onPoints(self):
        self.__setConfirmDialog(1)
        self.__confDlg.show()

    def __onConfirmedLine(self):
        self.__closeConfirmDialog()
        situations = self.__msgDlg.getSituations()
        points = []
        for s in situations:
            if s['point'] not in points:
                points.append(s['point'])
            else:
                QMessageBox("There is more than one elevation for the point " + str(s['point']))
                return
        self.__closeMessageDialog()
        line_v2 = self.__selectedFeature.geometry().geometry()
        for s in situations:
            z = self.__points[s['point']]['z'][s['layer']]
            line_v2.setZAt(s['point'], z)
        self.__lineLayer.startEditing()
        self.__lineLayer.changeGeometry(self.__selectedFeature.id(), QgsGeometry(line_v2))
        self.__lineLayer.updateExtents()
        self.__lineLayer.commitChanges()
        self.__dockWdg.clearData()


    def __onConfirmedPoints(self):
        self.__closeConfirmDialog()
        self.__closeMessageDialog()
        line_v2 = self.__selectedFeature.geometry().geometry()
        situations = self.__msgDlg.getSituations()
        for s in situations:
            layer = self.__layers[s['layer']-1]
            point = self.__features[s['point']][s['layer']-1]
            point_v2 = point.geometry().geometry()
            point_v2.setZ(line_v2.zAt(s['point']))
            layer.startEditing()
            layer.changeGeometry(point.id(), QgsGeometry(point_v2))
            layer.updateExtents()
            layer.commitChanges()
        self.__dockWdg.clearData()

    def __layCancel(self):
        self.__closeLayerDialog()
        self.__isChoosed = 0
        self.__lineLayer.removeSelection()

    def __layOk(self):
        self.__closeLayerDialog()
        self.__layers = self.__layDlg.getLayers()
        line_v2 = self.__selectedFeature.geometry().geometry()
        self.__features = []
        self.__points = []
        for i in xrange(line_v2.numPoints()):
            pt_v2 = line_v2.pointN(i)
            x = pt_v2.x()
            y = pt_v2.y()
            z = [pt_v2.z()]
            feat = []
            for layer in self.__layers:
                vertex = self.toCanvasCoordinates(QgsPoint(x, y))
                point = Finder.findClosestFeatureAt(vertex, layer, self)
                feat.append(point)
                if point is None:
                    z.append(None)
                else:
                    point_v2 = point.geometry().geometry()
                    z.append(point_v2.z())
            self.__points.append({'x': x, 'y': y, 'z': z})
            self.__features.append(feat)

        # points = []
        # for key, p in pointz.items():
        #     if p is not None:
        #         pt = p[0].geometry().asPoint()
        #         i = 0
        #         for l in layers:
        #             if l == p[1]:
        #                 break
        #             i += 1
        #         attName = attributes[i]
        #         z = p[0].attribute(attName)
        #         points.append({'x': pt.x(), 'y': pt.y(), 'z': z})
        names = [self.__lineLayer.name()]
        for layer in self.__layers:
            names.append(layer.name())
        self.__calculateProfile(names)
        self.__isChoosed = 0
        self.__lineLayer.removeSelection()

    def canvasMoveEvent(self, event):
        if not self.__isChoosed:
            if Finder is not None and self.__lineLayer is not None:
                f = Finder.findClosestFeatureAt(event.pos(), self.__lineLayer, self)
                if f is not None and self.__lastFeatureId != f.id():
                    self.__lastFeatureId = f.id()
                    self.__lineLayer.setSelectedFeatures([f.id()])
                if f is None:
                    self.__lineLayer.removeSelection()
                    self.__lastFeatureId = None

    def canvasReleaseEvent(self, event):
        found_features = self.__lineLayer.selectedFeatures()
        if len(found_features) > 0:
            if len(found_features) < 1:
                self.__iface.messageBar().pushMessage(u"Une seule feature à la fois", level=QgsMessageBar.INFO)
                return
            self.__selectedFeature = found_features[0]
            self.__isChoosed = 1
            pointLayers = self.__getPointLayers()
            self.__setLayerDialog(pointLayers)
            self.__layDlg.show()

    def __calculateProfile(self, names):
        if self.__points is None:
            return
        self.__dockWdg.clearData()
        if len(self.__points) == 0:
            return
        self.__dockWdg.setProfiles(self.__points)
        self.__dockWdg.drawVertLine()
        self.__dockWdg.attachCurves(names)

        situations = []
        for p in xrange(len(self.__points)):
            pt = self.__points[p]
            z0 = pt['z'][0]
            tol = 0.01 * z0
            for i in xrange(1, len(pt['z'])):
                if pt['z'][i] is None:
                    continue
                if abs(pt['z'][i]-z0) > tol:
                    situations.append({'point': p, 'layer': i})
        if len(situations) > 0:
            self.__setMessageDialog(situations, names)
            self.__msgDlg.show()
