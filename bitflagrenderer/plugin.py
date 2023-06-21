# -*- coding: utf-8 -*-
"""
***************************************************************************
        begin                : 2019-12-19
        copyright            : (C) 2019 by Benjamin Jakimow
        email                : benjamin.jakimow[at]geo.hu-berlin.de
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************/
"""

import copy
import os
import sys

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolBar

from bitflagrenderer.gui.bitflagrendererdockwidget import BitFlagRendererDockWidget
from bitflagrenderer.gui.maptoolhandler import BitFlagMapTool, BitFlagMapToolHandler
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.gui import QgisInterface
from qgis.core import QgsProject
from qgis.gui import QgsMapCanvas


class BitFlagRendererPlugin(object):

    def __init__(self, *args, **kwds):
        self.mMapTool = None
        self.mMapToolHandler = None

    def initGui(self):

        from qgis.utils import iface
        iface: QgisInterface

        pluginDir = os.path.dirname(__file__)
        if pluginDir not in sys.path:
            sys.path.append(pluginDir)

        from bitflagrenderer.resources.bitflagrenderer_rc import qInitResources
        qInitResources()

        self.mMapToolAction = QAction('Bit Flags')
        self.mShowDock = QAction('Bit Flag Dock')
        self.mShowDock.triggered.connct(self.showDock)
        self.mMapTool = BitFlagMapTool()
        self.mMapToolHandler = BitFlagMapToolHandler(self.mMapTool, self.mMapToolAction)
        self.mWidget = BitFlagRendererDockWidget()
        self.mWidget.setMapToolAction(self.mMapToolAction)

        self.mToolBar = QToolBar()
        self.mToolBar.setToolTip('Bit Flag Renderer')
        self.mToolBar.insertAction(self.mWidget.toggleVisibilityAction())
        self.mToolBar.insertAction(self.mMapToolAction)

        iface.addDockWidget(self.mWidget, Qt.RightDockWidgetArea)
        iface.registerMapToolHandler(self.mMapToolHandler)

        self.mAboutAction = QAction(QIcon(':/images/themes/default/mActionPropertiesWidget.svg'), 'About')
        self.mAboutAction.triggered.connect(self.onAboutAction)

        self.mLoadExample = QAction('Load Example Data')
        self.mLoadExample.triggered.connect(self.onLoadExampleData)

        iface.addPluginToRasterMenu(self.mMenuName, self.mAboutAction)
        iface.addPluginToRasterMenu(self.mMenuName, self.mLoadExample)
        iface.addToolBar(self.mToolBar)

    def showDock(self):

        if isinstance(self.mWidget, BitFlagRendererDockWidget):
            self.mWidget.setUserVisible(True)

    def onAboutAction(self, _testing=False):

        from bitflagrenderer.gui.aboutdialog import AboutBitFlagRenderer

        d = AboutBitFlagRenderer()
        if _testing:
            d.show()
        else:
            d.exec_()

    def onLoadExampleData(self):

        from bitflagrenderer import DIR_EXAMPLE_DATA
        from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer
        from bitflagrenderer.core.bitflagschemes import Landsat8_QA
        from qgis.utils import iface
        pathTOA = DIR_EXAMPLE_DATA / 'LC08_L1TP_227065_20191129_20191216_01_T1.TOA.subset.tif'
        pathBQA = DIR_EXAMPLE_DATA / 'LC08_L1TP_227065_20191129_20191216_01_T1.BQA.subset.tif'
        pathTOAStyle = DIR_EXAMPLE_DATA / 'L8_NIR_SWIR_Red.qml'
        if os.path.isfile(pathTOA) and os.path.isfile(pathBQA):
            lyrTOA = iface.addRasterLayer(pathTOA.as_posix(), 'Landsat TOA')
            lyrBQA = iface.addRasterLayer(pathBQA.as_posix(), 'Landsat Quality Band')
            lyrTOA.loadNamedStyle(pathTOAStyle.as_posix())

            scheme = Landsat8_QA()
            # show the cloud confidence paramter
            scheme[4][2].setVisible(True)
            scheme[4][3].setVisible(True)

            r = BitFlagRenderer(lyrBQA.dataProvider())
            r.setBitFlagScheme(copy.deepcopy(scheme))
            lyrBQA.setRenderer(r)

            QgsProject.instance().addMapLayers([lyrTOA, lyrBQA])
            canvas = iface.mapCanvas()
            assert isinstance(canvas, QgsMapCanvas)
            canvas.setDestinationCrs(lyrBQA.crs())
            canvas.setExtent(lyrBQA.extent())

    def unload(self):
        from qgis.utils import iface
        iface: QgisInterface
        iface.removePluginRasterMenu(self.mMenuName, self.mLoadExample)
        iface.removePluginRasterMenu(self.mMenuName, self.mAboutAction)
        iface.unregisterMapToolHandler(self.mMapToolHandler)
        iface.removeDockWidget(self.mWidget)
