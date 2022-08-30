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

import bisect
import collections
import copy
import enum
import io
import os
import pathlib
import pickle
import re
import sys
import typing

import numpy as np
from osgeo import gdal

import qgis.utils
from bitflagrenderer import DIR_BITFLAG_SCHEMES
from qgis.PyQt import uic, QtXml
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtXml import *
from qgis.core import QgsRasterLayer, QgsRasterRenderer,\
    QgsRasterTransparency, Qgis, \
    QgsRectangle, QgsSingleBandGrayRenderer, QgsRasterBlock, QgsRasterBlockFeedback
from qgis.gui import QgsMapLayerConfigWidget, QgsMapCanvas, QgsRasterRendererWidget, \
    QgsMapLayerConfigWidgetFactory, QgsColorDialog, QgsFileWidget, QgisInterface

PATH_UI = os.path.join(os.path.dirname(__file__), 'bitflagrenderer.ui')
PATH_ABOUT_UI = os.path.join(os.path.dirname(__file__), 'aboutdialog.ui')
PATH_ICON = os.path.join(os.path.dirname(__file__), *['icons', 'bitflagimage.png'])
PATH_UI_SAVE_FLAG_SCHEMA = os.path.join(os.path.dirname(__file__), 'saveflagschemadialog.ui')
assert os.path.isfile(PATH_ICON)

TYPE = 'BitFlagRenderer'

# dictionary to store form classes and avoid multiple calls to read <myui>.ui
QGIS_RESOURCE_WARNINGS = set()


def qgisAppQgisInterface() -> QgisInterface:
    """
    Returns the QgisInterface of the QgisApp in case everything was started from within the QGIS Main Application
    :return: QgisInterface | None in case the qgis.utils.iface points to another QgisInterface (e.g. the EnMAP-Box itself)
    """
    try:
        import qgis.utils
        if not isinstance(qgis.utils.iface, QgisInterface):
            return None
        mainWindow = qgis.utils.iface.mainWindow()
        if not isinstance(mainWindow, QMainWindow) or mainWindow.objectName() != 'QgisApp':
            return None
        return qgis.utils.iface
    except:
        return None


def settings() -> QSettings:
    """
    Returns the Bit Flag Renderer settings.
    :return: QSettings
    """
    settings = QSettings(QSettings.UserScope, 'HU-Berlin', TYPE)

    return settings


class SettingsKeys(enum.Enum):
    TreeViewState = 'tree_view_state'
    TreeViewSortColumn = 'tree_view_sort_column'
    TreeViewSortOrder = 'tree_view_sort_order'
    BitFlagSchemes = 'bit_flag_schemes'


FACTORY = None

QGIS2NUMPY_DATA_TYPES = {Qgis.Byte: np.uint8,
                         Qgis.UInt16: np.uint16,
                         Qgis.Int16: np.int16,
                         Qgis.UInt32: np.uint32,
                         Qgis.Int32: np.int32,
                         Qgis.Float32: np.float32,
                         Qgis.Float64: np.float64,
                         Qgis.CFloat32: complex,
                         Qgis.CFloat64: np.complex64,
                         Qgis.ARGB32: np.uint32,
                         Qgis.ARGB32_Premultiplied: np.uint32}

MAX_BITS_PER_PARAMETER = 4

NEXT_COLOR_HUE_DELTA_CON = 10
NEXT_COLOR_HUE_DELTA_CAT = 100

REMOVE_setShortcutVisibleInContextMenu = hasattr(QAction, 'setShortcutVisibleInContextMenu')


def loadUi(uifile, baseinstance=None, package='', resource_suffix='_rc', remove_resource_references=True,
           loadUiType=False):
    """
    :param uifile:
    :type uifile:
    :param baseinstance:
    :type baseinstance:
    :param package:
    :type package:
    :param resource_suffix:
    :type resource_suffix:
    :param remove_resource_references:
    :type remove_resource_references:
    :return:
    :rtype:
    """

    assert os.path.isfile(uifile), '*.ui file does not exist: {}'.format(uifile)

    with open(uifile, 'r', encoding='utf-8') as f:
        txt = f.read()

    dirUi = os.path.dirname(uifile)

    locations = []

    for m in re.findall(r'(<include location="(.*\.qrc)"/>)', txt):
        locations.append(m)

    missing = []
    for t in locations:
        line, path = t
        if not os.path.isabs(path):
            p = os.path.join(dirUi, path)
        else:
            p = path

        if not os.path.isfile(p):
            missing.append(t)

    match = re.search(r'resource="[^:].*/QGIS[^/"]*/images/images.qrc"', txt)
    if match:
        txt = txt.replace(match.group(), 'resource=":/images/images.qrc"')

    if len(missing) > 0:

        missingQrc = []
        missingQgs = []

        for t in missing:
            line, path = t
            if re.search(r'.*(?i:qgis)/images/images\.qrc.*', line):
                missingQgs.append(m)
            else:
                missingQrc.append(m)

        if len(missingQrc) > 0:
            print('{}\nrefers to {} none-existing resource (*.qrc) file(s):'.format(uifile, len(missingQrc)))
            for i, t in enumerate(missingQrc):
                line, path = t
                print('{}: "{}"'.format(i + 1, path), file=sys.stderr)

        if len(missingQgs) > 0 and not isinstance(qgisAppQgisInterface(), QgisInterface):
            missingFiles = [p[1] for p in missingQrc if p[1] not in QGIS_RESOURCE_WARNINGS]

            if len(missingFiles) > 0:
                print('{}\nrefers to {} none-existing resource (*.qrc) file(s) '.format(uifile, len(missingFiles)))
                for i, path in enumerate(missingFiles):
                    print('{}: "{}"'.format(i + 1, path))
                    QGIS_RESOURCE_WARNINGS.add(path)
                print('These files are likely available in a QGIS Desktop session. Further warnings will be skipped')

    doc = QDomDocument()
    doc.setContent(txt)

    if REMOVE_setShortcutVisibleInContextMenu and 'shortcutVisibleInContextMenu' in txt:
        toRemove = []
        actions = doc.elementsByTagName('action')
        for iAction in range(actions.count()):
            properties = actions.item(iAction).toElement().elementsByTagName('property')
            for iProperty in range(properties.count()):
                prop = properties.item(iProperty).toElement()
                if prop.attribute('name') == 'shortcutVisibleInContextMenu':
                    toRemove.append(prop)
        for prop in toRemove:
            prop.parentNode().removeChild(prop)
        del toRemove

    elem = doc.elementsByTagName('customwidget')
    for child in [elem.item(i) for i in range(elem.count())]:
        child = child.toElement()

        cClass = child.firstChildElement('class').firstChild()
        cHeader = child.firstChildElement('header').firstChild()
        cExtends = child.firstChildElement('extends').firstChild()

        sClass = str(cClass.nodeValue())
        sExtends = str(cHeader.nodeValue())
        if False:
            if sClass.startswith('Qgs'):
                cHeader.setNodeValue('qgis.gui')
        if True:
            # replace 'qps' package location with local absolute position
            if sExtends.startswith('qps.'):
                cHeader.setNodeValue(re.sub(r'^qps\.', qps.__spec__.name + '.', sExtends))

    if remove_resource_references:
        # remove resource file locations to avoid import errors.
        elems = doc.elementsByTagName('include')
        for i in range(elems.count()):
            node = elems.item(i).toElement()
            attribute = node.attribute('location')
            if len(attribute) > 0 and attribute.endswith('.qrc'):
                node.parentNode().removeChild(node)

        # remove iconset resource names, e.g.<iconset resource="../qpsbitflagrenderer.qrc">
        elems = doc.elementsByTagName('iconset')
        for i in range(elems.count()):
            node = elems.item(i).toElement()
            attribute = node.attribute('resource')
            if len(attribute) > 0:
                node.removeAttribute('resource')

    buffer = io.StringIO()  # buffer to store modified XML
    buffer.write(doc.toString())
    buffer.flush()
    buffer.seek(0)

    if not loadUiType:
        return uic.loadUi(buffer, baseinstance=baseinstance, package=package, resource_suffix=resource_suffix)
    else:
        return uic.loadUiType(buffer, resource_suffix=resource_suffix)


def nextColor(color, mode='cat') -> QColor:
    """
    Returns another color.
    :param color: QColor
    :param mode: str, 'cat' for categorical colors (much difference from 'color')
                      'con' for continuous colors (similar to 'color')
    :return: QColor
    """
    assert mode in ['cat', 'con']
    assert isinstance(color, QColor)
    hue, sat, value, alpha = color.getHsl()
    if mode == 'cat':
        hue += NEXT_COLOR_HUE_DELTA_CAT
    elif mode == 'con':
        hue += NEXT_COLOR_HUE_DELTA_CON
    if sat == 0:
        sat = 255
        value = 128
        alpha = 255
        s = ""
    while hue > 360:
        hue -= 360

    return QColor.fromHsl(hue, sat, value, alpha)


def contrastColor(c: QColor) -> QColor:
    """
    Returns a QColor with good contrast to the input color c
    :param c: QColor
    :return: QColor
    """
    assert isinstance(c, QColor)
    if c.lightness() < 0.5:
        return QColor('white')
    else:
        return QColor('black')


class AboutBitFlagRenderer(QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(AboutBitFlagRenderer, self).__init__(parent)
        loadUi(PATH_ABOUT_UI, self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init()

    def init(self):
        self.mTitle = self.windowTitle()
        self.listWidget.currentItemChanged.connect(lambda: self.setAboutTitle())
        self.setAboutTitle()

        # page About
        from bitflagrenderer import PATH_LICENSE, __version__, PATH_CHANGELOG, PATH_ABOUT
        self.labelVersion.setText('{}'.format(__version__))

        def readTextFile(path: str):
            with open(path, encoding='utf-8') as f:
                return f.read()
            return 'unable to read {}'.format(path)

        # page Changed
        self.tbAbout.setHtml(readTextFile(PATH_ABOUT))
        # self.tbChanges.setHtml(readTextFile(PATH_CHANGELOG.as_posix() + '.html'))
        # self.tbLicense.setHtml(readTextFile(os.path.splitext(PATH_LICENSE)[0] + '.html'))

        self.tbChanges.setPlainText(readTextFile(PATH_CHANGELOG.as_posix()))
        self.tbLicense.setPlainText(readTextFile(PATH_LICENSE.as_posix()))

    def setAboutTitle(self, suffix=None):
        item = self.listWidget.currentItem()

        if item:
            title = '{} | {}'.format(self.mTitle, item.text())
        else:
            title = self.mTitle
        if suffix:
            title += ' ' + suffix
        self.setWindowTitle(title)


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

    def __iter__(self) -> typing.Iterator[BitFlagState]:
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

    def states(self) -> typing.List[BitFlagState]:
        return self.mFlagStates

    def visibleStates(self) -> typing.List[BitFlagState]:
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
                   #bfs.FORCE_QAI()
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
    def fromFile(path: str) -> typing.List:
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

    def __iter__(self) -> typing.List[BitFlagParameter]:
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

    def visibleStates(self) -> typing.List[BitFlagState]:
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


class BitFlagModel(QAbstractItemModel):

    def __init__(self, *args, **kwds):
        super(BitFlagModel, self).__init__(*args, **kwds)
        self.mFlagParameters = []

        self.cnBitPosition = 'Bit No.'
        self.cnName = 'Name'
        self.cnBitComb = 'Bits'
        self.cnBitNum = 'Num'
        self.cnColor = 'Color'

        self.mRootIndex = QModelIndex()

        self.mColumnNames: typing.List[str] = [self.cnBitPosition, self.cnName, self.cnBitComb, self.cnBitNum, self.cnColor]

        self.mColumnToolTips: typing.List[str] = [
            'The Flag Parameters bit position(s), e.g. "0" or "1-2"',
            'Flag Parameter / Flag State name',
            'Bit combination of the Flag State',
            "Number of bit combination within a Flag states's possible bit combinations",
            "Color of Flag State or Z-Value for colors of a Flag Parameter"
        ]

    def columnNames(self):
        return

    def __contains__(self, item):
        return item in self.mFlagParameters

    def __getitem__(self, slice):
        return self.mFlagParameters[slice]

    def __len__(self):
        return len(self.mFlagParameters)

    def __iter__(self) -> typing.Iterator[BitFlagParameter]:
        return iter(self.mFlagParameters)

    def __repr__(self):
        return self.toString()

    def toString(self):
        lines = []
        for i, par in enumerate(self):
            assert isinstance(par, BitFlagParameter)
            lines.append('{}:{}'.format(par.mStartBit, par.name()))
            for j, state in enumerate(par):
                assert isinstance(state, BitFlagState)
                line = '  {}:{}'.format(state.bitCombination(), state.mNumber, state.name())
                lines.append(line)
        return '\n'.join(lines)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self.mFlagParameters)

        item = parent.internalPointer()
        assert isinstance(item, (BitFlagParameter, BitFlagState))
        return len(item)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.mColumnNames)

    def addFlagParameter(self, flagParameter: BitFlagParameter):
        row = bisect.bisect(self.mFlagParameters, flagParameter)
        self.beginInsertRows(self.mRootIndex, row, row)
        self.mFlagParameters.insert(row, flagParameter)
        self.endInsertRows()

    def removeFlagParameter(self, flagParameter: BitFlagParameter):
        if flagParameter in self.mFlagParameters:
            row = self.mFlagParameters.index(flagParameter)
            self.beginRemoveRows(self.mRootIndex, row, row)
            self.mFlagParameters.remove(flagParameter)
            self.endRemoveRows()

    def headerData(self, section, orientation, role):
        assert isinstance(section, int)

        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.mColumnNames[section]
            if role == Qt.ToolTipRole:
                return self.mColumnToolTips[section]

        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return section

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        cName = self.mColumnNames[index.column()]

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if isinstance(index.internalPointer(), (BitFlagParameter, BitFlagState)) and index.column() == 0:
            flags = flags | Qt.ItemIsUserCheckable

        if cName == self.cnName:
            flags = flags | Qt.ItemIsEditable

        if isinstance(index.internalPointer(), BitFlagParameter) and cName in [self.cnBitPosition, self.cnColor]:
            flags = flags | Qt.ItemIsEditable

        return flags

    def parent(self, child: QModelIndex) -> QModelIndex:

        if not child.isValid():
            return QModelIndex()

        item = child.internalPointer()
        if isinstance(item, BitFlagParameter):
            return self.mRootIndex

        if isinstance(item, BitFlagState):
            for row, parameter in enumerate(self):
                if item in parameter:
                    return self.createIndex(row, 0, parameter)

        return QModelIndex()

    def nextFreeBit(self) -> int:
        if len(self) == 0:
            return 0
        else:
            lastParameter = self[-1]
            return lastParameter.lastBit() + 1

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:

        if parent == self.mRootIndex:
            # root index -> return FlagParameter
            return self.createIndex(row, column, self[row])

        if parent.parent() == self.mRootIndex:
            # sub 1 -> return FlagState
            flagParameter = self[parent.row()]
            return self.createIndex(row, column, flagParameter[row])
        return QModelIndex()

    def data(self, index: QModelIndex, role: int) -> typing.Any:
        assert isinstance(index, QModelIndex)
        if not index.isValid():
            return None

        item = index.internalPointer()
        cName = self.mColumnNames[index.column()]
        if isinstance(item, BitFlagParameter):

            if role in [Qt.DisplayRole, Qt.EditRole]:

                if cName == self.cnBitPosition:
                    if item.bitCount() == 1:
                        return '{}'.format(item.firstBit())
                    else:
                        return '{}-{}'.format(item.firstBit(), item.lastBit())
                if cName == self.cnName:
                    return item.name()

            if cName == self.cnColor:
                if role == Qt.DisplayRole:
                    return f'Z={item.zValue()}'
                elif role == Qt.EditRole:
                    return item.zValue()

            if role == Qt.ToolTipRole:
                if cName == self.cnName:
                    return item.name()

            if role == Qt.CheckStateRole and index.column() == 0:
                # consider all states except of the first (empty bit)
                considered_state = item.states()[1:]
                nStates = len(considered_state)
                nChecked = len([s for s in considered_state if s.isVisible()])
                if nChecked == 0:
                    return Qt.Unchecked
                elif nChecked < nStates:
                    return Qt.PartiallyChecked
                else:
                    return Qt.Checked

            if role == Qt.UserRole:
                return item

            if role == Qt.InitialSortOrderRole and index.column() == 0:
                return Qt.DescendingOrder

        if isinstance(item, BitFlagState):

            if role in [Qt.DisplayRole, Qt.EditRole]:
                #if cName == self.cnBitPosition:
                #    return item.bitNumber()

                if cName == self.cnBitNum:
                    return item.bitNumber()

                if cName == self.cnBitComb:
                    param = index.parent().internalPointer()
                    assert isinstance(param, BitFlagParameter)
                    return item.bitCombination(param.bitCount())

                if cName == self.cnName:
                    return item.name()

                if cName == self.cnColor:
                    return item.color().name()

            if role == Qt.BackgroundColorRole:
                if cName == self.cnColor:
                    return item.color()

            if role == Qt.TextColorRole:
                if cName == self.cnColor:
                    return contrastColor(item.color())

            if role == Qt.TextAlignmentRole:
                if cName in [self.cnBitNum, self.cnBitComb]:
                    return Qt.AlignRight

            if role == Qt.CheckStateRole and index.column() == 0:
                return Qt.Checked if item.isVisible() else Qt.Unchecked

            if role == Qt.UserRole:
                return item

        return None

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:

        if not index.isValid():
            return False

        result = False
        index
        item = index.internalPointer()
        cName = self.mColumnNames[index.column()]

        if isinstance(item, BitFlagState):
            if role == Qt.CheckStateRole and index.column() == 0:

                isChecked = value == Qt.Checked
                if item.mVisible != isChecked:
                    item.mVisible = isChecked
                    # inform parent FlagParameter
                    flagIndex = index.parent()
                    self.dataChanged.emit(flagIndex, flagIndex, [role])
                    result = True

            if role == Qt.EditRole:
                if cName == self.cnName:
                    item.setName(str(value))
                    result = True

                if cName == self.cnColor:
                    item.setColor(QColor(value))
                    result = True

        if isinstance(item, BitFlagParameter):
            if role == Qt.CheckStateRole and index.column() == 0:
                if value in [Qt.Checked, Qt.Unchecked]:
                    # apply new checkstate downwards to all FlagStates
                    for row in range(len(item)):
                        if row == 0:  # row 0 = empty flag -> consider higher values only
                            continue
                        stateIndex = self.index(row, 0, index)
                        if self.data(stateIndex, Qt.CheckStateRole) != value:
                            self.setData(stateIndex, value, Qt.CheckStateRole)
                            result = True

            if role == Qt.EditRole:
                if cName == self.cnName:
                    item.setName(str(value))
                    result = True

                if cName == self.cnColor:
                    item.setZValue(int(value))
                    result = True

                if cName == self.cnBitPosition:
                    value = str(value).strip()
                    matchSingle = re.search(r'^(\d+)$', value)
                    matchRange = re.search(r'^(\d+)-(\d+)+$', value)
                    bit1 = None
                    bitSize = None
                    if matchSingle:
                        bit1 = int(matchSingle.group(1))
                        bitSize = 1
                        result = True
                    elif matchRange:
                        bit1, bit2 = sorted([int(matchRange.group(1)), int(matchRange.group(2))])
                        bitSize = bit2 - bit1 + 1

                    if isinstance(bit1, int) and isinstance(bitSize, int) and bitSize > 0:
                        bitSize = min(bitSize, MAX_BITS_PER_PARAMETER)
                        item.setFirstBit(bit1)
                        n1 = len(item)
                        n2 = 2 ** bitSize
                        diff = n2 - n1
                        if diff < 0:
                            self.beginRemoveRows(index, n2, n1 - 1)
                            item.setBitSize(bitSize)
                            self.endRemoveRows()
                        elif diff > 0:
                            self.beginInsertRows(index, n1, n2 - 1)
                            item.setBitSize(bitSize)
                            self.endInsertRows()
                        result = True

        if result == True:
            self.dataChanged.emit(index, index, [role])

        return result

    def clear(self):

        n = self.rowCount()
        self.beginRemoveRows(QModelIndex(), 0, n - 1)
        self.mFlagParameters.clear()
        self.endRemoveRows()


class BitFlagSortFilterProxyModel(QSortFilterProxyModel):

    def __init__(self, *args, **kwds):
        super(BitFlagSortFilterProxyModel, self).__init__(*args, *kwds)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """
        Ensures correct sorting with values like 1, '1', '1-2', 10
        :param left:
        :type left:
        :param right:
        :type right:
        :return:
        :rtype:
        """
        if isinstance(left.internalPointer(), BitFlagParameter) and isinstance(right.internalPointer(),
                                                                               BitFlagParameter) \
                and left.column() == 0 and right.column() == 0:
            b1 = left.internalPointer().firstBit()
            b2 = right.internalPointer().firstBit()

            if b1 != b2:
                return b1 < b2
            else:
                return left.data(Qt.DisplayRole) < right.data(Qt.DisplayRole)
        else:
            return super(BitFlagSortFilterProxyModel, self).lessThan(left, right)


class BitFlagRendererTreeView(QTreeView):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.doubleClicked.connect(self.onDoubleClick)

    def contextMenu(self, event: QContextMenuEvent) -> QMenu:
        """
        Create the context menu
        """
        cidx = self.currentIndex()

        model = self.model()

        cname = self.model().headerData(cidx.column(), Qt.Horizontal)
        flagModel: BitFlagModel = self.model().sourceModel()
        m = QMenu()

        if bool(self.model().flags(cidx) & Qt.ItemIsEditable):
            a = m.addAction('Edit')
            a.triggered.connect(lambda *args, idx=cidx: self.onEditRequest(idx))

        if cname == flagModel.cnColor and isinstance(cidx.data(role=Qt.UserRole), BitFlagState):
            a = m.addAction('Set Color')
            a.triggered.connect(lambda *args, idx=cidx: self.showColorDialog(idx))

        return m

    def onEditRequest(self, idx: QModelIndex):
        #print(f'{idx} {idx.row()} {idx.column()} {idx.isValid()}')
        #print(idx.data(role=Qt.UserRole))
        self.setCurrentIndex(idx)
        self.edit(idx)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Opens a context menu
        """
        m = self.contextMenu(event)
        m.exec_(event.globalPos())

    def onDoubleClick(self, idx: QModelIndex) -> None:
        cname = self.model().headerData(idx.column(), Qt.Horizontal)
        flagModel: BitFlagModel = self.model().sourceModel()
        if cname == flagModel.cnColor:
            self.showColorDialog(idx)
        # other actions handled by base-class

    def showColorDialog(self, idx: QModelIndex):
        item = idx.data(role=Qt.UserRole)
        if isinstance(item, BitFlagState):
            c = QgsColorDialog.getColor(item.color(), self, \
                                        'Set color for "{}"'.format(item.name()))

            if c.isValid():
                self.model().setData(idx, c, role=Qt.EditRole)


class BitFlagRendererWidget(QgsRasterRendererWidget):

    def __init__(self, layer: QgsRasterLayer, extent: QgsRectangle):
        super(BitFlagRendererWidget, self).__init__(layer, extent)
        loadUi(PATH_UI, self)
        self.mRasterBandComboBox.setShowNotSetOption(False)

        assert isinstance(self.mTreeView, QTreeView)

        self.mFlagModel: BitFlagModel
        self.mFlagModel = BitFlagModel()
        self.mProxyModel = BitFlagSortFilterProxyModel()
        self.mProxyModel.setSourceModel(self.mFlagModel)
        self.mTreeView.setModel(self.mProxyModel)
        self.mTreeView.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.mTreeView.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.mTreeView.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.mTreeView.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.setRasterLayer(layer)

        #self.mFlagModel.rowsInserted.connect(self.adjustColumnSizes)
        #self.mFlagModel.rowsRemoved.connect(self.adjustColumnSizes)
        self.mFlagModel.dataChanged.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsInserted.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsRemoved.connect(self.widgetChanged.emit)

        self.mTreeView.selectionModel().selectionChanged.connect(self.onSelectionChanged)

        #self.adjustColumnSizes()

        self.restoreTreeViewState()

        self.mLastBitFlagSchemeName = 'Bit Flag scheme'
        self.mNoDataColor = QColor(0, 0, 0, 0)

        self.actionAddParameter.triggered.connect(self.onAddParameter)
        self.actionRemoveParameters.triggered.connect(self.onRemoveParameters)
        self.actionLoadBitFlagScheme.triggered.connect(self.setBitFlagScheme)
        self.actionSaveBitFlagScheme.triggered.connect(self.saveBitFlagScheme)

        self.btnAddFlag.setDefaultAction(self.actionAddParameter)
        self.btnRemoveFlags.setDefaultAction(self.actionRemoveParameters)
        self.btnSaveBitFlagScheme.setDefaultAction(self.actionSaveBitFlagScheme)
        self.btnLoadBitFlagScheme.setDefaultAction(self.actionLoadBitFlagScheme)

        self.btnCombineFlags.setDefaultAction(self.actionCombineFlags)
        self.btnCombinedFlagsColor.setEnabled(self.actionCombineFlags.isChecked())
        self.actionCombineFlags.toggled.connect(self.btnCombinedFlagsColor.setEnabled)

        if True:
            self.btnCombineFlags.setVisible(False)
            self.btnCombinedFlagsColor.setVisible(False)

        self.updateWidgets()

    def saveBitFlagScheme(self):
        scheme = BitFlagScheme(self.mLastBitFlagSchemeName)
        scheme.mParameters.extend(self.mFlagModel.mFlagParameters)
        SaveFlagSchemeDialog.save(scheme)

    def adjustColumnSizes(self, *args):

        for i, c in enumerate(self.mFlagModel.mColumnNames):
            if c != self.mFlagModel.cnName:
                self.mTreeView.resizeColumnToContents(i)

    def setBitFlagScheme(self, scheme: BitFlagScheme = None, name: str = None):

        if not isinstance(scheme, BitFlagScheme):
            schemes = BitFlagScheme.loadAllSchemes()
            names = list(schemes.keys())

            if name is None:
                name, b = QInputDialog.getItem(self, 'Select Flag Scheme', 'Scheme', names, editable=False)
                if b:
                    scheme = schemes.get(name)

        if isinstance(scheme, BitFlagScheme):
            self.mLastBitFlagSchemeName = scheme.name()
            self.mNoDataColor = scheme.noDataColor()

            self.mFlagModel.beginResetModel()
            self.mFlagModel.mFlagParameters.clear()
            self.mFlagModel.mFlagParameters.extend(scheme.mParameters)
            self.mFlagModel.endResetModel()

            self.mTreeView.setUpdatesEnabled(False)
            for row in range(0, self.mProxyModel.rowCount()):
                idxP = self.mProxyModel.index(row, 0)
                idxS = self.mProxyModel.mapToSource(idxP)
                item = idxS.internalPointer()
                if isinstance(item, BitFlagParameter):
                    self.mTreeView.setExpanded(idxP, item.mIsExpanded)

            self.mTreeView.setUpdatesEnabled(True)
            #self.adjustColumnSizes()
            self.widgetChanged.emit()

    def bitFlagScheme(self) -> BitFlagScheme:

        scheme = BitFlagScheme(self.mLastBitFlagSchemeName)
        scheme.mNoDataColor = QColor(self.mNoDataColor)
        scheme.mParameters.extend(copy.copy(self.mFlagModel.mFlagParameters))
        return scheme

    def saveTreeViewState(self):

        rows = self.mProxyModel.rowCount()
        isExpanded = [self.treeView().isExpanded(self.mProxyModel.index(row, 0)) for row in range(rows)]
        gbIsCollapsed = self.mGroupBox.isCollapsed()
        columnWidths = [self.treeView().columnWidth(i) for i in range(self.treeView().model().columnCount())]
        state = {'state': self.treeView().state(),
                 'sortColumn': self.mProxyModel.sortColumn(),
                 'sortOrder': self.mProxyModel.sortOrder(),
                 'expandedPositions': isExpanded,
                 'columnWidths': columnWidths}

        settings().setValue(SettingsKeys.TreeViewState.value, pickle.dumps(state))

    def restoreTreeViewState(self):

        dump = settings().value(SettingsKeys.TreeViewState.value, None)
        if dump is not None:
            tv = self.treeView()
            # tv.blockSignals(True)
            try:

                d = pickle.loads(dump)
                assert isinstance(d, dict)
                self.treeView().setState(d['state'])
                self.mProxyModel.sort(d['sortColumn'], d['sortOrder'])

                expanded = d.get('expandedPositions', [])
                columnWidths = d.get('columnWidths', [])

                for row in range(min(len(expanded), self.mProxyModel.rowCount())):
                    idx = self.mProxyModel.index(row, 0)
                    tv.setExpanded(idx, expanded[row])

                for col in range(min(len(columnWidths), self.mProxyModel.columnCount())):
                    tv.setColumnWidth(col, columnWidths[col])

            except Exception as ex:
                s = ""

            # tv.blockSignals(False)

    def setRasterLayer(self, layer: QgsRasterLayer):
        super(BitFlagRendererWidget, self).setRasterLayer(layer)
        self.mRasterBandComboBox.setLayer(layer)
        if isinstance(layer, QgsRasterLayer):
            dt = layer.dataProvider().dataType(self.mRasterBandComboBox.currentBand())
            dtName = gdal.GetDataTypeName(dt)
            dtSize = gdal.GetDataTypeSize(dt)
            self.mRasterBandComboBox.setToolTip('{} bits ({}) '.format(dtSize, dtName))
            if layer.isValid() and isinstance(layer.renderer(), BitFlagRenderer):
                self.setBitFlagScheme(layer.renderer().bitFlagScheme())
                self.restoreTreeViewState()

        else:
            self.clear()

    def rasterLayer(self):
        self.saveTreeViewState()
        return super(BitFlagRendererWidget, self).rasterLayer()

    def onSelectionChanged(self, selected, deselected):
        self.updateWidgets()

    def selectedBand(self, index: int = 0):
        return self.mRasterBandComboBox.currentBand()

    def onAddParameter(self):

        startBit = self.mFlagModel.nextFreeBit()
        name = 'Parameter {}'.format(len(self.mFlagModel) + 1)

        flagParameter = BitFlagParameter(name, startBit, 1)
        self.mFlagModel.addFlagParameter(flagParameter)
        self.updateWidgets()

    def updateWidgets(self):
        b = len(self.treeView().selectionModel().selectedRows()) > 0
        self.actionRemoveParameters.setEnabled(b)

        b = self.mFlagModel.nextFreeBit() < self.layerBitCount()
        self.actionAddParameter.setEnabled(b)

    def renderer(self) -> QgsRasterRenderer:

        self.saveTreeViewState()

        r = BitFlagRenderer()
        r.setInput(self.rasterLayer().dataProvider())
        r.setBand(self.selectedBand())

        scheme = BitFlagScheme(self.mLastBitFlagSchemeName)
        parameters = []
        for row in range(self.mFlagModel.rowCount()):
            idxS = self.mFlagModel.index(row, 0)
            idxP = self.mProxyModel.mapFromSource(idxS)
            b = self.mTreeView.isExpanded(idxP)
            par = self.mFlagModel.data(idxS, role=Qt.UserRole)
            assert isinstance(par, BitFlagParameter)
            par.mIsExpanded = b
            par = copy.deepcopy(par)
            parameters.append(par)
        scheme.mParameters.extend(parameters)
        r.setBitFlagScheme(scheme)

        return r

    def onRemoveParameters(self):

        selectedRows = self.mTreeView.selectionModel().selectedRows()
        toRemove = []
        for idx in selectedRows:
            idx = self.mProxyModel.mapToSource(idx)
            parameter = self.mFlagModel.data(idx, Qt.UserRole)
            if isinstance(parameter, BitFlagParameter) and parameter not in toRemove:
                toRemove.append(parameter)
        for parameter in reversed(toRemove):
            self.mFlagModel.removeFlagParameter(parameter)

    def treeView(self) -> QTreeView:
        return self.mTreeView

    def layerBitCount(self) -> int:
        lyr = self.rasterLayer()
        if isinstance(lyr, QgsRasterLayer):
            return gdal.GetDataTypeSize(lyr.dataProvider().dataType(self.selectedBand()))
        else:
            return 0

    def clear(self):
        self.mRasterBandComboBox.setLayer(None)
        self.mRasterBandComboBox.setToolTip('')


class SaveFlagSchemeDialog(QDialog):

    @staticmethod
    def save(schema: BitFlagScheme):
        d = SaveFlagSchemeDialog(schema)
        if d.exec_() == QDialog.Accepted:
            schema = copy.deepcopy(schema)
            schema.setName(d.schemaName())
            schema.writeXMLFile(d.filePath())

    def __init__(self, schema: BitFlagScheme, parent=None):
        super(SaveFlagSchemeDialog, self).__init__(parent=parent)
        loadUi(PATH_UI_SAVE_FLAG_SCHEMA, self)
        assert isinstance(schema, BitFlagScheme)
        self.mSchema = copy.deepcopy(schema)

        self.wSchemeFilePath.setStorageMode(QgsFileWidget.SaveFile)
        filter = 'XML files (*.xml);;Any files (*)'
        self.wSchemeFilePath.setFilter(filter)
        root = DIR_BITFLAG_SCHEMES
        self.wSchemeFilePath.setDefaultRoot(root.as_posix())
        self.tbSchemaName.setText(schema.name())

        filePath = schema.name().encode().decode('ascii', 'replace').replace(u'\ufffd', '_')
        filePath = re.sub(r'[ ]', '_', filePath) + '.xml'
        filePath = root / filePath
        self.wSchemeFilePath.setFilePath(filePath.as_posix())

    def schemaName(self) -> str:
        return self.tbSchemaName.text()

    def schema(self) -> BitFlagScheme:
        return self.mSchema

    def filePath(self) -> str:
        """
        :return:
        :rtype:
        """
        return pathlib.Path(self.wSchemeFilePath.filePath()).as_posix()


class BitFlagRenderer(QgsSingleBandGrayRenderer):
    """
    A raster renderer to show flag states of a single byte/int/uint bands.
    Inherits from QgsSingleBandGrayRenderer to function with QGIS Core widgets that cannot handle new rasterrenderer
    that inherit QgsRasterRenderer directyl
    """

    def __init__(self, input=None):
        super(BitFlagRenderer, self).__init__(input, 1)

        self.mFlagScheme: BitFlagScheme
        self.mFlagScheme = BitFlagScheme()
        self.mBand = 1

    # def type(self)->str:
    #    return TYPE

    def writeXml(self, doc: QDomDocument, parentElem: QDomElement) -> None:
        super().writeXml(doc, parentElem)
        s = ""
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

    def usesBands(self) -> typing.List[int]:
        return [self.mBand]

    def legendSymbologyItems(self, *args, **kwargs):
        """ Overwritten from parent class. Items for the legend. """
        transparency = QColor(0, 255, 0, 0)
        items = [(self.bitFlagScheme().name(), transparency)]
        for parameter in self.bitFlagScheme().mParameters:
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

        output_block = QgsRasterBlock(Qgis.ARGB32_Premultiplied, width, height)
        color_array = np.frombuffer(output_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[output_block.dataType()])
        color_array[:] = scheme.noDataColor().rgba()

        if len(self.bitFlagScheme()) == 0:
            output_block.setData(color_array.tobytes())
            return output_block

        npx = height * width

        band_block = self.input().block(self.mBand, extent, width, height)
        assert isinstance(band_block, QgsRasterBlock)
        band_data = np.frombuffer(band_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[band_block.dataType()])
        assert len(band_data) == npx
        # THIS! seems to be a very fast way to convert block data into a numpy array
        # block_data[b, :] = band_data

        parameterNumbers = np.zeros(band_data.shape, dtype=np.uint8)
        for i, flagParameter in enumerate(sorted(self.bitFlagScheme(), key=lambda fp: (fp.zValue(), fp.firstBit()))):
            b0 = flagParameter.firstBit()

            # extract the parameter number
            for b in range(flagParameter.bitCount()):
                mask = 1 << (flagParameter.firstBit() + b)
                parameterNumbers += 2 ** b * np.uint8((band_data & mask) != 0)

            # compare each flag state
            for j, flagState in enumerate(flagParameter):
                if not flagState.isVisible():
                    continue
                color_array[np.where(parameterNumbers == flagState.bitNumber())[0]] = flagState.color().rgb()

            parameterNumbers.fill(0)
        output_block.setData(color_array.tobytes())
        return output_block

    def clone(self) -> QgsRasterRenderer:
        """ Overwritten from parent class. """
        r = BitFlagRenderer()
        scheme = copy.deepcopy(self.bitFlagScheme())
        r.setBitFlagScheme(scheme)

        return r

    def type(self) -> str:
        return 'bitflagrenderer'


class BitFlagLayerConfigWidget(QgsMapLayerConfigWidget):

    def __init__(self, layer: QgsRasterLayer, canvas: QgsMapCanvas, parent: QWidget = None):

        super(BitFlagLayerConfigWidget, self).__init__(layer, canvas, parent=parent)

        self.setLayout(QVBoxLayout())
        self.setPanelTitle('Flag Layer Settings')
        self.mCanvas = canvas
        self.mLayer = layer
        self.mRenderWidget: BitFlagRendererWidget
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            ext = layer.extent()
        else:
            ext = QgsRectangle()

        self.mIsInDockMode = False
        self.mRenderWidget = BitFlagRendererWidget(layer, ext)
        self.mRenderWidget.widgetChanged.connect(self.apply)
        self.layout().addWidget(self.mRenderWidget)

    def shouldTriggerLayerRepaint(self):
        return True

    def renderer(self) -> QgsRasterRenderer:
        return self.mRenderWidget.renderer()

    def apply(self):
        r = self.renderer()

        if isinstance(r, QgsRasterRenderer):
            self.mLayer.setRenderer(r)
            self.mLayer.triggerRepaint()

    def setDockMode(self, dockMode: bool):
        print('SET DOCKMODE CALLED')
        self.mIsInDockMode = dockMode
        super(BitFlagLayerConfigWidget, self).setDockMode(dockMode)


class BitFlagLayerConfigWidgetFactory(QgsMapLayerConfigWidgetFactory):

    def __init__(self):

        super(BitFlagLayerConfigWidgetFactory, self).__init__('Flags', QIcon(PATH_ICON))
        self.setSupportLayerPropertiesDialog(True)
        self.setSupportsStyleDock(True)
        self.setTitle('Flag Raster Renderer')
        self.mWidget = None
        self.mIcon = QIcon(PATH_ICON)

    def supportsLayer(self, layer):
        b = False
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            dt = layer.dataProvider().dataType(1)
            b = dt in [gdal.GDT_Byte, gdal.GDT_Int16, gdal.GDT_Int32, gdal.GDT_UInt16, gdal.GDT_UInt32, gdal.GDT_CInt16,
                       gdal.GDT_CInt32]

            if not b:
                print(dt)

        if b is False:
            print('Unsupported: {}'.format(layer))
        return b

    def icon(self) -> QIcon:
        return self.mIcon

    def supportLayerPropertiesDialog(self):
        return True

    def supportsStyleDock(self):
        return True

    def createWidget(self, layer, canvas, dockWidget=True, parent=None) -> QgsMapLayerConfigWidget:
        return BitFlagLayerConfigWidget(layer, canvas, parent=parent)


def registerConfigWidgetFactory():
    global FACTORY
    if not isinstance(FACTORY, BitFlagLayerConfigWidgetFactory):
        FACTORY = BitFlagLayerConfigWidgetFactory()
        qgis.utils.iface.registerMapLayerConfigWidgetFactory(FACTORY)

def unregisterConfigWidgetFactory():
    global FACTORY
    if isinstance(FACTORY, BitFlagLayerConfigWidgetFactory):
        qgis.utils.iface.unregisterMapLayerConfigWidgetFactory(FACTORY)
        FACTORY = None
