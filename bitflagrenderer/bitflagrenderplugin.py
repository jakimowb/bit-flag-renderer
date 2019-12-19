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

import os, sys, site
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *



class BitFlagRendererPlugin(object):

    def __init__(self, iface:QgisInterface):
        self.iface = iface
        self.mFactory = None

        from bitflagrenderer import TITLE
        self.mMenuName = TITLE

    def initGui(self):

        pluginDir = os.path.dirname(__file__)
        if not pluginDir in sys.path:
            sys.path.append(pluginDir)

        from bitflagrenderer.bitflagrenderer import registerConfigWidgetFactory
        registerConfigWidgetFactory()


        self.mAboutAction = QAction(QIcon(':/images/themes/default/mActionPropertiesWidget.svg'), 'About')
        self.mAboutAction.triggered.connect(self.onAboutAction)

        self.mLoadExample = QAction('Load Example Data')
        self.mLoadExample.triggered.connect(self.onLoadExampleData)
        self.iface.addPluginToRasterMenu(self.mMenuName, self.mAboutAction)
        self.iface.addPluginToRasterMenu(self.mMenuName, self.mLoadExample)

    def onAboutAction(self, _testing=False):

        from bitflagrenderer.bitflagrenderer import AboutBitFlagRenderer

        d = AboutBitFlagRenderer()
        if _testing:
            d.show()
        else:
            d.exec_()

    def onLoadExampleData(self):

        from bitflagrenderer import DIR_EXAMPLE_DATA
        from bitflagrenderer.bitflagrenderer import BitFlagRenderer
        from bitflagrenderer.bitflagschemes import Landsat8_QA
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
            import copy
            r.setBitFlagScheme(copy.deepcopy(scheme))
            lyrBQA.setRenderer(r)

            QgsProject.instance().addMapLayers([lyrTOA, lyrBQA])
            canvas = iface.mapCanvas()
            assert isinstance(canvas, QgsMapCanvas)
            canvas.setDestinationCrs(lyrBQA.crs())
            canvas.setExtent(lyrBQA.extent())

            s = ""



    def unload(self):
        from bitflagrenderer.bitflagrenderer import unregisterConfigWidgetFactory
        unregisterConfigWidgetFactory()

