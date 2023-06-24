import re
import unittest

from bitflagrenderer import DIR_EXAMPLE_DATA, DIR_BITFLAG_SCHEMES
from bitflagrenderer.core.bitflagscheme import BitFlagScheme
from bitflagrenderer.gui.aboutdialog import AboutBitFlagRenderer
from bitflagrenderer.gui.bitflagrendererdockwidget import BitFlagRendererDockWidget
from bitflagrenderer.plugin import BitFlagRendererPlugin
from bitflagrenderer.resources.bitflagrenderer_rc import qInitResources
from qgis.core import QgsLayerTreeModel, QgsLayerTree, QgsLayerTreeLayer, QgsLayerTreeGroup
from qgis.core import QgsRasterLayer, QgsProject
from qgis.gui import QgisInterface
from qgis.gui import QgsMapCanvas, QgsLayerTreeView
from qps.testing import start_app, QgisMockup
from qps.utils import file_search
from tests.src.bitflagtests import BitFlagTestCases
from tests.src.test_bitflagrenderer import filepath

app = start_app()
qInitResources()

pathFlagImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*BQA.*\.tif$')))[0]
pathTOAImage = list(file_search(DIR_EXAMPLE_DATA, re.compile(r'.*TOA.*\.tif$')))[0]


class PluginTestCases(BitFlagTestCases):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

    def test_AboutDialog(self):
        d = AboutBitFlagRenderer()
        d.show()

        self.showGui(d)

    def test_Plugin(self):
        from qgis.utils import iface
        iface: QgisInterface
        self.assertIsInstance(iface, QgisMockup)
        P = BitFlagRendererPlugin()
        P.initGui()

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

        w.setAutoApply(False)
        w.setLayer(lyr1)
        w.setVisible(True)

        pathFlagSchemeLND = filepath(DIR_BITFLAG_SCHEMES, r'landsat_level2_pixel_qa.xml')
        scheme = BitFlagScheme.fromFile(pathFlagSchemeLND)[0]

        w.setBitFlagScheme(scheme)
        w.setAutoApply(True)
        self.showGui(iface.mainWindow())

        project.removeAllMapLayers()


if __name__ == '__main__':
    unittest.main()
