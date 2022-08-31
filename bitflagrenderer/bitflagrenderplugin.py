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

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsProject
from qgis.gui import QgsMapCanvas
from qgis.utils import iface


class BitFlagRendererPlugin(object):

    def __init__(self, *args):
        self.mFactory = None

        from bitflagrenderer import TITLE
        self.mMenuName = TITLE

    def initGui(self):

        pluginDir = os.path.dirname(__file__)
        if pluginDir not in sys.path:
            sys.path.append(pluginDir)

        from bitflagrenderer.bitflagrenderer_rc import qInitResources
        qInitResources()

        from bitflagrenderer.bitflagrenderer import registerConfigWidgetFactory
        registerConfigWidgetFactory()

        self.mAboutAction = QAction(QIcon(':/images/themes/default/mActionPropertiesWidget.svg'), 'About')
        self.mAboutAction.triggered.connect(self.onAboutAction)

        self.mLoadExample = QAction('Load Example Data')
        self.mLoadExample.triggered.connect(self.onLoadExampleData)

        iface.addPluginToRasterMenu(self.mMenuName, self.mAboutAction)
        iface.addPluginToRasterMenu(self.mMenuName, self.mLoadExample)

    def onAboutAction(self, _testing=False):

        from bitflagrenderer.bitflagrenderer import AboutBitFlagRenderer

        d = AboutBitFlagRenderer()
        if _testing:
            d.show()
        else:
            d.exec_()

    def onLoadExampleData(self):

        from bitflagrenderer.exampledata import LC08_L1TP_227065_20191129_20191216_01_T1_TOA_subset_tif as pathTOA
        from bitflagrenderer.exampledata import LC08_L1TP_227065_20191129_20191216_01_T1_BQA_subset_tif as pathBQA
        from bitflagrenderer.exampledata import L8_NIR_SWIR_Red_qml as pathTOAStyle
        from bitflagrenderer.bitflagrenderer import BitFlagRenderer
        from bitflagrenderer.bitflagschemes import Landsat8_QA
        from qgis.utils import iface

        if os.path.isfile(pathTOA) and os.path.isfile(pathBQA):
            lyrTOA = iface.addRasterLayer(pathTOA, 'Landsat TOA')
            lyrBQA = iface.addRasterLayer(pathBQA, 'Landsat Quality Band')
            lyrTOA.loadNamedStyle(pathTOAStyle)

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
        iface.removePluginRasterMenu(self.mMenuName, self.mLoadExample)
        iface.removePluginRasterMenu(self.mMenuName, self.mAboutAction)
        from bitflagrenderer.bitflagrenderer import unregisterConfigWidgetFactory
        unregisterConfigWidgetFactory()
