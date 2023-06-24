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
import os
import pathlib
import re
import sys
import unittest
from typing import List

from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_REPO, DIR_BITFLAG_SCHEMES
from bitflagrenderer.core.bitflagmodel import BitFlagModel
from bitflagrenderer.core.bitflagscheme import BitFlagScheme, BitFlagParameter, BitFlagState
from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer
from bitflagrenderer.gui.aboutdialog import AboutBitFlagRenderer
from bitflagrenderer.gui.saveflagschemedialog import SaveFlagSchemeDialog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeView
from qgis.core import QgsProject, QgsRasterDataProvider
from qgis.core import QgsRasterLayer
from qgis.gui import QgsMapCanvas
from qps.testing import start_app, TestCase
from qps.utils import file_search


def filepath(root: pathlib.Path, rx: str) -> pathlib.Path:
    return list(file_search(root, re.compile(rx)))[0]


start_app()

pathFlagImage = filepath(DIR_EXAMPLE_DATA, r'.*BQA.*\.tif$')
pathTOAImage = filepath(DIR_EXAMPLE_DATA, r'.*TOA.*\.tif$')
pathFlagSchemeLND = filepath(DIR_BITFLAG_SCHEMES, r'landsat_level2_pixel_qa.xml')
pathFlagSchemeQAI = filepath(DIR_BITFLAG_SCHEMES, r'force_qai.xml')
DIR_TMP = DIR_REPO / 'tmp'
os.makedirs(DIR_TMP, exist_ok=True)


class BitFlagRendererTests(TestCase):

    def bitFlagLayer(self) -> QgsRasterLayer:
        lyr = QgsRasterLayer(pathFlagImage)
        lyr.setName('Flag Image')
        return lyr

    def createBitFlagParameters(self) -> List[BitFlagParameter]:

        parameters = BitFlagScheme.fromFile(pathFlagSchemeLND)[0][:]

        parFill = parameters[0]
        parClouds = parameters[6]

        return [parFill, parClouds]

    def createBitFlagScheme(self) -> BitFlagScheme:

        scheme = BitFlagScheme(name='TestdataScheme')
        for p in self.createBitFlagParameters():
            scheme.addParameter(p)
        return scheme

    def test_BitFlagStates(self):

        # example FORCE cloud state:
        # bit positions 1,2
        # values:   00 = 0 = clear
        #           01 = 1 = less confident cloud
        #           10 = 2 = confident, opaque cloud
        #           11 = 3 = cirrus
        # define

        flagPar = BitFlagParameter('test', 2, 3)
        self.assertIsInstance(flagPar, BitFlagParameter)
        self.assertEqual(len(flagPar), 8)
        flagPar.setBitSize(2)
        self.assertEqual(len(flagPar), 4)
        flagPar.setBitSize(3)
        self.assertEqual(len(flagPar), 8)

        flagModel = BitFlagModel()
        tv = QTreeView()
        tv.setModel(flagModel)
        tv.show()

        flagParameters = self.createBitFlagParameters()
        for i, par in enumerate(flagParameters):
            flagModel.addFlagParameter(par)
            self.assertEqual(len(flagModel), i + 1)
            self.assertIsInstance(flagModel[i], BitFlagParameter)
            self.assertIsInstance(flagModel[i][0], BitFlagState)
            self.assertEqual(flagModel[i], par)

        idx = flagModel.createIndex(0, 0)
        flagModel.setData(idx, '1-3', role=[Qt.EditRole])
        flagModel.setData(idx, '3', role=[Qt.EditRole])

        self.showGui(tv)
        QgsProject.instance().removeAllMapLayers()

    def test_SaveFlagSchemeDialog(self):

        schema = self.createBitFlagScheme()
        d = SaveFlagSchemeDialog(schema)

        self.assertEqual(schema, d.schema())

        self.showGui(d)
        QgsProject.instance().removeAllMapLayers()

    def test_BitFlagRenderer(self):

        lyr = self.bitFlagLayer()
        self.assertIsInstance(lyr, QgsRasterLayer)
        dp = lyr.dataProvider()
        self.assertIsInstance(dp, QgsRasterDataProvider)

        parameters = self.createBitFlagParameters()
        s = ""
        renderer = BitFlagRenderer()
        renderer.setInput(lyr.dataProvider())
        renderer.setBand(1)

        scheme = self.createBitFlagScheme()
        renderer.setBitFlagScheme(scheme)
        lyr.setRenderer(renderer)

        self.assertEqual(scheme, renderer.bitFlagScheme())
        self.assertListEqual(scheme.mParameters, renderer.bitFlagScheme().mParameters)
        colorBlock = renderer.block(0, lyr.extent(), lyr.width(), lyr.height())

        r2 = renderer.clone()
        self.assertIsInstance(r2, BitFlagRenderer)

        r2.legendSymbologyItems()

        canvas = QgsMapCanvas()
        QgsProject.instance().addMapLayer(lyr)
        canvas.mapSettings().setDestinationCrs(lyr.crs())
        canvas.setExtent(lyr.extent())
        canvas.setLayers([lyr])
        canvas.show()
        canvas.waitWhileRendering()
        block = lyr.renderer().block(1, canvas.extent(), lyr.width(), lyr.height())
        s = ""
        self.showGui(canvas)
        QgsProject.instance().removeAllMapLayers()

    def test_false(self):
        self.assertTrue(False)

    def test_Plugin(self):

        pluginDir = DIR_REPO.as_posix()
        addPluginDir = pluginDir not in sys.path
        if addPluginDir:
            sys.path.append(pluginDir)

        from bitflagrenderer.plugin import BitFlagRendererPlugin
        from qgis.utils import iface
        plugin = BitFlagRendererPlugin(iface)

        plugin.initGui()

        plugin.onAboutAction(_testing=True)
        plugin.onLoadExampleData()

        plugin.unload()

        if addPluginDir:
            sys.path.remove(pluginDir)

        QgsProject.instance().removeAllMapLayers()


if __name__ == '__main__':
    unittest.main()
