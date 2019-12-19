from qgis.gui import *

def classFactory(iface:QgisInterface):  # pylint: disable=invalid-name
    """Loads the Bit Flag Renderer Plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from bitflagrenderer.bitflagrendererplugin import FlagRasterRendererPlugin
    return FlagRasterRendererPlugin(iface)
