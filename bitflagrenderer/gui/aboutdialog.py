from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog

from bitflagrenderer import PATH_ABOUT_UI
from bitflagrenderer.core.utils import loadUi


class AboutBitFlagRenderer(QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(AboutBitFlagRenderer, self).__init__(parent)
        loadUi(PATH_ABOUT_UI, self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init()

    def init(self):
        self.mTitle = self.windowTitle()
        self.listWidget.currentItemChanged.connect(lambda: self.setAboutTitle())
        self.setAboutTitle()

        # page About
        from bitflagrenderer import PATH_LICENSE, __version__, PATH_CHANGELOG, PATH_ABOUT
        self.labelVersion.setText('{}'.format(__version__))

        def readTextFile(path: str):
            with open(path, encoding='utf-8') as f:
                return f.read()
            return 'unable to read {}'.format(path)

        # page Changed
        self.tbAbout.setHtml(readTextFile(PATH_ABOUT))
        # self.tbChanges.setHtml(readTextFile(PATH_CHANGELOG.as_posix() + '.html'))
        # self.tbLicense.setHtml(readTextFile(os.path.splitext(PATH_LICENSE)[0] + '.html'))

        self.tbChanges.setPlainText(readTextFile(PATH_CHANGELOG.as_posix()))
        self.tbLicense.setPlainText(readTextFile(PATH_LICENSE.as_posix()))

    def setAboutTitle(self, suffix=None):
        item = self.listWidget.currentItem()

        if item:
            title = '{} | {}'.format(self.mTitle, item.text())
        else:
            title = self.mTitle
        if suffix:
            title += ' ' + suffix
        self.setWindowTitle(title)
