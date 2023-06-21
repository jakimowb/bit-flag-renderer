import os
import re
from typing import List

from osgeo import gdal_array

from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_REPO
from bitflagrenderer.core.bitflagscheme import BitFlagScheme, BitFlagParameter
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsRasterLayer
from qps.testing import TestCase
from qps.utils import file_search

pathFlagImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*BQA.*\.tif$')))[0]
pathTOAImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*TOA.*\.tif$')))[0]

DIR_TMP = DIR_REPO / 'tmp'
os.makedirs(DIR_TMP, exist_ok=True)


class BitFlagTestCases(TestCase):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        array = gdal_array.LoadFile(pathTOAImage)
        array = array / 10000.0
        self.mTmpFloat = '/vsimem/floatimage.tif'
        gdal_array.SaveArray(array, self.mTmpFloat, prototype=pathTOAImage)

    def bitFlagLayer(self) -> QgsRasterLayer:
        lyr = QgsRasterLayer(pathFlagImage)
        lyr.setName('Flag Image')
        return lyr

    def floatLayer(self) -> QgsRasterLayer:
        lyr = QgsRasterLayer(self.mTmpFloat)
        assert lyr.isValid()
        lyr.setName('Float Array')
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
        for p in self.createBitFlagParameters():
            scheme.addParameter(p)
        return scheme
