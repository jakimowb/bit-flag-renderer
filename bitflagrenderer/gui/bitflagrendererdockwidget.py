from pathlib import Path
from typing import Dict, Tuple

from osgeo import gdal

from bitflagrenderer.core.bitflagmodel import BitFlagModel, BitFlagSortFilterProxyModel
from bitflagrenderer.core.bitflagscheme import BitFlagParameter, BitFlagScheme
from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer
from bitflagrenderer.core.utils import bit_string, BITFLAG_DATA_TYPES
from bitflagrenderer.gui.bitflagrenderertreeview import BitFlagRendererTreeView
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QMimeData, pyqtSignal
from qgis.PyQt.QtGui import QClipboard
from qgis.PyQt.QtWidgets import QHeaderView, QTreeView, QApplication, QLineEdit
from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsRasterDataProvider, QgsRaster, \
    QgsCoordinateTransform, QgsRasterIdentifyResult, QgsRasterRenderer
from qgis.core import Qgis, QgsMapLayerProxyModel, QgsProject, QgsMapLayer, QgsRasterLayer
from qgis.gui import QgsDockWidget, QgsMapLayerComboBox, QgsRasterBandComboBox, QgsColorButton


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

        self.mSchemeCache: Dict[Tuple[str, int], BitFlagScheme] = dict()

        self.mSchemeName: str = ''
        self.mFlagModel = BitFlagModel()
        self.mFlagModel.dataChanged.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.rowsRemoved.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.rowsInserted.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.modelReset.connect(self.bitFlagSchemeChanged)
        self.mFlagModel.combinedFlagsColorChanged.connect(self.bitFlagSchemeChanged)

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
        self.mFlagModel.setCombineFlags(False)
        self.actionCombineBitFlags.setChecked(False)
        self.actionCombineBitFlags.toggled.connect(self.mFlagModel.setCombineFlags)

        QApplication.instance().clipboard().dataChanged.connect(self.updateWidgets)
        self.btnRemoveParameters.setDefaultAction(self.actionRemoveParameters)
        self.btnAddParameter.setDefaultAction(self.actionAddParameter)
        self.btnCopyBitFlagScheme.setDefaultAction(self.actionCopyBitFlagScheme)
        self.btnPasteBitFlagScheme.setDefaultAction(self.actionPasteBitFlagScheme)
        self.btnShowBitFlags.setDefaultAction(self.actionShowBitFlags)
        self.btnCombineBitFlags.setDefaultAction(self.actionCombineBitFlags)
        self.btnNoDataColor: QgsColorButton
        self.btnNoDataColor.setToNoColor()
        self.btnNoDataColor.colorChanged.connect(self.bitFlagSchemeChanged.emit)

        self.btnApply.clicked.connect(self.apply)
        self.cbLiveUpdate.toggled.connect(self.liveUpdateToggled)
        self.setProject(QgsProject.instance())

    def liveUpdateToggled(self, b: bool):
        if b:
            self.apply()

    def loadBitFlags(self, crs: QgsCoordinateReferenceSystem, point: QgsPointXY):
        lyr = self.layer()
        if isinstance(lyr, QgsRasterLayer):
            band = self.band()
            dp: QgsRasterDataProvider = lyr.dataProvider()

            if dp.dataType(band) in BITFLAG_DATA_TYPES.keys():
                if crs != lyr.crs():
                    trans = QgsCoordinateTransform()
                    trans.setSourceCrs(crs)
                    trans.setDestinationCrs(lyr.crs())
                    point = trans.transform(point)

                point = point
                values: QgsRasterIdentifyResult = dp.identify(point, QgsRaster.IdentifyFormatValue)
                if values.isValid():
                    pixelvalue = values.results().get(band, None)
                    if pixelvalue:
                        self.tbCursorValue: QLineEdit
                        self.tbCursorValue.setText(bit_string(int(pixelvalue)))
            s = ""

    def restoreModel(self, *args):
        layer = self.layer()
        band = self.band()
        key = (layer.id(), band)
        r: QgsRasterRenderer = layer.renderer()
        if isinstance(r, BitFlagRenderer):
            self.setBitFlagScheme(r.bitFlagScheme())
        else:
            self.setBitFlagScheme(self.mSchemeCache.get(key, BitFlagScheme(name=layer.name())))

    def onBitFlagSchemeChanged(self):
        if self.autoApply():
            self.apply()

    def autoApply(self) -> bool:
        return self.cbLiveUpdate.isChecked()

    def setAutoApply(self, b: bool):
        self.cbLiveUpdate.setChecked(b)

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
        self.actionCombineBitFlags.setChecked(scheme.combineFlags())
        self.btnNoDataColor.setColor(scheme.noDataColor())

        self.flagModel().clear()
        self.flagModel().setCombinedFlagsColor(scheme.combinedFlagsColor())
        self.flagModel().setCombineFlags(scheme.combineFlags())
        for p in scheme:
            self.flagModel().addFlagParameter(p)

    def bitFlagScheme(self) -> BitFlagScheme:
        """
        Reads all settings and returns them as BitFlagScheme
        """

        scheme = BitFlagScheme()
        scheme.setName(self.mSchemeName)
        scheme.setCombineFlags(self.mFlagModel.combineFlags())
        scheme.setCombinedFlagsColor(self.mFlagModel.combinedFlagsColor())
        scheme.setNoDataColor(self.btnNoDataColor.color())

        for p in self.flagModel():
            scheme.addParameter(p)

        return scheme
