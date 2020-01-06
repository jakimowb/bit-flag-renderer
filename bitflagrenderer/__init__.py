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

import pathlib, os

VERSION = '0.3'
__version__ = '<dummy>'
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
DIR_EXAMPLE_DATA = DIR_REPO / 'exampledata'
DIR_BITFLAG_SCHEMES = DIR_REPO / 'bitflagschemes'
DIR_ICONS = DIR_REPO / 'bitflagrenderer' / 'icons'

PATH_CHANGELOG = DIR_REPO / 'CHANGELOG'
PATH_LICENSE = DIR_REPO / 'LICENSE.md'
PATH_ABOUT = DIR_REPO / 'ABOUT.html'

PATH_RESOURCES = pathlib.Path(__file__).parents[0] / 'resources.py'
if os.path.isfile(PATH_RESOURCES):
    import bitflagrenderer.resources
    bitflagrenderer.resources.qInitResources()