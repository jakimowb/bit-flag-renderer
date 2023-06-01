import copy
import pathlib
import re

from qgis.PyQt.QtWidgets import QDialog

from bitflagrenderer import DIR_BITFLAG_SCHEMES, PATH_UI_SAVE_FLAG_SCHEMA
from bitflagrenderer.core.utils import loadUi
from bitflagrenderer.core.bitflagscheme import BitFlagScheme
from qgis.gui import QgsFileWidget


class SaveFlagSchemeDialog(QDialog):

    @staticmethod
    def save(schema: BitFlagScheme):
        d = SaveFlagSchemeDialog(schema)
        if d.exec_() == QDialog.Accepted:
            schema = copy.deepcopy(schema)
            schema.setName(d.schemaName())
            schema.writeXMLFile(d.filePath())

    def __init__(self, schema: BitFlagScheme, parent=None):
        super(SaveFlagSchemeDialog, self).__init__(parent=parent)
        loadUi(PATH_UI_SAVE_FLAG_SCHEMA, self)
        assert isinstance(schema, BitFlagScheme)
        self.mSchema = copy.deepcopy(schema)

        self.wSchemeFilePath.setStorageMode(QgsFileWidget.SaveFile)
        filter = 'XML files (*.xml);;Any files (*)'
        self.wSchemeFilePath.setFilter(filter)
        root = DIR_BITFLAG_SCHEMES
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
