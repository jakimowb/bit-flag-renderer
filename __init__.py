import os, sys, site
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *

class FlagRasterRendererPlugin(object):

    def __init__(self, iface:QgisInterface):

        self.iface = iface
        self.mFactory = None
        site.addsitedir(os.path.dirname(__file__))

    def initGui(self):

        from bitflagrenderer.bitflagrenderer import registerConfigWidgetFactory
        registerConfigWidgetFactory()

    def unload(self):
        from bitflagrenderer.bitflagrenderer import unregisterConfigWidgetFactory
        unregisterConfigWidgetFactory()


def classFactory(iface:QgisInterface):  # pylint: disable=invalid-name
    """Load the Bit Flag Renderer Plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    return  FlagRasterRendererPlugin(iface)
