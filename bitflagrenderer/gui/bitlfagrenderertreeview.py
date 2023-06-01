from qgis.PyQt.QtCore import Qt, QModelIndex
from qgis.PyQt.QtGui import QContextMenuEvent
from qgis.PyQt.QtWidgets import QTreeView, QMenu

from bitflagrenderer.core.bitflagscheme import BitFlagState
from bitflagrenderer.core.bitflagmodel import BitFlagModel
from qgis.gui import QgsColorDialog


class BitFlagRendererTreeView(QTreeView):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.doubleClicked.connect(self.onDoubleClick)

    def contextMenu(self, event: QContextMenuEvent) -> QMenu:
        """
        Create the context menu
        """
        cidx = self.currentIndex()

        model = self.model()

        cname = self.model().headerData(cidx.column(), Qt.Horizontal)
        flagModel: BitFlagModel = self.model().sourceModel()
        m = QMenu()

        if bool(self.model().flags(cidx) & Qt.ItemIsEditable):
            a = m.addAction('Edit')
            a.triggered.connect(lambda *args, idx=cidx: self.onEditRequest(idx))

        if cname == flagModel.cnColor and isinstance(cidx.data(role=Qt.UserRole), BitFlagState):
            a = m.addAction('Set Color')
            a.triggered.connect(lambda *args, idx=cidx: self.showColorDialog(idx))

        return m

    def onEditRequest(self, idx: QModelIndex):
        #  print(f'{idx} {idx.row()} {idx.column()} {idx.isValid()}')
        #  print(idx.data(role=Qt.UserRole))
        self.setCurrentIndex(idx)
        self.edit(idx)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Opens a context menu
        """
        m = self.contextMenu(event)
        m.exec_(event.globalPos())

    def onDoubleClick(self, idx: QModelIndex) -> None:
        cname = self.model().headerData(idx.column(), Qt.Horizontal)
        flagModel: BitFlagModel = self.model().sourceModel()
        if cname == flagModel.cnColor:
            self.showColorDialog(idx)
        # other actions handled by base-class

    def showColorDialog(self, idx: QModelIndex):
        item = idx.data(role=Qt.UserRole)
        if isinstance(item, BitFlagState):
            c = QgsColorDialog.getColor(item.color(), self,
                                        'Set color for "{}"'.format(item.name()))

            if c.isValid():
                self.model().setData(idx, c, role=Qt.EditRole)
