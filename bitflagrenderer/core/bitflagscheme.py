import collections
import os
from typing import List, Iterator

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument, QDomElement

from .. import DIR_BITFLAG_SCHEMES
from .utils import nextColor


class BitFlagState(object):

    @staticmethod
    def fromXml(element: QDomElement):
        assert isinstance(element, QDomElement)
        if element.isNull() or element.nodeName() != BitFlagState.__name__:
            return None

        name = element.attribute('name')
        bitNumber = int(element.attribute('number'))
        visible = bool(element.attribute('visible').lower() in ['true', '1'])
        color = QColor(element.attribute('color'))
        state = BitFlagState(0, bitNumber, name=name, color=color, isVisible=visible)
        return state

    def __init__(self, offset: int, number: int, name: str = None, color: QColor = None, isVisible: bool = False):

        self.mBitShift: int
        self.mBitShift = offset
        self.mNumber: int
        assert isinstance(number, int) and number >= 0
        self.mNumber = number

        self.mName: str
        if name is None:
            name = 'state {}'.format(number + 1)
        self.mName = name

        if color is None:
            color = QColor('blue')
            for i in range(number):
                color = nextColor(color, mode='cat')

        self.mColor: QColor
        self.mColor = color

        self.mVisible: bool
        self.mVisible = isVisible

    def __len__(self):
        return 0

    def bitCombination(self, nbits=1) -> str:
        f = '{:0' + str(nbits) + 'b}'
        return f.format(self.mNumber)

    def bitNumber(self) -> str:
        return self.mNumber

    def name(self) -> str:
        return self.mName

    def setValues(self, name: str = None, color=None, isVisible: bool = None):

        if isinstance(name, str):
            self.setName(name)
        if color is not None:
            self.setColor(color)
        if isinstance(isVisible, bool):
            self.setVisible(isVisible)

    def setName(self, name: str):
        assert isinstance(name, str)
        self.mName = name

    def isVisible(self) -> bool:
        return self.mVisible

    def setVisible(self, b: bool):
        assert isinstance(b, bool)
        self.mVisible = b

    def color(self) -> QColor:
        return self.mColor

    def setColor(self, color):
        self.mColor = QColor(color)

    def writeXml(self, doc: QDomDocument, parentElement: QDomElement):

        if parentElement.isNull():
            return

        stateNode = doc.createElement(self.__class__.__name__)
        stateNode.setAttribute('name', self.name())
        stateNode.setAttribute('visible', self.isVisible())
        stateNode.setAttribute('color', self.color().name(QColor.HexArgb))
        stateNode.setAttribute('number', self.bitNumber())

        parentElement.appendChild(stateNode)

    def __eq__(self, other):
        if not isinstance(other, BitFlagState):
            return False
        else:
            return (self.mBitShift, self.mNumber, self.mName, self.mColor.getRgb()) == \
                (other.mBitShift, other.mNumber, other.mName, other.mColor.getRgb())

    def __lt__(self, other):
        assert isinstance(other, BitFlagState)
        if self.mBitShift == other.mBitShift:
            return self.mNumber < other.mNumber
        else:
            return self.mBitShift < other.mBitShift

    def __repr__(self) -> str:
        info = f'{self.name()}-{self.bitNumber()}'
        return super().__repr__() + info


class BitFlagParameter(object):
    """
    A class to define possible states of a flag / flag-set
    """

    @staticmethod
    def fromXml(element: QDomElement):
        assert isinstance(element, QDomElement)
        if element.isNull() or element.nodeName() != BitFlagParameter.__name__:
            return None

        name = element.attribute('name')
        zValue = int(element.attribute('z', '1'))
        firstBit = int(element.attribute('firstBit'))
        bitCount = int(element.attribute('bitCount'))

        parameter = BitFlagParameter(name, firstBit, bitCount)
        parameter.setZValue(zValue)
        stateNodes = element.elementsByTagName(BitFlagState.__name__)

        for i in range(min(len(parameter), stateNodes.count())):
            state = BitFlagState.fromXml(stateNodes.at(i).toElement())

            if isinstance(state, BitFlagState):
                state.mBitShift = firstBit
                parameter.mFlagStates[i] = state

        return parameter

    def __init__(self, name: str, firstBit: int, bitCount: int = 1):
        assert isinstance(name, str)
        assert isinstance(firstBit, int) and firstBit >= 0
        assert isinstance(bitCount, int) and bitCount >= 1 and bitCount <= 128  # this should be enough

        # initialize the parameter states
        self.mName: str = name
        self.mStartBit: int = firstBit
        self.mBitSize: int = bitCount
        self.mFlagStates = list()
        self.mZValue: int = 1

        self.mIsExpanded: bool
        self.mIsExpanded = True

        color0 = QColor('black')
        for i in range(firstBit + 1):
            color0 = nextColor(color0, 'cat')
        color = QColor(color0)

        for i in range(2 ** bitCount):
            color = nextColor(color, 'con')
            state = BitFlagState(self.mStartBit, i, name, color=color)
            self.mFlagStates.append(state)

        # a good default for 1-bit flags
        if bitCount == 1:
            self[0].setValues('No', QColor('white'), False)
            self[1].setValues('Yes', QColor('black'), False)
        else:
            self[0].setValues('No', QColor('white'), False)

    def zValue(self) -> int:
        return self.mZValue

    def setZValue(self, z: int):
        assert isinstance(z, int)
        self.mZValue = z

    def __eq__(self, other):
        if not isinstance(other, BitFlagParameter):
            return None
        if not len(other) == len(
                self) and self.name() == other.name() and self.mStartBit == other.mStartBit and self.mBitSize == other.mBitSize:
            return False
        for s1, s2 in zip(self.mFlagStates, other.mFlagStates):
            if not s1 == s2:
                return False

        return True

    def __contains__(self, item):
        return item in self.mFlagStates

    def __getitem__(self, slice):
        return self.mFlagStates[slice]

    def __iter__(self) -> Iterator[BitFlagState]:
        return iter(self.mFlagStates)

    def bitCount(self) -> int:
        return self.mBitSize

    def setFirstBit(self, firstBit: int):
        assert isinstance(firstBit, int) and firstBit >= 0
        self.mStartBit = firstBit
        for state in self.states():
            state.mBitShift = self.mStartBit

    def __len__(self):
        return len(self.mFlagStates)

    def __lt__(self, other):
        assert isinstance(other, BitFlagParameter)
        return self.mStartBit < other.mStartBit

    def __repr__(self) -> str:
        info = ': {}-{}, "{}"'.format(self.mStartBit, self.mBitSize, self.mName)
        return super().__repr__() + info

    def setBitSize(self, bitSize: int):
        assert isinstance(bitSize, int) and bitSize >= 1
        nStates0 = 2 ** self.mBitSize
        nStates2 = 2 ** bitSize
        n = len(self.mFlagStates)
        self.mBitSize = bitSize
        diff = 2 ** bitSize - n
        if diff > 0:
            # add missing states
            for i in range(diff):
                s = n + i
                state = BitFlagState(self.mStartBit, s)
                self.mFlagStates.append(state)
            # remove
        elif diff < 0:
            remove = self.mFlagStates[n + diff:]
            del self.mFlagStates[n + diff:]

    def states(self) -> List[BitFlagState]:
        return self.mFlagStates

    def visibleStates(self) -> List[BitFlagState]:
        return [state for state in self.mFlagStates if state.isVisible()]

    def name(self) -> str:
        return self.mName

    def setName(self, name: str):
        assert isinstance(name, str)
        self.mName = name

    def firstBit(self) -> int:
        return self.mStartBit

    def lastBit(self) -> int:
        """
        Returns the last bit affected by this FlagState
        :return:
        :rtype:
        """
        return self.mStartBit + self.mBitSize - 1

    def writeXml(self, doc: QDomDocument, parentElement: QDomElement):

        if parentElement.isNull():
            return

        parameterNode = doc.createElement(self.__class__.__name__)
        parameterNode.setAttribute('name', self.name())
        parameterNode.setAttribute('z', self.zValue())
        parameterNode.setAttribute('firstBit', self.firstBit())
        parameterNode.setAttribute('bitCount', self.bitCount())
        for state in self:
            state.writeXml(doc, parameterNode)

        parentElement.appendChild(parameterNode)


class BitFlagScheme(object):

    @staticmethod
    def loadAllSchemes() -> collections.OrderedDict:
        """
        Loads BitFlagSchemes.
        :return:
        :rtype:
        """
        SCHEMES = collections.OrderedDict()

        import bitflagrenderer.bitflagschemes as bfs
        schemes = [bfs.Landsat8_QA(),
                   bfs.LandsatTM_QA(),
                   bfs.LandsatMSS_QA(),
                   #  bfs.FORCE_QAI()
                   ]
        for s in schemes:
            SCHEMES[s.name()] = s

        if os.path.isdir(DIR_BITFLAG_SCHEMES):
            schemes = []
            for entry in os.scandir(DIR_BITFLAG_SCHEMES):
                if entry.is_file and entry.path.endswith('.xml'):
                    fileSchemes = BitFlagScheme.fromFile(entry.path)
                    schemes.extend(fileSchemes)
            schemes = sorted(schemes, key=lambda s: s.name())
            for s in schemes:
                SCHEMES[s.name()] = s

        return SCHEMES

    @staticmethod
    def fromFile(path: str) -> List:
        schemes = []
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                xml = f.read()
                dom = QDomDocument()
                dom.setContent(xml)

                schemeNodes = dom.elementsByTagName(BitFlagScheme.__name__)
                for i in range(schemeNodes.count()):
                    scheme = BitFlagScheme.fromXml(schemeNodes.at(i).toElement())
                    if isinstance(scheme, BitFlagScheme):
                        schemes.append(scheme)

        return schemes

    def __init__(self, name: str = 'unspecified name'):

        self.mName: str
        self.mName = name

        self.mNoDataColor = QColor(0, 0, 0, 0)

        self.mParameters: list
        self.mParameters = []

    def __eq__(self, other):

        if not isinstance(other, BitFlagScheme):
            return False
        if self.name() != other.name():
            return False
        if self.mNoDataColor != other.mNoDataColor:
            return False
        if self.mParameters != other.mParameters:
            return False
        return True

    def __len__(self):
        return len(self.mParameters)

    def __iter__(self) -> List[BitFlagParameter]:
        return iter(self.mParameters)

    def __contains__(self, item):
        return item in self.mParameters

    def __getitem__(self, slice):
        return self.mParameters[slice]

    @staticmethod
    def fromXml(element: QDomElement):
        assert isinstance(element, QDomElement)
        if element.isNull() or element.nodeName() != BitFlagScheme.__name__:
            return None

        scheme = BitFlagScheme()
        scheme.setName(element.attribute('name'))
        scheme.setNoDataColor(element.attribute('noDataColor'))

        parameterNodes = element.elementsByTagName(BitFlagParameter.__name__)
        for i in range(parameterNodes.count()):
            parameter = BitFlagParameter.fromXml(parameterNodes.at(i).toElement())
            if isinstance(parameter, BitFlagParameter):
                scheme.mParameters.append(parameter)

        return scheme

    def visibleStates(self) -> List[BitFlagState]:
        """
        Returns all visible BitFlagStates
        :return: list
        :rtype:
        """
        visible = []
        for p in self:
            visible.extend(p.visibleStates())
        return visible

    def noDataColor(self) -> QColor:
        return self.mNoDataColor

    def setNoDataColor(self, color):
        self.mNoDataColor = QColor(color)

    def setName(self, name: str):
        assert isinstance(name, str)
        self.mName = name

    def name(self) -> str:
        return self.mName

    def writeXMLFile(self, path):

        doc = QDomDocument()

        root = doc.createElement(self.__class__.__name__ + 's')
        self.writeXml(doc, root)
        doc.appendChild(root)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(doc.toString())

    def writeXml(self, doc: QDomDocument, parentElement: QDomElement):

        if parentElement.isNull():
            return

        schemeNode = doc.createElement(self.__class__.__name__)
        schemeNode.setAttribute('noDataColor', self.noDataColor().name(QColor.HexArgb))
        schemeNode.setAttribute('name', self.name())

        for parameter in self:
            parameter.writeXml(doc, schemeNode)
        parentElement.appendChild(schemeNode)
