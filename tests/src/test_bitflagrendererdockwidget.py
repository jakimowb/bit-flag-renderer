import re
import unittest

from qgis.PyQt.QtCore import Qt, QMimeData
from qgis.PyQt.QtWidgets import QMainWindow, QApplication
from qgis.gui import QgsMapCanvas, QgsLayerTreeView

from qgis.core import QgsLayerTreeModel, QgsLayerTree, QgsLayerTreeLayer, QgsLayerTreeGroup
from qgis.core import QgsRasterLayer, QgsProject

from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_BITFLAG_SCHEMES
from bitflagrenderer.core.bitflagscheme import BitFlagScheme
from bitflagrenderer.core.bitlfagrenderer import BitFlagRenderer
from bitflagrenderer.gui.bitflagrendererdockwidget import BitFlagRendererDockWidget
from bitflagrenderer.resources.bitflagrenderer_rc import qInitResources
from qgis.gui import QgisInterface
from qps.testing import start_app
from qps.utils import file_search
from tests.src.bitflagtests import BitFlagTestCases
from tests.src.test_bitflagrenderer import filepath

app = start_app()
qInitResources()

pathFlagImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*BQA.*\.tif$')))[0]
pathTOAImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*TOA.*\.tif$')))[0]


class DockWidgetTestCases(BitFlagTestCases):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

    def test_DockWidget(self):
        w = BitFlagRendererDockWidget()

        scheme = self.createBitFlagScheme()
        w.setBitFlagScheme(scheme)

        w.copyBitFlagScheme()

        # test copy & paste
        md: QMimeData = QApplication.clipboard().mimeData()
        scheme2 = BitFlagScheme.fromMimeData(md)
        self.assertEqual(scheme, scheme2)
        del scheme2[1]
        self.assertNotEqual(scheme, scheme2)

        w.setBitFlagScheme(scheme2)

        self.assertNotEqual(scheme, w.bitFlagScheme())
        w.pasteBitFlagScheme()
        self.assertEqual(scheme, w.bitFlagScheme())

    def test_QGIS_integration(self):
        from qgis.utils import iface
        assert isinstance(iface, QgisInterface)
        mw: QMainWindow = iface.mainWindow()
        iface.mapCanvas().setParallelRenderingEnabled(False)

        lyr1 = QgsRasterLayer(pathFlagImage)
        lyr1.setName('Flags')
        lyr2 = QgsRasterLayer(pathTOAImage)
        lyr2.setName('TOA')
        lyr3 = self.floatLayer()

        project = QgsProject.instance()
        layers = [lyr1, lyr2, lyr3]
        project.addMapLayers(layers)
        w = BitFlagRendererDockWidget()

        def reorderLayers(*args):
            c: QgsMapCanvas = iface.mapCanvas()
            tv: QgsLayerTreeView = iface.layerTreeView()
            tm: QgsLayerTreeModel = tv.model().sourceModel()
            lt: QgsLayerTree = tm.rootGroup()
            n = lt.findLayer(w.layer())
            if isinstance(n, QgsLayerTreeLayer):
                n2 = n.clone()

                p: QgsLayerTreeGroup = n.parent()
                p.insertChildNode(0, n2)
                p.removeChildNode(n)

        w.cbLayer.layerChanged.connect(reorderLayers)

        mw.addDockWidget(Qt.RightDockWidgetArea, w)

        w.setAutoApply(False)
        w.setLayer(lyr1)

        w.addParameter()
        w.addParameter()
        w.addParameter()

        scheme = w.bitFlagScheme()
        self.assertIsInstance(scheme, BitFlagScheme)
        self.assertTrue(len(scheme) == 3)

        point = lyr1.extent().center()
        w.loadBitFlags(lyr1.crs(), point)

        renderer = w.bitFlagRenderer(lyr1)
        self.assertIsInstance(renderer, BitFlagRenderer)
        self.assertTrue(not isinstance(lyr1.renderer(), BitFlagRenderer))

        w.apply()
        self.assertTrue(isinstance(lyr1.renderer(), BitFlagRenderer))

        pathFlagSchemeLND = filepath(DIR_BITFLAG_SCHEMES, r'landsat_level2_pixel_qa.xml')
        scheme = BitFlagScheme.fromFile(pathFlagSchemeLND)[0]
        w.setBitFlagScheme(scheme)
        w.setAutoApply(True)
        self.showGui(mw)

        project.removeAllMapLayers()


if __name__ == '__main__':
    unittest.main()
