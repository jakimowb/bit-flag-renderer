import os, sys
from qgis.gui import *


def classFactory(iface:QgisInterface):  # pylint: disable=invalid-name
    """Loads the Bit Flag Renderer Plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    pluginDir = os.path.dirname(__file__)
    if not pluginDir in sys.path:
        sys.path.append(pluginDir)





    from bitflagrenderer.bitflagrenderplugin import BitFlagRendererPlugin
    return BitFlagRendererPlugin(iface)
