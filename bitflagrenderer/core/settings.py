from qgis.core import QgsSettingsEntryString

from bitflagrenderer import TITLE, DIR_BITFLAG_SCHEMES
from qgis.core import QgsSettingsTree
from qgis.core import QgsSettingsTreeNode

settingsNode: QgsSettingsTreeNode = QgsSettingsTree.createPluginTreeNode(TITLE)

settingsBitFlagSchemeDirectory: QgsSettingsEntryString = QgsSettingsEntryString(
    'scheme_directories', settingsNode, defaultValue=DIR_BITFLAG_SCHEMES.as_posix())
