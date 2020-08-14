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

import unittest

from qps.testing import initQgisApplication

#from qgis.testing import start_app
#QAPP = start_app()
#QAPP.setPkgDataPath(re.sub(r'/\.$', '/Library', QAPP.pkgDataPath()))
QAPP = initQgisApplication()
from qps.utils import file_search
from qps.testing import TestObjects, TestCase
from bitflagrenderer.bitflagrenderer import *



from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_REPO
pathFlagImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*BQA.*\.tif$')))[0]
pathTOAImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*TOA.*\.tif$')))[0]


DIR_TMP = DIR_REPO / 'tmp'
os.makedirs(DIR_TMP, exist_ok=True)

class BitFlagRendererTests(TestCase):


    def bitFlagLayer(self)->QgsRasterLayer:
        lyr = QgsRasterLayer(pathFlagImage)
        lyr.setName('Flag Image')
        return lyr

    def createBitFlagParameters(self)->typing.List[BitFlagParameter]:
        parValid = BitFlagParameter('Valid data', 0)
        self.assertIsInstance(parValid, BitFlagParameter)
        self.assertEqual(len(parValid), 2)
        parValid[0].setValues('valid', 'green', False)
        parValid[1].setValues('no data', 'red', True)

        self.assertEqual(parValid[1].name(), 'no data')
        self.assertEqual(parValid[1].isVisible(), True)
        self.assertEqual(parValid[1].color(), QColor('red'))

        parCloudState = BitFlagParameter('Cloud state', 1, bitCount=2)
        self.assertIsInstance(parCloudState, BitFlagParameter)
        self.assertEqual(len(parCloudState), 4)
        parCloudState[0].setValues('clear', QColor('white'), False)
        parCloudState[1].setValues('less confident cloud', QColor('orange'), True)
        parCloudState[2].setValues('confident, opaque cloud', QColor('red'), True)
        parCloudState[3].setValues('cirrus', QColor('blue'), True)

        return [parValid, parCloudState]

    def createBitFlagScheme(self)->BitFlagScheme:

        scheme = BitFlagScheme(name='test scheme')
        scheme.mParameters.extend(self.createBitFlagParameters())
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
            self.assertEqual(len(flagModel), i+1)
            self.assertIsInstance(flagModel[i], BitFlagParameter)
            self.assertIsInstance(flagModel[i][0], BitFlagState)
            self.assertEqual(flagModel[i], par)

        idx = flagModel.createIndex(0, 0)
        flagModel.setData(idx, '1-3', role=[Qt.EditRole])
        flagModel.setData(idx, '3', role=[Qt.EditRole])

        self.showGui(tv)

    def test_BitFlagRendererWidget(self):

        lyr = self.bitFlagLayer()

        canvas = QgsMapCanvas()
        QgsProject.instance().addMapLayer(lyr)
        canvas.mapSettings().setDestinationCrs(lyr.crs())
        ext = lyr.extent()
        ext.scale(1.1)
        canvas.setExtent(ext)
        canvas.setLayers([lyr])
        canvas.show()
        canvas.waitWhileRendering()
        canvas.setCanvasColor(QColor('grey'))

        w = BitFlagRendererWidget(lyr, lyr.extent())


        btnReAdd = QPushButton('Re-Add')
        btnReAdd.clicked.connect(lambda : w.setRasterLayer(w.rasterLayer()))

        def onWidgetChanged(w, lyr):

            renderer = w.renderer()
            renderer.setInput(lyr.dataProvider())
            lyr.setRenderer(renderer)
            lyr.triggerRepaint()

        w.widgetChanged.connect(lambda lyr=lyr, w=w: onWidgetChanged(w, lyr))

        for p in self.createBitFlagParameters():
            w.mFlagModel.addFlagParameter(p)


        top = QWidget()
        top.setLayout(QHBoxLayout())
        top.layout().addWidget(canvas)
        v = QVBoxLayout()
        v.addWidget(btnReAdd)
        v.addWidget(w)
        top.layout().addLayout(v)
        top.show()

        w.saveTreeViewState()

        self.showGui(top)


    def test_BitFlagSchemes(self):

        lyr = self.bitFlagLayer()
        from bitflagrenderer.bitflagschemes import FORCE_QAI
        scheme1 = FORCE_QAI()
        self.assertIsInstance(scheme1, BitFlagScheme)

        w = BitFlagRendererWidget(lyr, lyr.extent())
        w.setBitFlagScheme(scheme1)

        r = w.renderer().clone()
        self.assertIsInstance(r, BitFlagRenderer)
        self.assertEqual(r.bitFlagScheme(), scheme1)

        tmpPath = DIR_TMP / 'test.xml'

        scheme1.setName('test')
        scheme1.writeXMLFile(tmpPath)

        savesSchemes = BitFlagScheme.fromFile(tmpPath)
        self.assertListEqual(savesSchemes, [scheme1])

        allSchemes = BitFlagScheme.loadAllSchemes()
        self.assertIsInstance(allSchemes, collections.OrderedDict)
        for k, v in allSchemes.items():
            self.assertIsInstance(v, BitFlagScheme)
            self.assertEqual(k, v.name())

    def test_SaveFlagSchemeDialog(self):

        schema = self.createBitFlagScheme()
        d = SaveFlagSchemeDialog(schema)

        self.assertEqual(schema, d.schema())

        self.showGui(d)

    def test_BitFlagRenderer(self):

        lyr = self.bitFlagLayer()
        self.assertIsInstance(lyr, QgsRasterLayer)
        dp = lyr.dataProvider()
        self.assertIsInstance(dp, QgsRasterDataProvider)

        renderer = BitFlagRenderer()
        renderer.setInput(lyr.dataProvider())
        renderer.setBand(1)

        scheme = self.createBitFlagScheme()
        renderer.setBitFlagScheme(scheme)
        lyr.setRenderer(renderer)


        self.assertEqual(scheme, renderer.bitFlagScheme())
        self.assertListEqual(scheme.mParameters, renderer.bitFlagScheme().mParameters)
        colorBlock = renderer.block(0, lyr.extent(), 200, 200)


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

        self.showGui(canvas)

    def test_BitFlagLayerConfigWidget(self):

        factory = BitFlagLayerConfigWidgetFactory()
        lyr = self.bitFlagLayer()
        parameters = self.createBitFlagParameters()

        canvas = QgsMapCanvas()
        QgsProject.instance().addMapLayer(lyr)
        canvas.mapSettings().setDestinationCrs(lyr.crs())
        ext = lyr.extent()
        ext.scale(1.1)
        canvas.setExtent(ext)
        canvas.setLayers([lyr])
        canvas.show()
        canvas.waitWhileRendering()
        canvas.setCanvasColor(QColor('grey'))

        w = factory.createWidget(lyr, canvas)

        top = QWidget()
        top.setLayout(QHBoxLayout())
        top.layout().addWidget(canvas)
        top.layout().addWidget(w)
        top.show()

        self.showGui(w)

    def test_factory(self):

        from bitflagrenderer.bitflagrenderer import registerConfigWidgetFactory, unregisterConfigWidgetFactory

        registerConfigWidgetFactory()
        unregisterConfigWidgetFactory()

    def test_AboutDialog(self):

        d = AboutBitFlagRenderer()
        d.show()

        self.showGui(d)


    def test_Plugin(self):

        pluginDir = DIR_REPO.as_posix()
        addPluginDir = pluginDir not in sys.path
        if addPluginDir:
            sys.path.append(pluginDir)

        from bitflagrenderer.bitflagrenderplugin import BitFlagRendererPlugin
        from qgis.utils import iface
        plugin = BitFlagRendererPlugin(iface)

        plugin.initGui()

        plugin.onAboutAction(_testing=True)
        plugin.onLoadExampleData()

        plugin.unload()

        if addPluginDir:
            sys.path.remove(pluginDir)

    def test_RendererRasterPropertiesWidget(self):
        lyr = self.bitFlagLayer()
        parameters = self.createBitFlagParameters()

        canvas = QgsMapCanvas()
        QgsProject.instance().addMapLayer(lyr)
        canvas.mapSettings().setDestinationCrs(lyr.crs())
        ext = lyr.extent()
        ext.scale(1.1)
        canvas.setExtent(ext)
        canvas.setLayers([lyr])
        canvas.show()
        canvas.waitWhileRendering()
        canvas.setCanvasColor(QColor('grey'))

        r = BitFlagRenderer()
        r.setInput(lyr.dataProvider())
        lyr.setRenderer(r)

        w = QgsRendererRasterPropertiesWidget(lyr, canvas)
        w.show()
        cw = w.currentRenderWidget().renderer().type()

        self.showGui(w)

if __name__ == '__main__':
    unittest.main()
