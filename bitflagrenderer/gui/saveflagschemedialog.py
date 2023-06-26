import copy
import pathlib
import re

from bitflagrenderer.core import settings
from qgis.PyQt.QtWidgets import QDialog

from bitflagrenderer import PATH_UI_SAVE_FLAG_SCHEME, DIR_PKG
from bitflagrenderer.core.utils import loadUi
from bitflagrenderer.core.bitflagscheme import BitFlagScheme, FILTER_SCHEME_FILES
from qgis.gui import QgsFileWidget


class SaveFlagSchemeDialog(QDialog):

    @staticmethod
    def save(schema: BitFlagScheme) -> pathlib.Path:
        d = SaveFlagSchemeDialog(schema)
        if d.exec_() == QDialog.Accepted:
            schema: BitFlagScheme = copy.deepcopy(schema)
            schema.setName(d.schemaName())
            path = d.filePath()
            schema.writeFile(path)
            return pathlib.Path(path)
        else:
            return None

    def __init__(self, schema: BitFlagScheme, parent=None):
        super(SaveFlagSchemeDialog, self).__init__(parent=parent)
        loadUi(PATH_UI_SAVE_FLAG_SCHEME, self)
        assert isinstance(schema, BitFlagScheme)
        self.mSchema = copy.deepcopy(schema)

        self.wSchemeFilePath.setStorageMode(QgsFileWidget.SaveFile)
        self.wSchemeFilePath.setFilter(FILTER_SCHEME_FILES)
        root = settings.settingsBitFlagSchemeDirectory.value()
        if root:
            root = pathlib.Path(root)
            if not root.is_absolute():
                root = DIR_PKG / root
            self.wSchemeFilePath.setDefaultRoot(root.as_posix())
        self.tbSchemaName.setText(schema.name())

        filePath = schema.name().encode().decode('ascii', 'replace').replace(u'\ufffd', '_')
        filePath = re.sub(r'[ ]', '_', filePath) + '.xml'
        filePath = root / filePath
        self.wSchemeFilePath.setFilePath(filePath.as_posix())

    def schemaName(self) -> str:
        return self.tbSchemaName.text()

    def schema(self) -> BitFlagScheme:
        return self.mSchema

    def filePath(self) -> str:
        """
        :return:
        :rtype:
        """
        return pathlib.Path(self.wSchemeFilePath.filePath()).as_posix()
