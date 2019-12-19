# -*- coding: utf-8 -*-
"""
***************************************************************************
        begin                : 2019-12-19
        copyright            : (C) 2019 by Benjamin Jakimow
        email                : benjamin.jakimow[at]geo.hu-berlin.de
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************/
"""
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
