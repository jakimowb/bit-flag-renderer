import collections
import copy
import json
import os
from typing import List, Iterator, Union

from qgis.PyQt.QtCore import QMimeData
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument, QDomElement

from .. import DIR_BITFLAG_SCHEMES
from .utils import nextColor


def bit_string(value: int) -> str:
    """
    Returns the bit representation of a number
    """
    return bin(value)[2:]


class BitFlagState(object):

    @staticmethod
    def fromXml(element: QDomElement) -> 'BitFlagState':
        assert isinstance(element, QDomElement)
        if element.isNull() or element.nodeName() != BitFlagState.__name__:
            return None

        name = element.attribute('name')
        bitNumber = int(element.attribute('number'))
        visible = bool(element.attribute('visible').lower() in ['true', '1'])
        color = QColor(element.attribute('color'))
        state = BitFlagState(0, bitNumber, name=name, color=color, isVisible=visible)
        return state

    def __init__(self, offset: int,
                 number: int,
                 name: str = None,
                 color: QColor = None,
                 isVisible: bool = False,
                 description: str = None):

        self.mBitShift: int
        self.mBitShift = offset
        self.mNumber: int
        assert isinstance(number, int) and number >= 0
        self.mNumber = number

        self.mName: str
        self.mDescription: str = description
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

    def clone(self):
        return copy.deepcopy(self)

    def value(self) -> int:
        return self.mNumber

    def __len__(self):
        return 0

    def bitCombination(self, nbits=1) -> str:
        f = '{:0' + str(nbits) + 'b}'
        return f.format(self.mNumber)

    def bitNumber(self) -> str:
        return self.mNumber

    def name(self) -> str:
        return self.mName

    def description(self) -> str:
        return self.mDescription

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
    MIMEDATAKEY = 'xml/bitflagscheme'

    @staticmethod
    def fromXml(element: QDomElement) -> List['BitFlagParameter']:
        assert isinstance(element, QDomElement)

        parameterNodes = element.elementsByTagName(BitFlagParameter.__name__)
        parameters = []

        for i in range(parameterNodes.count()):
            element = parameterNodes.at(i).toElement()
            # objectid = int(element.attribute('objectid'))
            name = element.attribute('name')
            zValue = int(element.attribute('z', '1'))
            firstBit = int(element.attribute('firstBit'))
            bitCount = int(element.attribute('bitCount'))

            parameter = BitFlagParameter(name, firstBit, bitCount)

            stateNodes = element.elementsByTagName(BitFlagState.__name__)

            for i in range(min(len(parameter), stateNodes.count())):
                state = BitFlagState.fromXml(stateNodes.at(i).toElement())
                if isinstance(state, BitFlagState):
                    state.mBitShift = firstBit
                    parameter.mFlagStates[i] = state

            parameters.append(parameter)
        return parameters

    @staticmethod
    def mimeData(parameters: List['BitFlagParameter']) -> QMimeData:

        mimeData = QMimeData()

        doc = QDomDocument()
        node = doc.createElement('BitFlagParameters')
        for p in parameters:
            p.writeXml(doc, node)
        doc.appendChild(node)
        mimeData.setData(BitFlagParameter.MIMEDATAKEY, doc.toByteArray())
        return mimeData

    @staticmethod
    def fromMimeData(mimeData: QMimeData) -> List['BitFlagParameter']:

        if mimeData.hasFormat(BitFlagParameter.MIMEDATAKEY):
            doc = QDomDocument()
            ba = mimeData.data(BitFlagParameter.MIMEDATAKEY)
            doc.setContent(ba)
            return BitFlagParameter.fromXml(doc.documentElement())
        else:
            return []

    def __init__(self,
                 name: str,
                 firstBit: int,
                 bitCount: int = 1,
                 description: str = None):
        assert isinstance(name, str)
        assert isinstance(firstBit, int) and firstBit >= 0
        assert isinstance(bitCount, int) and 1 <= bitCount <= 128  # this should be enough

        # initialize the parameter states
        self.mName: str = name
        self.mDescription: str = description
        self.mStartBit: int = firstBit
        self.mBitSize: int = bitCount
        self.mFlagStates: List[BitFlagState] = list()

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

    def clone(self) -> 'BitFlagParameter':

        return copy.deepcopy(self)

        p = BitFlagParameter(firstBit=self.firstBit(), bitCount=self.bitCount(), name=self.name())
        for i, state in enumerate(self):
            p[i] = state.clone()
        return p

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

    def description(self) -> str:
        return self.mDescription

    def setDescription(self, description: str):
        self.mDescription = description

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
        parameterNode.setAttribute('firstBit', self.firstBit())
        parameterNode.setAttribute('bitCount', self.bitCount())
        for state in self:
            state.writeXml(doc, parameterNode)

        parentElement.appendChild(parameterNode)

    def asMap(self) -> dict:
        # see https://github.com/stac-extensions/classification/blob/main/examples/item-bitfields-landsat.json
        d = dict()
        d['name'] = self.name()
        d['description'] = self.description()
        d['offset'] = self.firstBit()
        d['length'] = self.bitCount()
        classes = []
        for state in self.states():
            c = {'name': state.name(),
                 'description': state.description(),
                 'value': state.value(),
                 'visible': state.isVisible(),
                 'color': state.color().name()
                 }
            classes.append(c)
        d['classes'] = classes

        return d

    @staticmethod
    def fromMap(d: dict) -> 'BitFlagParameter':

        p = BitFlagParameter(name=d['name'],
                             firstBit=d['offset'],
                             bitCount=d['length'],
                             description=d.get('description', None))
        for i, c in enumerate(d['classes']):
            p.mFlagStates[i] = BitFlagState(d['offset'],
                                            i,
                                            name=c['name'],
                                            color=QColor(c.get('color', 'white')),
                                            isVisible=c.get('visible', False)
                                            )
        return p


class BitFlagScheme(object):
    MIMEDATA = 'applications/bitflagrenderer/bitflagscheme'

    @staticmethod
    def loadAllSchemes() -> collections.OrderedDict:
        """
        Loads BitFlagSchemes.
        :return:
        :rtype:
        """
        SCHEMES = collections.OrderedDict()

        import bitflagrenderer.core.bitflagschemes as bfs
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

        self.mCombineFlags: bool = False
        self.mCombinedFlagsColor: QColor = QColor('yellow')

        self.mParameters: list
        self.mParameters = []

    def addParameter(self, parameter: BitFlagParameter):
        assert isinstance(parameter, BitFlagParameter)
        self.mParameters.append(parameter)

    def __eq__(self, other):
        if not isinstance(other, BitFlagScheme):
            return False

        for k in self.__dict__.keys():
            a = self.__dict__[k]
            b = other.__dict__[k]
            if isinstance(a, QColor):
                a = a.name()
                b = b.name()
            if a != b:
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

    def __delitem__(self, key):
        del self.mParameters[key]

    @staticmethod
    def fromMimeData(mimeData: QMimeData) -> 'BitFlagScheme':

        if mimeData.hasFormat(BitFlagScheme.MIMEDATA):
            doc = QDomDocument()
            ba = mimeData.data(BitFlagScheme.MIMEDATA)
            doc.setContent(ba)

            node = doc.documentElement().firstChildElement(BitFlagScheme.__name__)

            return BitFlagScheme.fromXml(node)
        else:
            return None

    @staticmethod
    def fromXml(element: QDomElement) -> 'BitFlagScheme':
        assert isinstance(element, QDomElement)
        if element.isNull() or element.nodeName() != BitFlagScheme.__name__:
            return None

        scheme = BitFlagScheme()
        scheme.setName(element.attribute('name'))
        scheme.setNoDataColor(element.attribute('noDataColor'))
        scheme.setCombineFlags(element.attribute('combineFlags') not in ['0', 0, False])
        scheme.setCombinedFlagsColor(element.attribute('combinedFlagsColor'))

        parameters = BitFlagParameter.fromXml(element)
        scheme.mParameters.extend(parameters)

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

    def clone(self) -> 'BitFlagScheme':

        scheme = BitFlagScheme(name=self.name())
        scheme.setCombinedFlagsColor(self.combinedFlagsColor())
        scheme.setCombineFlags(self.combineFlags())
        for p in self:
            scheme.addParameter(p.clone())
        return scheme

    def setCombinedFlagsColor(self, color: Union[str, QColor]):
        self.mCombinedFlagsColor = QColor(color)

    def combinedFlagsColor(self) -> QColor:
        return self.mCombinedFlagsColor

    def setCombineFlags(self, b: bool):
        self.mCombineFlags = b is True

    def combineFlags(self) -> bool:
        return self.mCombineFlags

    def noDataColor(self) -> QColor:
        return self.mNoDataColor

    def setNoDataColor(self, color):
        self.mNoDataColor = QColor(color)

    def setName(self, name: str):
        assert isinstance(name, str)
        self.mName = name

    def name(self) -> str:
        return self.mName

    def mimeData(self) -> QMimeData:

        mimeData = QMimeData()
        doc = QDomDocument()
        node = doc.createElement('root')
        self.writeXml(doc, node)
        doc.appendChild(node)
        mimeData.setData(self.MIMEDATA, doc.toByteArray())
        return mimeData

    def asMap(self) -> dict:
        """
        Returns a JSON serializable dictionary
        """

        m = dict()
        m['name'] = self.name()
        m['noDataColor'] = self.noDataColor().name()
        m['combineFlags'] = self.combineFlags()
        m['combinedFlagsColor'] = self.combinedFlagsColor().name()
        m['BitFlagParameters'] = [p.asMap() for p in self.mParameters]
        return {self.__class__.__name__: m}

    def json(self) -> str:
        """
        Returns the BitFlagScheme in a JSON representation
        """
        return json.dumps(self.asMap())

    @staticmethod
    def fromJson(jsonText: str):
        m = json.loads(jsonText)

        d = m[BitFlagScheme.__name__]

        scheme = BitFlagScheme(name=d['name'])
        scheme.setNoDataColor(d['noDataColor'])
        scheme.setCombineFlags(d['combineFlags'])
        scheme.setCombinedFlagsColor(d['combinedFlagsColor'])

        for p in d[BitFlagParameter.__name__ + 's']:
            param = BitFlagParameter.fromMap(p)
            scheme.mParameters.append(param)
            s = ""
        return scheme

    def writeXmlFile(self, path):

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
        schemeNode.setAttribute('name', self.name())
        schemeNode.setAttribute('noDataColor', self.noDataColor().name(QColor.HexArgb))
        schemeNode.setAttribute('combineFlags', self.combineFlags())
        schemeNode.setAttribute('combinedFlagsColor', self.combinedFlagsColor().name())

        for parameter in self:
            parameter.writeXml(doc, schemeNode)
        parentElement.appendChild(schemeNode)
