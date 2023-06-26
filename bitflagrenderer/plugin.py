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

from bitflagrenderer import TITLE
from bitflagrenderer.gui.bitflagrendererdockwidget import BitFlagRendererDockWidget
from bitflagrenderer.gui.maptoolhandler import BitFlagMapTool, BitFlagMapToolHandler
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject
from qgis.gui import QgisInterface
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

        self.mMenuName = TITLE
        self.mWidget = BitFlagRendererDockWidget()

        self.actionShowDock = QAction('Bit Flag Dock')
        self.actionShowDock.setIcon(QIcon(':/bitflagrenderer/icons/bitflagimage.svg'))
        self.actionShowDock.setCheckable(True)
        self.mWidget.setToggleVisibilityAction(self.actionShowDock)

        self.mAboutAction = QAction(QIcon(':/images/themes/default/mActionPropertiesWidget.svg'), 'About')
        self.mAboutAction.triggered.connect(self.onAboutAction)

        self.mLoadExample = QAction('Load Example Data')
        self.mLoadExample.triggered.connect(self.onLoadExampleData)

        self.actionShowBitFlags = self.mWidget.actionShowBitFlags

        self.mMapTool = BitFlagMapTool(iface.mapCanvas())
        self.mMapToolHandler = BitFlagMapToolHandler(self.mMapTool, self.actionShowBitFlags)
        self.mMapToolHandler.bitFlagRequest.connect(self.mWidget.loadBitFlags)

        self.mToolBarActions = [self.actionShowDock, self.actionShowBitFlags]
        self.mPluginMenuActions = self.mToolBarActions + [self.mLoadExample, self.mAboutAction]

        for a in self.mToolBarActions:
            iface.addToolBarIcon(a)

        iface.addDockWidget(Qt.RightDockWidgetArea, self.mWidget)
        iface.registerMapToolHandler(self.mMapToolHandler)

        for a in self.mPluginMenuActions:
            iface.addPluginToRasterMenu(self.mMenuName, a)

    def unload(self):
        from qgis.utils import iface
        iface: QgisInterface
        # self.mToolBar.parent().removeToolBar(self.mToolBar)
        for a in self.mToolBarActions:
            iface.removeToolBarIcon(a)

        for a in self.mPluginMenuActions:
            iface.removePluginRasterMenu(self.mMenuName, a)

        iface.unregisterMapToolHandler(self.mMapToolHandler)
        iface.removeDockWidget(self.mWidget)

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
