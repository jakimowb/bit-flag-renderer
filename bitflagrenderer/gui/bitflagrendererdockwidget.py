from pathlib import Path
from typing import Dict, Tuple

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QMimeData, pyqtSignal
from qgis.PyQt.QtGui import QClipboard
from qgis.PyQt.QtWidgets import QHeaderView, QTreeView, QApplication, QAction
from osgeo import gdal

from bitflagrenderer.core.bitflagmodel import BitFlagModel, BitFlagSortFilterProxyModel
from bitflagrenderer.core.bitflagscheme import BitFlagParameter, BitFlagScheme
from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer
from bitflagrenderer.gui.bitflagrenderertreeview import BitFlagRendererTreeView

from qgis.core import Qgis
from qgis.core import QgsMapLayerProxyModel, QgsProject, QgsMapLayer, QgsRasterLayer
from qgis.gui import QgsDockWidget, QgsMapLayerComboBox, QgsRasterBandComboBox


class BitFlagRendererDockWidget(QgsDockWidget):
    bitFlagSchemeChanged = pyqtSignal()

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        pathUi = Path(__file__).parent / "bitflagrendererdockwidget.ui"
        with open(pathUi.as_posix()) as uifile:
            uic.loadUi(uifile, baseinstance=self)

        self.cbLayer: QgsMapLayerComboBox
        self.cbLayer.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.cbLayer.setAllowEmptyLayer(True)
        self.cbBand: QgsRasterBandComboBox
        self.mProject: QgsProject = None
        self.cbLayer.layerChanged.connect(self.setLayer)
        self.btnMapTool.setVisible(False)
        self.mSchemeCache: Dict[Tuple[str, int], BitFlagScheme] = dict()

        self.mSchemeName: str = ''
        self.mFlagModel = BitFlagModel()
        self.mFlagModel.dataChanged.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.rowsRemoved.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.rowsInserted.connect(self.bitFlagSchemeChanged)
        self.bitFlagSchemeChanged.connect(self.onBitFlagSchemeChanged)
        self.mProxyModel = BitFlagSortFilterProxyModel()
        self.mProxyModel.setSourceModel(self.mFlagModel)
        self.mTreeView: QTreeView
        self.mTreeView.setModel(self.mProxyModel)
        self.mTreeView.selectionModel().selectionChanged.connect(self.updateWidgets)
        self.mTreeView.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.mTreeView.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.mTreeView.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.mTreeView.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.actionRemoveParameters.triggered.connect(self.removeParameters)
        self.actionAddParameter.triggered.connect(self.addParameter)
        self.actionCopyBitFlagScheme.triggered.connect(self.copyBitFlagScheme)
        self.actionPasteBitFlagScheme.triggered.connect(self.pasteBitFlagScheme)

        QApplication.instance().clipboard().dataChanged.connect(self.updateWidgets)
        self.btnRemoveParameters.setDefaultAction(self.actionRemoveParameters)
        self.btnAddParameter.setDefaultAction(self.actionAddParameter)
        self.btnCopyBitFlagScheme.setDefaultAction(self.actionCopyBitFlagScheme)
        self.btnPasteBitFlagScheme.setDefaultAction(self.actionPasteBitFlagScheme)

        self.btnApply.clicked.connect(self.apply)

        self.setProject(QgsProject.instance())

    def setMapToolAction(self, action: QAction):

        self.btnMapTool.setDefaultAction(action)
        self.btnMapTool.setVisible(True)

    def restoreModel(self, *args):
        layer = self.layer()
        band = self.band()
        key = (layer.id(), band)
        if key in self.mSchemeCache.keys():
            scheme = self.mSchemeCache[key]
            self.setBitFlagScheme(scheme)

    def onBitFlagSchemeChanged(self):
        if self.cbLiveUpdate.isChecked():
            self.apply()

    def copyBitFlagScheme(self):

        scheme = self.bitFlagScheme()
        md = scheme.mimeData()

        cb: QClipboard = QApplication.clipboard()
        cb.setMimeData(md, QClipboard.Clipboard)

    def pasteBitFlagScheme(self):

        md = QApplication.clipboard().mimeData()
        scheme = BitFlagScheme.fromMimeData(md)
        if isinstance(scheme, BitFlagScheme) > 0:
            self.setBitFlagScheme(scheme)

    def setLayer(self, layer: QgsMapLayer):
        if isinstance(layer, QgsRasterLayer):
            if self.cbLayer.currentLayer() != layer:
                self.cbLayer.setLayer(layer)
            elif self.cbBand.layer() != layer:
                self.cbBand.setLayer(layer)

            self.restoreModel()

    def layer(self) -> QgsRasterLayer:
        return self.cbBand.layer()

    def addParameter(self):

        startBit = self.mFlagModel.nextFreeBit()
        name = 'Parameter {}'.format(len(self.mFlagModel) + 1)

        flagParameter = BitFlagParameter(name, startBit, 1)
        self.mFlagModel.addFlagParameter(flagParameter)
        self.updateWidgets()

    def layerBitCount(self) -> int:
        lyr = self.layer()
        if isinstance(lyr, QgsRasterLayer):
            return gdal.GetDataTypeSize(lyr.dataProvider().dataType(self.band()))
        else:
            return 0

    def apply(self):

        lyr = self.layer()
        if isinstance(lyr, QgsRasterLayer):
            renderer = self.bitFlagRenderer(self.layer())
            lyr.setRenderer(renderer)
            self.mSchemeCache[(lyr.id(), renderer.grayBand())] = renderer.bitFlagScheme()
            lyr.repaintRequested.emit()

    def updateWidgets(self):
        b = len(self.flagTreeView().selectionModel().selectedRows()) > 0
        self.actionRemoveParameters.setEnabled(b)

        b = self.mFlagModel.nextFreeBit() < self.layerBitCount()
        self.actionAddParameter.setEnabled(b)

        md: QMimeData = QApplication.instance().clipboard().mimeData()

        self.actionPasteBitFlagScheme.setEnabled(BitFlagScheme.MIMEDATA in md.formats())

    def removeParameters(self):

        selectedRows = self.mTreeView.selectionModel().selectedRows()
        toRemove = []
        for idx in selectedRows:
            idx = self.mProxyModel.mapToSource(idx)
            parameter = self.mFlagModel.data(idx, Qt.UserRole)
            if isinstance(parameter, BitFlagParameter) and parameter not in toRemove:
                toRemove.append(parameter)
        for parameter in reversed(toRemove):
            self.mFlagModel.removeFlagParameter(parameter)

    def setBand(self, bandNo: int):
        self.cbBand: QgsRasterBandComboBox
        self.cbBand.setBand(bandNo)

    def band(self) -> int:
        return self.cbBand.currentBand()

    def flagModel(self) -> BitFlagModel:
        return self.mFlagModel

    def flagTreeView(self) -> BitFlagRendererTreeView:
        return self.mTreeView

    def setProject(self, project: QgsProject):
        if project != self.mProject:
            if isinstance(self.mProject, QgsProject):
                self.mProject.layersAdded.disconnect(self.updateExcludedLayers)
            self.cbLayer.setProject(project)
            self.mProject = project
            project.layersAdded.connect(self.updateExcludedLayers)
            self.updateExcludedLayers()

    def updateExcludedLayers(self):

        cb: QgsMapLayerComboBox = self.cbLayer

        excluded = []
        for lyr in self.mProject.mapLayers().values():
            if isinstance(lyr, QgsRasterLayer):
                if lyr.dataProvider().dataType(1) not in [Qgis.DataType.Byte,
                                                          Qgis.DataType.Int8,
                                                          Qgis.DataType.Int16,
                                                          Qgis.DataType.Int32,
                                                          Qgis.DataType.UInt16,
                                                          Qgis.DataType.UInt32]:
                    excluded.append(lyr)

        cb.setExceptedLayerList(excluded)

    def bitFlagRenderer(self, layer: QgsRasterLayer) -> BitFlagRenderer:

        renderer = BitFlagRenderer(layer.dataProvider())
        renderer.setBitFlagScheme(self.bitFlagScheme())

        return renderer

    def name(self) -> str:
        return self.mSchemeName

    def setBitFlagScheme(self, scheme: BitFlagScheme):

        self.mSchemeName = scheme.name()
        self.actionCombineFlags.setChecked(scheme.combineFlags())
        self.btnCombinedFlagsColor.setColor(scheme.combinedFlagsColor())

        self.flagModel().clear()
        for p in scheme:
            self.flagModel().addFlagParameter(p)

    def bitFlagScheme(self) -> BitFlagScheme:
        """
        Reads all settings and returns them as BitFlagScheme
        """

        scheme = BitFlagScheme()
        scheme.setName(self.mSchemeName)
        scheme.setCombineFlags(self.actionCombineFlags.isChecked())
        scheme.setCombinedFlagsColor(self.btnCombinedFlagsColor.color())

        for p in self.flagModel():
            scheme.addParameter(p)

        return scheme
