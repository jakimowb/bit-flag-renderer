from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from osgeo import gdal
from qgis.gui import QgsMapLayerConfigWidget, QgsMapCanvas, QgsMapLayerConfigWidgetFactory

from qgis.core import QgsRasterLayer, QgsRectangle, QgsRasterRenderer

from bitflagrenderer import PATH_ICON
from bitflagrenderer.gui.bitflagrasterrendererwidet import BitFlagRasterRendererWidget


class BitFlagLayerConfigWidget(QgsMapLayerConfigWidget):

    def __init__(self, layer: QgsRasterLayer, canvas: QgsMapCanvas, parent: QWidget = None):

        super(BitFlagLayerConfigWidget, self).__init__(layer, canvas, parent=parent)

        self.setLayout(QVBoxLayout())
        self.setPanelTitle('Flag Layer Settings')
        self.mCanvas = canvas
        self.mLayer = layer
        self.mRenderWidget: BitFlagRasterRendererWidget
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            ext = layer.extent()
        else:
            ext = QgsRectangle()

        self.mIsInDockMode = False
        self.mRenderWidget = BitFlagRasterRendererWidget(layer, ext)
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
