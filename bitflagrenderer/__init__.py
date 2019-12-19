import pathlib, os

VERSION = '0.1'
__version__ = '<dummy>'
TITLE = 'Bit Flag Renderer'
AUTHOR = 'Benjamin Jakimow'
MAIL = 'benjamin.jakimow@geo.hu-berlin.de'

LICENSE = 'GNU GPL-3'
DESCRIPTION = 'Visualization of multi-sensor Earth observation time series data.'
URL_HOMEPAGE = 'https://bitbucket.org/jakimowb/eo-time-series-viewer'
URL_DOCUMENTATION = 'http://eo-time-series-viewer.readthedocs.io/en/latest/'
URL_REPOSITORY = 'https://bitbucket.org/jakimowb/eo-time-series-viewer'

URL_ISSUE_TRACKER = 'https://bitbucket.org/jakimowb/eo-time-series-viewer/issues'
URL_CREATE_ISSUE = 'https://bitbucket.org/jakimowb/eo-time-series-viewer/issues/new'
DEPENDENCIES = ['numpy', 'gdal']

LOG_MESSAGE_TAG = TITLE
DIR_REPO = pathlib.Path(__file__).parents[1]
DIR_EXAMPLE_DATA = DIR_REPO / 'exampledata'
DIR_BITFLAG_SCHEMES = DIR_REPO / 'bitflagschemes'

PATH_CHANGELOG = DIR_REPO / 'CHANGELOG'
PATH_LICENSE = DIR_REPO / 'LICENSE.md'
PATH_ABOUT = DIR_REPO / 'ABOUT.html'

PATH_RESOURCES = pathlib.Path(__file__).parents[0] / 'resources.py'
if os.path.isfile(PATH_RESOURCES):
    import bitflagrenderer.resources
    bitflagrenderer.resources.qInitResources()