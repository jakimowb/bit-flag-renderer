import copy
import pickle

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QTreeView, QHeaderView, QInputDialog
from osgeo import gdal
from qgis.gui import QgsRasterRendererWidget

from qgis.core import QgsRasterLayer, QgsRectangle, QgsRasterRenderer

from bitflagrenderer import settings, SettingsKeys, PATH_UI
from bitflagrenderer.core.utils import loadUi
from bitflagrenderer.gui.saveflagschemedialog import SaveFlagSchemeDialog
from bitflagrenderer.core.bitflagscheme import BitFlagScheme, BitFlagParameter
from bitflagrenderer.core.bitflagmodel import BitFlagModel, BitFlagSortFilterProxyModel
from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer


class BitFlagRasterRendererWidget(QgsRasterRendererWidget):

    def __init__(self, layer: QgsRasterLayer, extent: QgsRectangle):
        super(BitFlagRasterRendererWidget, self).__init__(layer, extent)
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

        #  self.mFlagModel.rowsInserted.connect(self.adjustColumnSizes)
        #  self.mFlagModel.rowsRemoved.connect(self.adjustColumnSizes)
        self.mFlagModel.dataChanged.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsInserted.connect(self.widgetChanged.emit)
        self.mFlagModel.rowsRemoved.connect(self.widgetChanged.emit)

        self.mTreeView.selectionModel().selectionChanged.connect(self.onSelectionChanged)

        #  self.adjustColumnSizes()

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
            #  self.adjustColumnSizes()
            self.widgetChanged.emit()

    def bitFlagScheme(self) -> BitFlagScheme:

        scheme = BitFlagScheme(self.mLastBitFlagSchemeName)
        scheme.mNoDataColor = QColor(self.mNoDataColor)
        scheme.mParameters.extend(copy.copy(self.mFlagModel.mFlagParameters))
        return scheme

    def saveTreeViewState(self):

        rows = self.mProxyModel.rowCount()
        isExpanded = [self.treeView().isExpanded(self.mProxyModel.index(row, 0)) for row in range(rows)]
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
        super(BitFlagRasterRendererWidget, self).setRasterLayer(layer)
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
        return super(BitFlagRasterRendererWidget, self).rasterLayer()

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
