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
import enum
import os
import pathlib

__version__ = '0.5'

from qgis.PyQt.QtCore import QSettings

import qgis.utils
from qgis.gui import QgisInterface

TITLE = 'Bit Flag Renderer'
AUTHOR = 'Benjamin Jakimow'
MAIL = 'benjamin.jakimow@geo.hu-berlin.de'

LICENSE = 'GNU GPL-3'
DESCRIPTION = 'Visualization of quality image bit flags.'
URL_HOMEPAGE = 'https://bit-flag-renderer.readthedocs.io/en/latest/'
URL_DOCUMENTATION = 'https://bit-flag-renderer.readthedocs.io/en/latest/'
URL_REPOSITORY = 'https://bitbucket.org/jakimowb/bit-flag-renderer'

URL_ISSUE_TRACKER = 'https://bitbucket.org/jakimowb/bit-flag-renderer/issues'
URL_CREATE_ISSUE = 'https://bitbucket.org/jakimowb/bit-flag-renderer/issues/new'
DEPENDENCIES = ['numpy', 'gdal']

LOG_MESSAGE_TAG = TITLE
DIR_REPO = pathlib.Path(__file__).parents[1]
DIR_RESOURCES = pathlib.Path(__file__).parent / 'resources'
DIR_EXAMPLE_DATA = DIR_RESOURCES / 'exampledata'
DIR_BITFLAG_SCHEMES = DIR_RESOURCES / 'bitflagschemes'
DIR_ICONS = DIR_RESOURCES / 'bitflagrenderer' / 'icons'

PATH_CHANGELOG = DIR_REPO / 'CHANGELOG.md'
PATH_LICENSE = DIR_REPO / 'LICENSE.md'
PATH_ABOUT = DIR_REPO / 'ABOUT.html'

PATH_RESOURCES = pathlib.Path(__file__).parents[0] / 'resources.py'


# if os.path.isfile(PATH_RESOURCES):
#    import bitflagrenderer.resources
#    bitflagrenderer.resources.qInitResources()

def classFactory(iface: QgisInterface):  # pylint: disable=invalid-name
    """Loads the Bit Flag Renderer Plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    pluginDir = os.path.dirname(__file__)
    # if not pluginDir in sys.path:
    #    sys.path.append(pluginDir)
    from bitflagrenderer.plugin import BitFlagRendererPlugin
    return BitFlagRendererPlugin(iface)


def registerConfigWidgetFactory():
    global FACTORY
    from .gui.bitflaglayerconfigwidget import BitFlagLayerConfigWidgetFactory
    if not isinstance(FACTORY, BitFlagLayerConfigWidgetFactory):
        FACTORY = BitFlagLayerConfigWidgetFactory()
        qgis.utils.iface.registerMapLayerConfigWidgetFactory(FACTORY)


def unregisterConfigWidgetFactory():
    global FACTORY
    from .gui.bitflaglayerconfigwidget import BitFlagLayerConfigWidgetFactory
    if isinstance(FACTORY, BitFlagLayerConfigWidgetFactory):
        qgis.utils.iface.unregisterMapLayerConfigWidgetFactory(FACTORY)
        FACTORY = None


def settings() -> QSettings:
    """
    Returns the Bit Flag Renderer settings.
    :return: QSettings
    """
    settings = QSettings(QSettings.UserScope, 'HU-Berlin', TYPE)

    return settings


FACTORY = None


class SettingsKeys(enum.Enum):
    TreeViewState = 'tree_view_state'
    TreeViewSortColumn = 'tree_view_sort_column'
    TreeViewSortOrder = 'tree_view_sort_order'
    BitFlagSchemes = 'bit_flag_schemes'


MAX_BITS_PER_PARAMETER = 4
PATH_UI = os.path.join(os.path.dirname(__file__), 'resources/bitflagrenderer.ui')
PATH_ABOUT_UI = os.path.join(os.path.dirname(__file__), 'gui/aboutdialog.ui')
PATH_ICON = os.path.join(os.path.dirname(__file__), *['icons', 'bitflagimage.png'])
PATH_UI_SAVE_FLAG_SCHEMA = os.path.join(os.path.dirname(__file__), 'gui/saveflagschemadialog.ui')
TYPE = 'BitFlagRenderer'
QGIS_RESOURCE_WARNINGS = set()

NEXT_COLOR_HUE_DELTA_CON = 10
NEXT_COLOR_HUE_DELTA_CAT = 100
