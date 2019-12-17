# -*- coding: utf-8 -*-
import unittest
from qgis.testing import start_app, stop_app
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

from qps.testing import initQgisApplication
from bitflagrenderer.bitflagrenderer import *

QAPP = initQgisApplication()
SHOW_GUI = False and os.environ.get('CI') is None

pathFlagImage = r'J:\diss_bj\level2\s-america\X0048_Y0025\20140826_LEVEL2_LND07_QAI.tif'


class BitFlagRendererTests(unittest.TestCase):


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



        if SHOW_GUI:
            QAPP.exec_()


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
        btnReAdd.clicked.connect(lambda : w.setRasterLayer(lyr))

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

        if SHOW_GUI:
            QAPP.exec_()



    def test_BitFlagRenderer(self):

        lyr = self.bitFlagLayer()
        self.assertIsInstance(lyr, QgsRasterLayer)
        dp = lyr.dataProvider()
        self.assertIsInstance(dp, QgsRasterDataProvider)

        renderer = BitFlagRenderer()
        renderer.setInput(lyr.dataProvider())
        renderer.setBand(1)

        flagPars = self.createBitFlagParameters()

        renderer.setFlagParameters(flagPars)
        lyr.setRenderer(renderer)

        self.assertListEqual(flagPars, renderer.flagParameters())
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

        if SHOW_GUI:
            QAPP.exec_()

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

        #w = factory.createWidget(lyr, canvas)
        #w.show()

        if SHOW_GUI:
            QAPP.exec_()

    def test_factory(self):

        from bitflagrenderer.bitflagrenderer import registerConfigWidgetFactory, unregisterConfigWidgetFactory

        registerConfigWidgetFactory()
        unregisterConfigWidgetFactory()

if __name__ == '__main__':
    unittest.main()
