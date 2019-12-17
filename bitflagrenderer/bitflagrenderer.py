import sys, os, re, pathlib, pickle, typing, enum, copy, bisect, io
from qgis.core import *
from qgis.gui import *
import qgis.utils
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtXml import *
from qgis.PyQt.uic import loadUiType
from osgeo import gdal
import numpy as np
PATH_UI = os.path.join(os.path.dirname(__file__), 'bitflagrenderer.ui')
PATH_ICON = os.path.join(os.path.dirname(__file__), 'bitflagimage.png')
assert os.path.isfile(PATH_ICON)

FACTORY = None
TYPE = 'BitFlagRenderer'

QGIS2NUMPY_DATA_TYPES = {Qgis.Byte: np.byte,
                         Qgis.UInt16: np.uint16,
                         Qgis.Int16: np.int16,
                         Qgis.UInt32: np.uint32,
                         Qgis.Int32: np.int32,
                         Qgis.Float32: np.float32,
                         Qgis.Float64: np.float64,
                         Qgis.CFloat32: np.complex,
                         Qgis.CFloat64: np.complex64,
                         Qgis.ARGB32: np.uint32,
                         Qgis.ARGB32_Premultiplied: np.uint32}

MAX_BITS_PER_PARAMETER = 4

NEXT_COLOR_HUE_DELTA_CON = 10
NEXT_COLOR_HUE_DELTA_CAT = 100


def loadFormClass(pathUi: str):
    """
    Loads Qt UI files (*.ui) while taking care on QgsCustomWidgets.
    Uses PyQt4.uic.loadUiType (see http://pyqt.sourceforge.net/Docs/PyQt4/designer.html#the-uic-module)
    """
    REMOVE_setShortcutVisibleInContextMenu = True

    assert os.path.isfile(pathUi), '*.ui file does not exist: {}'.format(pathUi)

    with open(pathUi, 'r', encoding='utf-8') as f:
        txt = f.read()
    doc = QDomDocument()
    doc.setContent(txt)

    toRemove = []
    if REMOVE_setShortcutVisibleInContextMenu and 'shortcutVisibleInContextMenu' in txt:

        actions = doc.elementsByTagName('action')
        for iAction in range(actions.count()):
            properties = actions.item(iAction).toElement().elementsByTagName('property')
            for iProperty in range(properties.count()):
                prop = properties.item(iProperty).toElement()
                if prop.attribute('name') == 'shortcutVisibleInContextMenu':
                    toRemove.append(prop)

    elem = doc.elementsByTagName('customwidget')
    for child in [elem.item(i) for i in range(elem.count())]:
        child = child.toElement()

        cClass = child.firstChildElement('class').firstChild()
        cHeader = child.firstChildElement('header').firstChild()
        cExtends = child.firstChildElement('extends').firstChild()

        sClass = str(cClass.nodeValue())
        sExtends = str(cHeader.nodeValue())

        if sClass.startswith('Qgs'):
            cHeader.setNodeValue('qgis.gui')

        # collect resource file locations
        includes = doc.elementsByTagName('include')
        for i in range(includes.count()):
            node = includes.item(i).toElement()
            toRemove.append(node)

    for prop in toRemove:
        prop.parentNode().removeChild(prop)
    del toRemove

    buffer = io.StringIO()  # buffer to store modified XML
    buffer.write(doc.toString())
    buffer.flush()
    buffer.seek(0)

    # load form class
    FORM_CLASS, _ = loadUiType(buffer, resource_suffix='')
    buffer.close()
    # remove temporary added directories from python path

    return FORM_CLASS


def nextColor(color, mode='cat')->QColor:
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


def contrastColor(c:QColor)->QColor:
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

class BitFlagState(object):

    def __init__(self, offset:int, number:int, name:str=None, color:QColor=None):

        self.mBitShift:int
        self.mBitShift = offset
        self.mNumber: int
        assert isinstance(number, int) and number >= 0
        self.mNumber = number

        self.mName:str
        if name is None:
            name = 'state {}'.format(number+1)
        self.mName = name

        if color is None:
            color = QColor('blue')
            for i in range(number):
                color = nextColor(color, mode='cat')

        self.mColor:QColor
        self.mColor = color

        self.mVisible:bool
        self.mVisible = True

    def __len__(self):
        return 0

    def bitCombination(self, nbits=1)->str:
        f = '{:0'+str(nbits)+'b}'
        return f.format(self.mNumber)

    def bitNumber(self)->str:
        return self.mNumber

    def name(self)->str:
        return self.mName

    def setValues(self, name:str=None, color=None, isVisible:bool=None):

        if isinstance(name, str):
            self.setName(name)
        if color is not None:
            self.setColor(color)
        if isinstance(isVisible, bool):
            self.setVisible(isVisible)

    def setName(self, name:str):
        assert isinstance(name, str)
        self.mName = name

    def isVisible(self)->bool:
        return self.mVisible

    def setVisible(self, b:bool):
        assert isinstance(b, bool)
        self.mVisible = b

    def color(self)->QColor:
        return self.mColor

    def setColor(self, color):
        self.mColor = QColor(color)

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



class BitFlagParameter(object):
    """
    A class to define possible states of a flag / flag-set
    """

    def __init__(self, name:str, firstBit:int, bitCount:int=1):
        assert isinstance(name, str)
        assert isinstance(firstBit, int) and firstBit >= 0
        assert isinstance(bitCount, int) and bitCount >= 1 and bitCount <= 128 # this should be enough

        # initialize the parameter states
        self.mName = name
        self.mStartBit = firstBit
        self.mBitSize = bitCount
        self.mFlagStates = list()

        self.mIsExpanded : bool
        self.mIsExpanded = True

        color0 = QColor('black')
        for i in range(firstBit + 1):
            color0 = nextColor(color0, 'cat')
        color = QColor(color0)

        for i in range(2 ** bitCount):
            color = nextColor(color, 'con')
            state = BitFlagState(self.mStartBit, i, name, color=color)
            self.mFlagStates.append(state)

    def __eq__(self, other):
        if not isinstance(other, BitFlagParameter):
            return None
        if not len(other) == len(self) and self.name() == other.name() and self.mStartBit == other.mStartBit and self.mBitSize == other.mBitSize:
            return False
        for s1, s2 in zip(self.mFlagStates, other.mFlagStates):
            if not s1 == s2:
                return False

        return True



    def __contains__(self, item):
        return item in self.mFlagStates

    def __getitem__(self, slice):
        return self.mFlagStates[slice]

    def __iter__(self)->typing.Iterator[BitFlagState]:
        return iter(self.mFlagStates)

    def bitCount(self)->int:
        return self.mBitSize

    def setFirstBit(self, firstBit:int):
        assert isinstance(firstBit, int) and firstBit >= 0
        self.mStartBit = firstBit
        for state in self.states():
            state.mBitShift = self.mStartBit

    def __len__(self):
        return len(self.mFlagStates)

    def __lt__(self, other):
        assert isinstance(other, BitFlagParameter)
        return self.mStartBit < other.mStartBit

    def __repr__(self)->str:
        info = '{}:{}bits:"{}"'.format(self.mStartBit, self.mBitSize, self.mName)
        return info

    def setBitSize(self, bitSize:int):
        assert isinstance(bitSize, int) and bitSize >= 1
        nStates0 = 2 ** self.mBitSize
        nStates2 = 2 ** bitSize
        n = len(self.mFlagStates)
        self.mBitSize = bitSize
        diff = 2**bitSize - n
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

    def states(self)->typing.List[BitFlagState]:
        return self.mFlagStates

    def visibleStates(self)->typing.List[BitFlagState]:
        return [state for state in self.mFlagStates if state.isVisible()]

    def name(self)->str:
        return self.mName

    def setName(self, name:str):
        assert isinstance(name, str)
        self.mName = name

    def firstBit(self)->int:
        return self.mStartBit

    def lastBit(self)->int:
        """
        Returns the last bit affected by this FlagState
        :return:
        :rtype:
        """
        return self.mStartBit + self.mBitSize - 1





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

    def columnNames(self):
        return [self.cnBitPosition, self.cnName, self.cnBitComb, self.cnBitNum, self.cnColor]

    def __contains__(self, item):
        return item in self.mFlagParameters

    def __getitem__(self, slice):
        return self.mFlagParameters[slice]


    def __len__(self):
        return len(self.mFlagParameters)

    def __iter__(self)->typing.Iterator[BitFlagParameter]:
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
        return len(self.columnNames())

    def addFlagParameter(self, flagParameter:BitFlagParameter):
        row = bisect.bisect(self.mFlagParameters, flagParameter)
        self.beginInsertRows(self.mRootIndex, row, row)
        self.mFlagParameters.insert(row, flagParameter)
        self.endInsertRows()

    def removeFlagParameter(self, flagParameter:BitFlagParameter):
        if flagParameter in self.mFlagParameters:
            row = self.mFlagParameters.index(flagParameter)
            self.beginRemoveRows(self.mRootIndex, row, row)
            self.mFlagParameters.remove(flagParameter)
            self.endRemoveRows()

    def headerData(self, section, orientation, role):
        assert isinstance(section, int)

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columnNames()[section]

        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return section

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        cName = self.columnNames()[index.column()]

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if isinstance(index.internalPointer(), (BitFlagParameter, BitFlagState)) and index.column() == 0:
            flags = flags | Qt.ItemIsUserCheckable

        if cName in [self.cnName, self.cnColor]:
            flags = flags | Qt.ItemIsEditable

        if cName == self.cnBitPosition and isinstance(index.internalPointer(), BitFlagParameter):
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

    def nextFreeBit(self)->int:
        if len(self) == 0:
            return 0
        else:
            lastParameter = self[-1]
            return lastParameter.lastBit()+1

    def index(self, row: int, column: int, parent: QModelIndex=QModelIndex()) -> QModelIndex:

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
        cName = self.columnNames()[index.column()]
        if isinstance(item, BitFlagParameter):

            if role in [Qt.DisplayRole, Qt.EditRole]:
                if cName == self.cnBitPosition:
                    if item.bitCount() == 1:
                        return '{}'.format(item.firstBit())
                    else:
                        return '{}-{}'.format(item.firstBit(), item.lastBit())
                if cName == self.cnName:
                    return item.name()

            if role == Qt.ToolTipRole:
                if cName == self.cnName:
                    return item.name()

            if role == Qt.CheckStateRole and index.column() == 0:
                nStates = len(item)
                nChecked = len(item.visibleStates())
                if nChecked == 0:
                    return Qt.Unchecked
                elif nChecked < nStates:
                    return Qt.PartiallyChecked
                else:
                    return Qt.Checked

            if role == Qt.UserRole:
                return item

        if isinstance(item, BitFlagState):

            if role in [Qt.DisplayRole, Qt.EditRole]:
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
        cName = self.columnNames()[index.column()]

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
                        stateIndex = self.index(row, 0, index)
                        if self.data(stateIndex, Qt.CheckStateRole) != value:
                            self.setData(stateIndex, value, Qt.CheckStateRole)
                            result = True


            if role == Qt.EditRole:
                if cName == self.cnName:
                    item.setName(str(value))
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
                        bitSize = bit2-bit1+1

                    if isinstance(bit1, int) and isinstance(bitSize, int) and bitSize > 0:
                        bitSize = min(bitSize, MAX_BITS_PER_PARAMETER)
                        item.setFirstBit(bit1)
                        n1 = len(item)
                        n2 = 2**bitSize
                        diff = n2 - n1
                        if diff < 0:
                            self.beginRemoveRows(index, n2, n1-1)
                            item.setBitSize(bitSize)
                            self.endRemoveRows()
                        elif diff > 0:
                            self.beginInsertRows(index, n1, n2-1)
                            item.setBitSize(bitSize)
                            self.endInsertRows()
                        result = True



        if result == True:
            self.dataChanged.emit(index, index, [role])

        return result

    def clear(self):

        n = self.rowCount()
        self.beginRemoveRows(QModelIndex(), 0, n-1)
        self.mFlagParameters.clear()
        self.endRemoveRows()



class BitFlagRendererWidget(QgsRasterRendererWidget, loadFormClass(PATH_UI)):

    def __init__(self, layer:QgsRasterLayer, extent:QgsRectangle):
        super(BitFlagRendererWidget, self).__init__(layer, extent)
        self.setupUi(self)
        self.mRasterBandComboBox.setShowNotSetOption(False)

        assert isinstance(self.mTreeView, QTreeView)



        self.mFlagModel:BitFlagModel
        self.mFlagModel = BitFlagModel()
        self.mProxyModel = QSortFilterProxyModel()
        self.mProxyModel.setSourceModel(self.mFlagModel)
        self.mTreeView.setModel(self.mProxyModel)

        self.setRasterLayer(layer)

        self.mFlagModel.dataChanged.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsInserted.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsRemoved.connect(self.widgetChanged.emit)

        self.mTreeView.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        self.mTreeView.doubleClicked.connect(self.onTreeViewDoubleClick)
        self.mTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.actionAddParameter.triggered.connect(self.onAddParameter)
        self.actionRemoveParameters.triggered.connect(self.onRemoveParameters)
        self.btnAddFlag.setDefaultAction(self.actionAddParameter)
        self.btnRemoveFlags.setDefaultAction(self.actionRemoveParameters)

        self.updateWidgets()


    def onTreeViewDoubleClick(self, idx):
        idx = self.mProxyModel.mapToSource(idx)
        item = idx.internalPointer()
        cname = self.mFlagModel.columnNames()[idx.column()]
        if isinstance(item, BitFlagState) and cname == self.mFlagModel.cnColor:
            c = QColorDialog.getColor(item.color(), self.treeView(), \
                                      'Set color for "{}"'.format(item.name()))

            self.mFlagModel.setData(idx, c, role=Qt.EditRole)

    def setRasterLayer(self, layer:QgsRasterLayer):
        super(BitFlagRendererWidget, self).setRasterLayer(layer)
        self.mRasterBandComboBox.setLayer(layer)

        if layer.isValid() and isinstance(layer.renderer(), BitFlagRenderer):

            self.mFlagModel.beginResetModel()
            self.mFlagModel.mFlagParameters.clear()
            self.mFlagModel.mFlagParameters.extend(layer.renderer().flagParameters())
            self.mFlagModel.endResetModel()

            self.mTreeView.setUpdatesEnabled(False)
            for row in range(0, self.mProxyModel.rowCount()):
                idxP = self.mProxyModel.index(row, 0)
                idxS = self.mProxyModel.mapToSource(idxP)
                item = idxS.internalPointer()
                if isinstance(item, BitFlagParameter):
                    self.mTreeView.setExpanded(idxP, item.mIsExpanded)

            self.mTreeView.setUpdatesEnabled(True)

    def onSelectionChanged(self, selected, deselected):
        self.updateWidgets()

    def selectedBand(self, index:int=0):
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




    def renderer(self)->QgsRasterRenderer:

        r = BitFlagRenderer()
        r.setInput(self.rasterLayer().dataProvider())
        r.setBand(self.selectedBand())

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

        r.setFlagParameters(parameters)

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


    def treeView(self)->QTreeView:
        return self.mTreeView

    def layerBitCount(self)->int:
        lyr = self.rasterLayer()
        if isinstance(lyr, QgsRasterLayer):
            return gdal.GetDataTypeSize(lyr.dataProvider().dataType(self.selectedBand()))
        else:
            return 0

    def setLayer(self, rasterLayer:QgsRasterLayer):
        if isinstance(rasterLayer, QgsRasterLayer):
            self.mRasterBandComboBox.setLayer(rasterLayer)
            dt = rasterLayer.dataProvider().dataType(self.mRasterBandComboBox.currentBand())
            dtName = gdal.GetDataTypeName(dt)
            dtSize = gdal.GetDataTypeSize(dt)
            self.mRasterBandComboBox.setToolTip('{} bits ({}) '.format(dtSize, dtName))
        else:
            self.clear()

    def clear(self):
        self.mRasterBandComboBox.setLayer(None)
        self.mRasterBandComboBox.setToolTip('')




class BitFlagRenderer(QgsRasterRenderer):
    """ A raster renderer to show flag states of a single band. """

    def __init__(self, input=None, type=TYPE):
        super(BitFlagRenderer, self).__init__(input=input, type=type)

        self.mFlagParameters:typing.List[BitFlagParameter]
        self.mFlagParameters = []
        self.mNoDataColor = QColor(0, 255, 0, 0)
        self.mBand = 1

    def type(self)->str:
        return TYPE

    def setBand(self, band:int):
        self.mBand = band

    def setFlagParameters(self, flagParameters:typing.List[BitFlagParameter]):
        self.mFlagParameters.clear()
        self.mFlagParameters.extend(flagParameters)

    def flagParameters(self)->typing.List[BitFlagParameter]:
        return self.mFlagParameters[:]

    def __reduce_ex__(self, protocol):
        return self.__class__, (), self.__getstate__()

    def __getstate__(self):
        dump = pickle.dumps(self.__dict__)
        return dump

    def __setstate__(self, state):
        d = pickle.loads(state)
        self.__dict__.update(d)

    def usesBands(self)->typing.List[int]:
        return [self.mBand]

    def writeXml(self, doc:QDomDocument, parentElem:QDomElement):

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


    def readXml(self, rendererElem:QDomElement):

        pass


    def legendSymbologyItems(self, *args, **kwargs):
        """ Overwritten from parent class. Items for the legend. """
        items = []
        for parameter in self.flagParameters():
            b0 = parameter.firstBit()
            b1 = parameter.lastBit()
            if b0 == b1:
                bitPos = '{}'.format(b0)
            else:
                bitPos = '{}-{}'.format(b0, b1)


            for flagState in parameter:
                assert isinstance(flagState, BitFlagState)

                if flagState.isVisible():
                    item = ('Bit {}:{}:{}'.format(bitPos, flagState.bitNumber(), flagState.name()), flagState.color())
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

        output_block = QgsRasterBlock(Qgis.ARGB32_Premultiplied, width, height)
        color_array = np.frombuffer(output_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[output_block.dataType()])
        color_array[:] = self.mNoDataColor.rgba()

        if len(self.mFlagParameters) == 0:
            print(input_missmatch, file=sys.stderr)
            output_block.setData(color_array.tobytes())
            return output_block

        npx = height * width


        band_block = self.input().block(self.mBand, extent, width, height)
        assert isinstance(band_block, QgsRasterBlock)
        band_data = np.frombuffer(band_block.data(), dtype=QGIS2NUMPY_DATA_TYPES[band_block.dataType()])
        assert len(band_data) == npx
        # THIS! seems to be a very fast way to convert block data into a numpy array
        #block_data[b, :] = band_data

        parameterNumbers = np.zeros(band_data.shape, dtype=np.uint8)
        for i, flagParameter in enumerate(self.mFlagParameters):
            b0 = flagParameter.firstBit()

            # extract the parameter number
            for b in range(flagParameter.bitCount()):
                mask = 1 << (flagParameter.firstBit() + b)
                parameterNumbers += 2**b * np.uint8((band_data & mask) != 0)

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
        parameters = [copy.copy(par) for par in self.mFlagParameters]
        r.setFlagParameters(parameters)

        return r


class BitFlagLayerConfigWidget(QgsMapLayerConfigWidget):

    def __init__(self, layer:QgsRasterLayer, canvas:QgsMapCanvas, parent:QWidget=None):

        super(BitFlagLayerConfigWidget, self).__init__(layer, canvas, parent=parent)

        self.setLayout(QVBoxLayout())
        self.setPanelTitle('Flag Layer Settings')
        self.mCanvas = canvas
        self.mLayer = layer
        self.mRenderWidget : BitFlagRendererWidget
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

    def renderer(self)->QgsRasterRenderer:
        return self.mRenderWidget.renderer()

    def apply(self):
        r = self.renderer()

        if isinstance(r, QgsRasterRenderer):
            self.mLayer.setRenderer(r)
            self.mLayer.triggerRepaint()

    def setDockMode(self, dockMode:bool):
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
            b = dt in [gdal.GDT_Byte, gdal.GDT_Int16, gdal.GDT_Int32, gdal.GDT_UInt16, gdal.GDT_UInt32, gdal.GDT_CInt16, gdal.GDT_CInt32]

            if not b:
                print(dt)

        if b is False:
            print('Unsupported: {}'.format(layer))
        return b

    def icon(self)->QIcon:
        return self.mIcon

    def supportLayerPropertiesDialog(self):
        return True

    def supportsStyleDock(self):
        return True


    def createWidget(self, layer, canvas, dockWidget=True, parent=None)->QgsMapLayerConfigWidget:
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