import re
from typing import List, Iterator, Any, Union

from bitflagrenderer import MAX_BITS_PER_PARAMETER
from bitflagrenderer.core.bitflagscheme import BitFlagParameter, BitFlagState
from bitflagrenderer.core.utils import contrastColor
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from qgis.PyQt.QtCore import QMimeData, pyqtSignal
from qgis.PyQt.QtGui import QColor


class BitFlagModel(QAbstractItemModel):
    combinedFlagsColorChanged = pyqtSignal(QColor)

    def __init__(self, *args, **kwds):
        super(BitFlagModel, self).__init__(*args, **kwds)
        self.mFlagParameters = []

        self.mCombineFlags: bool = False
        self.mCombinedFlagsColor: QColor = QColor('blue')

        self.cnBitPosition = 'Bit No.'
        self.cnName = 'Name'
        self.cnBitComb = 'Bits'
        self.cnBitNum = 'Num'
        self.cnColor = 'Color'

        self.mRootIndex = QModelIndex()

        self.mColumnNames: List[str] = [self.cnBitPosition, self.cnName, self.cnBitComb, self.cnBitNum, self.cnColor]

        self.mColumnToolTips: List[str] = [
            'The Flag Parameters bit position(s), e.g. "0" or "1-2"',
            'Name of flag parameter or its different flag states',
            'Flag state bit combination',
            "Flag state  of bit combination within a Flag statess possible bit combinations",
            "Flag State Color"
        ]

    def setCombineFlags(self, b: bool):

        if self.mCombineFlags != b:
            # this changes all colors
            self.mCombineFlags = b
            self._updateColors()

    def _updateColors(self):
        c = self.columnNames().index(self.cnColor)
        for p in self.mFlagParameters:
            idx = self.parameter2index(p)
            for r in range(self.rowCount(idx)):
                idx2 = self.index(r, c, idx)
                self.dataChanged.emit(idx2, idx2)

    def combineFlags(self) -> bool:
        return self.mCombineFlags

    def setCombinedFlagsColor(self, c: Union[QColor, str]):

        c = QColor(c)
        if c != self.mCombinedFlagsColor:
            self.mCombinedFlagsColor = c
            self._updateColors()
            self.combinedFlagsColorChanged.emit(c)

    def combinedFlagsColor(self) -> QColor:
        return self.mCombinedFlagsColor

    def columnNames(self) -> List[str]:
        return self.mColumnNames

    def __contains__(self, item):
        return item in self.mFlagParameters

    def __getitem__(self, slice):
        return self.mFlagParameters[slice]

    def __len__(self):
        return len(self.mFlagParameters)

    def __iter__(self) -> Iterator[BitFlagParameter]:
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
                line = '  {}:{}'.format(state.bitCombination(), state.mNumber)
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

    def addFlagParameter(self, flagParameter: BitFlagParameter) -> bool:
        row = len(self.mFlagParameters)
        if flagParameter not in self.mFlagParameters:
            self.beginInsertRows(self.mRootIndex, row, row)
            self.mFlagParameters.insert(row, flagParameter)
            self.endInsertRows()
            return True
        else:
            return False

    def supportedDragActions(self):
        return Qt.MoveAction  # | Qt.CopyAction

    def supportedDropActions(self):
        return Qt.MoveAction  # | Qt.CopyAction

    def canDropMimeData(self, mimeData: QMimeData, action: Qt.DropAction, row, column, index: QModelIndex):

        if action not in [Qt.MoveAction, Qt.CopyAction, Qt.IgnoreAction]:
            return False

        # print((index.row(), index.column(), index.internalPointer(), index == self.mRootIndex))
        return index == self.mRootIndex

    def dropMimeData(self, mimeData: QMimeData, action: Qt.DropAction, row, column, index: QModelIndex):

        if action == Qt.IgnoreAction:
            return True

        parameters = BitFlagParameter.fromMimeData(mimeData)

        if index != self.mRootIndex:
            return False

        if len(parameters) > 0:
            self.beginInsertRows(index, row, row + len(parameters) - 1)
            for p in reversed(parameters):
                self.mFlagParameters.insert(row, p)
            self.endInsertRows()

            return True
        else:
            return False

    def mimeData(self, indices: List[QModelIndex]) -> QMimeData:

        parameters = []
        for idx in indices:
            p: BitFlagParameter = self.data(idx, Qt.UserRole)
            assert isinstance(p, BitFlagParameter)
            if p not in parameters:
                parameters.append(p)
        return BitFlagParameter.mimeData(parameters)

    def insertRows(self, *args, **kwds):

        s = ""

    def removeRows(self, row: int, count: int, index: QModelIndex) -> bool:

        if index == self.mRootIndex:
            self.beginRemoveRows(index, row, row + count - 1)
            while count > 0:
                del self.mFlagParameters[row]
                count -= 1
            self.endRemoveRows()
            return True
        return False

    def moveRows(self, *args, **kwds):
        s = ""
        return False

    def removeFlagParameter(self, flagParameter: BitFlagParameter) -> bool:
        if flagParameter in self.mFlagParameters:
            row = self.mFlagParameters.index(flagParameter)
            return self.removeRows(row, 1, self.mRootIndex)
        else:
            return False

    def parameter2index(self, parameter: BitFlagParameter) -> QModelIndex:
        assert parameter in self.mFlagParameters
        r = self.mFlagParameters.index(parameter)
        return self.createIndex(r, 0, parameter)

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
        if index == self.mRootIndex:
            return Qt.ItemIsDropEnabled
        if not index.isValid():
            return Qt.NoItemFlags

        cName = self.mColumnNames[index.column()]

        item = index.internalPointer()

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if isinstance(item, (BitFlagParameter, BitFlagState)) and index.column() == 0:
            flags = flags | Qt.ItemIsUserCheckable

        if cName == self.cnName:
            flags = flags | Qt.ItemIsEditable

        if isinstance(item, BitFlagParameter):
            flags = flags | Qt.ItemIsDragEnabled  # | Qt.ItemIsDropEnabled

            if cName in [self.cnBitPosition]:
                flags = flags | Qt.ItemIsEditable

        if index == self.mRootIndex:
            flags = flags | Qt.ItemIsDropEnabled
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
            if row < len(flagParameter):
                return self.createIndex(row, column, flagParameter[row])
            else:
                return self.createIndex(row, column)
        return QModelIndex()

    def data(self, index: QModelIndex, role: int) -> Any:
        assert isinstance(index, QModelIndex)
        if not index.isValid():
            return None

        item = index.internalPointer()
        cName = self.mColumnNames[index.column()]

        cColor: QColor = self.combinedFlagsColor()
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
                if cName == self.cnColor:
                    return 'Flag color'
                if cName == self.cnBitPosition:
                    return 'Bit position'

                if cName == self.cnBitComb:
                    return 'Parameter bits'

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
                #  if cName == self.cnBitPosition:
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
                    color = cColor if self.mCombineFlags else item.color()
                    return color.name(QColor.HexArgb)

            if role == Qt.BackgroundColorRole:
                if cName == self.cnColor:
                    color = cColor if self.mCombineFlags else item.color()
                    return color

            if role == Qt.TextColorRole:
                if cName == self.cnColor:
                    color = cColor if self.mCombineFlags else item.color()
                    return contrastColor(color)

            if role == Qt.TextAlignmentRole:
                if cName in [self.cnBitNum, self.cnBitComb]:
                    return Qt.AlignRight

            if role == Qt.CheckStateRole and index.column() == 0:
                return Qt.Checked if item.isVisible() else Qt.Unchecked

            if role == Qt.UserRole:
                return item

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:

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
                    color = QColor(value)
                    if self.combineFlags():
                        self.setCombinedFlagsColor(color)
                    else:
                        item.setColor(color)
                        result = True

        if isinstance(item, BitFlagParameter):
            if role == Qt.CheckStateRole and index.column() == 0:
                if value in [Qt.Checked, Qt.Unchecked]:
                    # apply new check state downwards to all FlagStates
                    for row in range(len(item)):
                        # if row == 0:  # row 0 = empty flag -> consider higher values only
                        #    pass  # continue
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

        if result is True:
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
