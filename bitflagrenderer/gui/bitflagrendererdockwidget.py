from qgis.gui import QgsDockWidget


class BitFlagRendererDockWidget(QgsDockWidget):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
