from qgis.PyQt.QtCore import Qt, QModelIndex
from qgis.PyQt.QtGui import QContextMenuEvent, QColor
from qgis.PyQt.QtWidgets import QTreeView, QMenu, QAction

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
            a: QAction = m.addAction('Set Color')
            a.setEnabled(not flagModel.combineFlags())
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

        if idx.flags() & Qt.ItemIsEditable != 0:
            color: QColor = idx.data(Qt.BackgroundColorRole)

            item = idx.data(role=Qt.UserRole)
            title = 'Set color'

            if isinstance(item, BitFlagState):
                title += f' for "{item.name()}"'

            color2 = QgsColorDialog.getColor(initialColor=color, parent=self, allowOpacity=True, title=title)
            if color2.isValid():
                flagModel: BitFlagModel = self.model().sourceModel()
                self.model().setData(idx, color2, role=Qt.EditRole)
