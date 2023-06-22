import copy
import pickle
from typing import List

import numpy as np

from bitflagrenderer.core.bitflagscheme import BitFlagScheme, BitFlagParameter, BitFlagState
from bitflagrenderer.core.utils import QGIS2NUMPY_DATA_TYPES, BITFLAG_DATA_TYPES
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument, QDomElement
from qgis.core import QgsRasterInterface
from qgis.core import QgsSingleBandGrayRenderer, QgsRasterTransparency, QgsRectangle, QgsRasterBlockFeedback, \
    QgsRasterBlock, Qgis, QgsRasterRenderer


class BitFlagRenderer(QgsSingleBandGrayRenderer):
    """
    A raster renderer to show flag states of a single byte/int/uint bands.
    Inherits from QgsSingleBandGrayRenderer to function with QGIS Core widgets that cannot handle new rasterrenderer
    that inherit QgsRasterRenderer directyl
    """

    def __init__(self, input: QgsRasterInterface = None):
        super(BitFlagRenderer, self).__init__(input, 1)

        self.mFlagScheme: BitFlagScheme
        self.mFlagScheme = BitFlagScheme()
        self.mBand = 1

    # def type(self)->str:
    #    return TYPE

    def setBand(self, band: int):
        self.mBand = band

    def setGrayBand(self, band):
        self.setBand(band)

    def setBitFlagScheme(self, flagScheme: BitFlagScheme):
        assert isinstance(flagScheme, BitFlagScheme)
        self.mFlagScheme = flagScheme

    def bitFlagScheme(self) -> BitFlagScheme:
        return self.mFlagScheme

    def __reduce_ex__(self, protocol):
        return self.__class__, (), self.__getstate__()

    def __getstate__(self):
        dump = pickle.dumps(self.__dict__)
        return dump

    def __setstate__(self, state):
        d = pickle.loads(state)
        self.__dict__.update(d)

    def usesBands(self) -> List[int]:
        return [self.mBand]

    def writeXml(self, doc: QDomDocument, parentElem: QDomElement):

        if parentElem.isNull():
            return

        domElement = doc.createElement('rasterrenderer')
        domElement.setAttribute('type', self.type())
        domElement.setAttribute('opacity', str(self.opacity()))
        domElement.setAttribute('alphaBand', self.alphaBand())
        trans = self.rasterTransparency()
        if isinstance(trans, QgsRasterTransparency):
            trans.writeXml(doc, domElement)

        minMaxOriginElement = doc.createElement('minMaxOrigin')
        self.minMaxOrigin().writeXml(doc, minMaxOriginElement)

    def readXml(self, rendererElem: QDomElement):

        pass

    def legendSymbologyItems(self, *args, **kwargs):
        """ Overwritten from parent class. Items for the legend. """
        transparency = QColor(0, 255, 0, 0)
        items = [(self.bitFlagScheme().name(), transparency)]
        for parameter in self.bitFlagScheme():
            assert isinstance(parameter, BitFlagParameter)
            visibleStates = [s for s in parameter if s.isVisible()]
            if len(visibleStates) == 0:
                continue

            items.append(('[{}]'.format(parameter.name()), transparency))

            for flagState in visibleStates:
                assert isinstance(flagState, BitFlagState)
                item = (flagState.name(), flagState.color())
                items.append(item)
        return items

    def block(self, band_nr: int, extent: QgsRectangle, width: int, height: int,
              feedback: QgsRasterBlockFeedback = None):
        """" Overwritten from parent class. Todo.

        :param band_nr: todo
        :param extent: todo
        :param width: todo
        :param height: todo
        :param feedback: todo
        """

        # see https://github.com/Septima/qgis-hillshaderenderer/blob/master/hillshaderenderer.py
        nb = self.input().bandCount()
        scheme = self.bitFlagScheme()

        #  output_block = QgsRasterBlock(Qgis.ARGB32_Premultiplied, width, height)
        output_block = QgsRasterBlock(Qgis.ARGB32, width, height)
        color_array = np.frombuffer(output_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[output_block.dataType()])
        color_array[:] = scheme.noDataColor().rgba()

        if len(self.bitFlagScheme()) == 0 or self.input().dataType(self.mBand) not in BITFLAG_DATA_TYPES.keys():
            output_block.setData(color_array.tobytes())
            return output_block

        npx = height * width

        band_block: QgsRasterBlock = self.input().block(self.mBand, extent, width, height)
        band_data = np.frombuffer(band_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[band_block.dataType()])
        assert len(band_data) == npx

        # THIS! seems to be a very fast way to convert block data into a numpy array
        # block_data[b, :] = band_data

        parameterNumbers = np.zeros(band_data.shape, dtype=np.uint8)
        for i, p in enumerate(reversed(self.bitFlagScheme())):
            p: BitFlagParameter

            # extract the parameter number
            for b in range(p.bitCount()):
                mask = 1 << (p.firstBit() + b)
                parameterNumbers += 2 ** b * np.uint8((band_data & mask) != 0)

            # compare each flag state
            for j, flagState in enumerate(p):
                flagState: BitFlagState
                if not flagState.isVisible():
                    continue

                if scheme.combineFlags():
                    rgba = scheme.combinedFlagsColor().rgba()
                else:
                    rgba = flagState.color().rgba()
                color_array[np.where(parameterNumbers == flagState.bitNumber())[0]] = rgba

            parameterNumbers.fill(0)

        output_block.setData(color_array.tobytes())
        return output_block

    def clone(self) -> QgsRasterRenderer:
        """ Overwritten from parent class. """
        r = BitFlagRenderer(self.input())
        scheme = copy.deepcopy(self.bitFlagScheme())
        r.setBitFlagScheme(scheme)
        return r
