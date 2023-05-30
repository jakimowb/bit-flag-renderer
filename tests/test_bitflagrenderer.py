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
import inspect
import pathlib
import shutil
import unittest
import os
import re
import sys

from osgeo import gdal

import qgis.testing
import gc
from typing import List, OrderedDict, Union, Tuple, Set

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QImage
from PyQt5.QtWidgets import QTreeView, QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QApplication

from qgis.gui import QgsMapCanvas, QgsRendererRasterPropertiesWidget

from qgis.core import QgsProject, QgsRasterDataProvider, QgsProcessingContext, QgsProcessingFeedback

from qps.utils import file_search, findUpwardPath
from qgis.core import QgsRasterLayer

from bitflagrenderer.bitflagrenderer import BitFlagParameter, BitFlagState, BitFlagScheme, BitFlagModel, \
    BitFlagRendererWidget, BitFlagRenderer, SaveFlagSchemeDialog, BitFlagLayerConfigWidgetFactory, AboutBitFlagRenderer
from qps.testing import start_app, TestCase

start_app()

from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_REPO

pathFlagImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*BQA.*\.tif$')))[0]
pathTOAImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*TOA.*\.tif$')))[0]

DIR_TMP = DIR_REPO / 'tmp'
os.makedirs(DIR_TMP, exist_ok=True)


class TestCaseBase(TestCase):

    @staticmethod
    def check_empty_layerstore(name: str):
        error = None
        if len(QgsProject.instance().mapLayers()) > 0:
            error = f'QgsProject layers store is not empty:\n{name}:'
            for lyr in QgsProject.instance().mapLayers().values():
                error += f'\n\t{lyr.id()}: "{lyr.name()}"'
            raise AssertionError(error)

    def setUp(self):
        self.check_empty_layerstore(f'{self.__class__.__name__}::{self._testMethodName}')

    def tearDown(self):
        self.check_empty_layerstore(f'{self.__class__.__name__}::{self._testMethodName}')
        # call gc and processEvents to fail fast
        gc.collect()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.processEvents()
        gc.collect()

    @classmethod
    def setUpClass(cls):
        cls.check_empty_layerstore(cls.__class__)

    @classmethod
    def tearDownClass(cls):
        cls.check_empty_layerstore(cls.__class__)

    @classmethod
    def showGui(cls, widgets: Union[QWidget, List[QWidget]] = None) -> bool:
        """
        Call this to show GUI(s) in case we do not run within a CI system
        """

        if widgets is None:
            widgets = []
        if not isinstance(widgets, list):
            widgets = [widgets]

        keepOpen = False

        for w in widgets:
            if isinstance(w, QWidget):
                w.show()
                keepOpen = True
            elif callable(w):
                w()

        if cls.runsInCI():
            return False

        app = QApplication.instance()
        if isinstance(app, QApplication) and keepOpen:
            app.exec_()

        return True

    @staticmethod
    def runsInCI() -> True:
        """
        Returns True if this the environment is supposed to run in a CI environment
        and should not open blocking dialogs
        """
        return str(os.environ.get('CI', '')).lower() not in ['', 'none', 'false', '0']

    @classmethod
    def createProcessingContextFeedback(cls) -> Tuple[QgsProcessingContext, QgsProcessingFeedback]:
        """
        Create a QgsProcessingContext with connected QgsProcessingFeedback
        """

        def onProgress(progress: float):
            sys.stdout.write('\r{:0.2f} %'.format(progress))
            sys.stdout.flush()

            if progress == 100:
                print('')

        feedback = QgsProcessingFeedback()
        feedback.progressChanged.connect(onProgress)

        context = QgsProcessingContext()
        context.setFeedback(feedback)

        return context, feedback

    @classmethod
    def createProcessingFeedback(cls) -> QgsProcessingFeedback:
        """
        Creates a QgsProcessingFeedback.
        :return:
        """
        feedback = QgsProcessingFeedback()

        return feedback

    def createImageCopy(self, path, overwrite_existing: bool = True) -> str:
        """
        Creates a save image copy to manipulate metadata
        :param path: str, path to valid raster image
        :type path:
        :return:
        :rtype:
        """
        if isinstance(path, pathlib.Path):
            path = path.as_posix()

        ds: gdal.Dataset = gdal.Open(path)
        assert isinstance(ds, gdal.Dataset)
        drv: gdal.Driver = ds.GetDriver()

        testdir = self.createTestOutputDirectory() / 'images'
        os.makedirs(testdir, exist_ok=True)
        bn, ext = os.path.splitext(os.path.basename(path))

        newpath = testdir / f'{bn}{ext}'
        i = 0
        if overwrite_existing and newpath.is_file():
            drv.Delete(newpath.as_posix())
        else:
            while newpath.is_file():
                i += 1
                newpath = testdir / f'{bn}{i}{ext}'

        drv.CopyFiles(newpath.as_posix(), path)

        return newpath.as_posix()

    def createTestOutputDirectory(self,
                                  name: str = 'test-outputs',
                                  subdir: str = None) -> pathlib.Path:
        """
        Returns the path to a test output directory
        :return:
        """
        if name is None:
            name = 'test-outputs'
        repo = findUpwardPath(inspect.getfile(self.__class__), '.git').parent

        testDir = repo / name
        os.makedirs(testDir, exist_ok=True)

        if subdir:
            testDir = testDir / subdir
            os.makedirs(testDir, exist_ok=True)

        return testDir

    def createTestCaseDirectory(self,
                                basename: str = None,
                                testclass: bool = True,
                                testmethod: bool = True
                                ):

        d = self.createTestOutputDirectory(name=basename)
        if testclass:
            d = d / self.__class__.__name__
        if testmethod:
            d = d / self._testMethodName

        os.makedirs(d, exist_ok=True)
        return d

    @classmethod
    def assertImagesEqual(cls, image1: QImage, image2: QImage):
        if image1.size() != image2.size():
            return False
        if image1.format() != image2.format():
            return False

        for x in range(image1.width()):
            for y in range(image1.height()):
                if image1.pixel(x, y, ) != image2.pixel(x, y):
                    return False
        return True

    def tempDir(self, subdir: str = None, cleanup: bool = False) -> pathlib.Path:
        """
        Returns the <enmapbox-repository/test-outputs/test name> directory
        :param subdir:
        :param cleanup:
        :return: pathlib.Path
        """
        DIR_REPO = findUpwardPath(__file__, '.git').parent
        if isinstance(self, TestCaseBase):
            foldername = self.__class__.__name__
        else:
            foldername = self.__name__
        p = pathlib.Path(DIR_REPO) / 'test-outputs' / foldername
        if isinstance(subdir, str):
            p = p / subdir
        if cleanup and p.exists() and p.is_dir():
            shutil.rmtree(p)
        os.makedirs(p, exist_ok=True)
        return p

    @classmethod
    def _readVSIMemFiles(cls) -> Set[str]:

        r = gdal.ReadDirRecursive('/vsimem/')
        if r is None:
            return set([])
        return set(r)


class BitFlagRendererTests(TestCaseBase):

    def bitFlagLayer(self) -> QgsRasterLayer:
        lyr = QgsRasterLayer(pathFlagImage)
        lyr.setName('Flag Image')
        return lyr

    def createBitFlagParameters(self) -> List[BitFlagParameter]:
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

    def createBitFlagScheme(self) -> BitFlagScheme:

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
            self.assertEqual(len(flagModel), i + 1)
            self.assertIsInstance(flagModel[i], BitFlagParameter)
            self.assertIsInstance(flagModel[i][0], BitFlagState)
            self.assertEqual(flagModel[i], par)

        idx = flagModel.createIndex(0, 0)
        flagModel.setData(idx, '1-3', role=[Qt.EditRole])
        flagModel.setData(idx, '3', role=[Qt.EditRole])

        self.showGui(tv)
        QgsProject.instance().removeAllMapLayers()

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
        btnReAdd.clicked.connect(lambda: w.setRasterLayer(w.rasterLayer()))

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
        QgsProject.instance().removeAllMapLayers()

    def test_BitFlagSchemes(self):

        lyr = self.bitFlagLayer()
        from bitflagrenderer.bitflagschemes import DEPR_FORCE_QAI
        scheme1 = DEPR_FORCE_QAI()
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
        self.assertIsInstance(allSchemes, OrderedDict)
        for k, v in allSchemes.items():
            self.assertIsInstance(v, BitFlagScheme)
            self.assertEqual(k, v.name())

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
        QgsProject.instance().removeAllMapLayers()

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
        QgsProject.instance().removeAllMapLayers()

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

        QgsProject.instance().removeAllMapLayers()

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
        QgsProject.instance().removeAllMapLayers()


if __name__ == '__main__':
    unittest.main()
