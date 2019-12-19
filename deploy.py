import os, sys, pathlib, re, datetime, shutil
from pb_tool import pb_tool
import git
from qps.utils import file_search, zipdir
from qps.make.make import compileResourceFile
from os.path import join as jp
from docutils.core import publish_string
from bitflagrenderer import DIR_REPO, PATH_ABOUT, PATH_CHANGELOG, VERSION, PATH_LICENSE, URL_ISSUE_TRACKER, DIR_ICONS

DIR_BUILD = DIR_REPO / 'build'
DIR_DOC_SOURCE = DIR_REPO / 'doc' / 'source'
DIR_DEPLOY = DIR_REPO / 'deploy'
PATH_CFG = DIR_REPO / 'pb_tool.cfg'
PATH_METADATA = DIR_REPO / 'metadata.txt'


QGIS_MIN = '3.4'
QGIS_MAX = '3.99'

REPO = git.Repo(DIR_REPO)
currentBranch = REPO.active_branch.name
timestamp = re.sub(r'[- :]', '', datetime.datetime.now().isoformat())[0:13]
buildID = '{}.{}.{}'.format(re.search(r'(\.?[^.]*){2}', VERSION).group()
                            , timestamp,
                            re.sub(r'[\\/]', '_', currentBranch))

def rm(p):
    """
    Remove files or directory 'p'
    :param p: path of file or directory to be removed.
    """
    if os.path.isfile(p):
        os.remove(p)
    elif os.path.isdir(p):
        shutil.rmtree(p)

def mkDir(d, delete=False):
    """
    Make directory.
    :param d: path of directory to be created
    :param delete: set on True to delete the directory contents, in case the directory already existed.
    """
    if delete and os.path.isdir(d):
        rm(d)
    if not os.path.isdir(d):
        os.makedirs(d)


def compileResourceFiles():

    for path in file_search(DIR_REPO / 'bitflagrenderer', '*.qrc', recursive=True):
        compileResourceFile(path)


class QGISMetadataFileWriter(object):

    def __init__(self):
        self.mName = None

        self.mDescription = None
        self.mVersion = None
        self.mQgisMinimumVersion = '3.8'
        self.mQgisMaximumVersion = '3.99'
        self.mAuthor = None
        self.mAbout = None
        self.mEmail = None
        self.mHomepage = None
        self.mIcon = None
        self.mTracker = None
        self.mRepository = None
        self.mIsExperimental = False
        self.mTags = None
        self.mCategory = None
        self.mChangelog = ''

    def validate(self)->bool:

        return True

    def metadataString(self)->str:
        assert self.validate()

        lines = ['[general]']
        lines.append('name={}'.format(self.mName))
        lines.append('author={}'.format(self.mAuthor))
        if self.mEmail:
            lines.append('email={}'.format(self.mEmail))

        lines.append('description={}'.format(self.mDescription))
        lines.append('version={}'.format(self.mVersion))
        lines.append('qgisMinimumVersion={}'.format(self.mQgisMinimumVersion))
        lines.append('qgisMaximumVersion={}'.format(self.mQgisMaximumVersion))
        lines.append('about={}'.format(re.sub('\n', '', self.mAbout)))

        lines.append('icon={}'.format(self.mIcon))

        lines.append('tags={}'.format(', '.join(self.mTags)))
        lines.append('category={}'.format(self.mRepository))

        lines.append('homepage={}'.format(self.mHomepage))
        if self.mTracker:
            lines.append('tracker={}'.format(self.mTracker))
        if self.mRepository:
            lines.append('repository={}'.format(self.mRepository))
        if isinstance(self.mIsExperimental, bool):
            lines.append('experimental={}'.format(self.mIsExperimental))


        #lines.append('deprecated={}'.format(self.mIsDeprecated))
        lines.append('')
        lines.append('changelog={}'.format(self.mChangelog))

        return '\n'.join(lines)
    """
    [general]
    name=dummy
    description=dummy
    version=dummy
    qgisMinimumVersion=dummy
    qgisMaximumVersion=dummy
    author=dummy
    about=dummy
    email=dummy
    icon=dummy
    homepage=dummy
    tracker=dummy
    repository=dummy
    experimental=False
    deprecated=False
    tags=remote sensing, raster, time series, data cube, landsat, sentinel
    category=Raster
    """

    def writeMetadataTxt(self, path:str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.metadataString())
        # read again and run checks
        import pyplugin_installer.installer_data

        # test if we could read the plugin
        import pyplugin_installer.installer_data
        P = pyplugin_installer.installer_data.Plugins()
        plugin = P.getInstalledPlugin(self.mName, os.path.dirname(path), True)

        #if hasattr(pyplugin_installer.installer_data, 'errorDetails'):
        #    raise Exception('plugin structure/metadata error:\n{}'.format(pyplugin_installer.installer_data.errorDetails))
        s = ""



def updateSphinxChangelog():
    with open(PATH_CHANGELOG, 'r') as f:
        # replace (#1) with (https://bitbucket.org/jakimowb/eo-time-series-viewer/issues/1)
        urlPrefix = r'https://bitbucket.org/jakimowb/eo-time-series-viewer/issues/'
        lines = f.readlines()
        lines = [re.sub(r'(#(\d+))', r'`#\2 <{}\2>`_'.format(urlPrefix), line) for line in lines]

        pathChangelogRst = jp(DIR_DOC_SOURCE, 'changelog.rst')

        with open(pathChangelogRst, 'w', encoding='utf-8') as f2:
            f2.writelines(lines)

        s = ""


def updateInfoHTMLs():

    urlIssueTracker = URL_ISSUE_TRACKER

    def readTextFile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def doUpdate(path:str, content:str)->bool:

        b = False
        if not os.path.isfile(path):
            b = True
        else:
            with open(path, 'r', encoding='utf-8') as f:
                b = content != f.read()

        if b:
            print('update {}'.format(path))
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print('{} already updated'.format(path))

    # CHANGELOG -> CHANGELOG.html
    txt = readTextFile(PATH_CHANGELOG)
    txt = re.sub(r'(#(\d+))', r'`#\2 <{}\2>`_'.format(urlIssueTracker), txt)

    txt = publish_string(txt, writer_name='html').decode('utf-8')

    pathChangelogHtml = PATH_CHANGELOG.as_posix() + '.html'
    doUpdate(pathChangelogHtml, txt)

    # LICENSE.md -> LICENSE.html
    txt = readTextFile(PATH_LICENSE)
    txt = publish_string(txt, writer_name='html').decode('utf-8')
    pathLicenseHtml = os.path.splitext(PATH_LICENSE)[0]+'.html'
    doUpdate(pathLicenseHtml, txt)

def build():
    # local pb_tool configuration file.
    pathCfg = jp(DIR_REPO, 'pb_tool.cfg')
    cfg = pb_tool.get_config(pathCfg)
    cdir = os.path.dirname(pathCfg)
    pluginname = cfg.get('plugin', 'name')
    dirPlugin = jp(DIR_DEPLOY, pluginname)
    os.chdir(cdir)

    mkDir(DIR_DEPLOY)

    # describe metadata
    import bitflagrenderer
    MD = QGISMetadataFileWriter()
    with open(PATH_ABOUT, 'r', encoding='utf-8') as f:
        aboutText = f.readlines()
        for i in range(1, len(aboutText)):
            aboutText[i] = '    ' + aboutText[i]
        aboutText = ''.join(aboutText)
    MD.mName = bitflagrenderer.TITLE

    with open(PATH_CHANGELOG, 'r', encoding='utf-8') as f:
        changelog = f.readlines()
        changelog = ''.join(changelog[4:])

    MD.mChangelog = changelog
    MD.mCategory = 'Raster'
    MD.mAbout = aboutText
    MD.mDescription = bitflagrenderer.DESCRIPTION
    MD.mVersion = buildID
    MD.mTracker = bitflagrenderer.URL_ISSUE_TRACKER
    MD.mHomepage = bitflagrenderer.URL_HOMEPAGE
    MD.mRepository = bitflagrenderer.URL_REPOSITORY
    MD.mQgisMinimumVersion = QGIS_MIN
    MD.mQgisMaximumVersion = QGIS_MAX
    MD.mAuthor = bitflagrenderer.AUTHOR
    MD.mEmail = bitflagrenderer.MAIL
    MD.mIcon = 'bitflagrenderer/icons/bitflagimage.png'
    MD.mTags = ['remote sensing', 'raster', 'flags', 'bit flags', 'landsat']
    print(MD.metadataString())

    if os.path.isdir(dirPlugin):
        print('Remove old build folder...')
        shutil.rmtree(dirPlugin, ignore_errors=True)

    # required to choose andy DIR_DEPLOY of choice
    # issue tracker: https://github.com/g-sherman/plugin_build_tool/issues/4

    if True:
        # 1. clean an existing directory = plugin folder
        try:
            pb_tool.clean_deployment(ask_first=False)
        except:
            pass


        # 3. Deploy = write the data to the new plugin folder
        pb_tool.deploy_files(pathCfg, DIR_DEPLOY, 'default', quick=True, confirm=False)

        # 4. As long as we can not specify in the pb_tool.cfg which file types are not to deploy,
        # we need to remove them afterwards.
        # issue: https://github.com/g-sherman/plugin_build_tool/issues/5
        print('Remove files...')

        if True:
            # delete help folder
            shutil.rmtree(os.path.join(dirPlugin, *['help']), ignore_errors=True)
        for f in file_search(DIR_DEPLOY, re.compile('(svg|pyc)$'), recursive=True):
            os.remove(f)
        for d in file_search(DIR_DEPLOY, '__pycache__', directories=True, recursive=True):
            os.rmdir(d)

    # update metadata version
    if True:
        pathMetadata = jp(dirPlugin, 'metadata.txt')

        MD.writeMetadataTxt(pathMetadata)

        # update version number in metadata

        pathPackageInit = jp(dirPlugin, *['bitflagrenderer', '__init__.py'])
        f = open(pathPackageInit)
        lines = f.read()
        f.close()
        lines = re.sub(r'(__version__\W*=\W*)([^\n]+)', r'__version__ = "{}"\n'.format(buildID), lines)
        f = open(pathPackageInit, 'w')
        f.write(lines)
        f.flush()
        f.close()

    # copy CHANGELOG to doc/source/changelog.rst
    updateSphinxChangelog()

    # update the internal-used CHANGELOG.html
    updateInfoHTMLs()

    # 5. create a zip
    print('Create zipfile...')

    pluginname = cfg.get('plugin', 'name')
    pathZip = jp(DIR_DEPLOY, '{}.{}.zip'.format(pluginname, buildID))
    dirPlugin = jp(DIR_DEPLOY, pluginname)
    zipdir(dirPlugin, pathZip)
    # os.chdir(dirPlugin)
    # shutil.make_archive(pathZip, 'zip', '..', dirPlugin)


    # 6. install the zip file into the local QGIS instance. You will need to restart QGIS!
    if True:
        print('\n### To update/install run this command on your QGIS Python shell:\n')
        print('from pyplugin_installer.installer import pluginInstaller')
        print('pluginInstaller.installFromZipFile(r"{}")'.format(pathZip))
        print('#### Close (and restart manually)\n')
        # print('iface.mainWindow().close()\n')
        print('QProcess.startDetached(QgsApplication.arguments()[0], [])')
        print('QgsApplication.quit()\n')
        print('## press ENTER\n')

    print('Finished')

if __name__ == "__main__":
    compileResourceFiles()
    build()
