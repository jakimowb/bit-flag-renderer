# -*- coding: utf-8 -*-

"""
***************************************************************************
    create_plugin.py
    Script to build the Bit Flag Renderer Plugin from Repository code
    ---------------------
    Date                 : August 2020
    Copyright            : (C) 2020 by Benjamin Jakimow
    Email                : benjamin.jakimow@geo.hu-berlin.de
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.
                 *
*                                                                         *
***************************************************************************
"""
# noinspection PyPep8Naming

import argparse
import datetime
import os
import pathlib
import re
import shutil
from typing import Iterator, Union
from xml.dom import minidom

import docutils.core
import markdown

import bitflagrenderer
from bitflagrenderer import DIR_REPO, __version__, PATH_ABOUT, DIR_RESOURCES, DIR_PKG
from qps.make.deploy import QGISMetadataFileWriter
from qps.utils import zipdir

CHECK_COMMITS = False

########## Config Section

with open(PATH_ABOUT, 'r', encoding='utf-8') as f:
    aboutText = f.readlines()
    for i in range(1, len(aboutText)):
        aboutText[i] = '    ' + aboutText[i]
    aboutText = ''.join(aboutText)

MD = QGISMetadataFileWriter()
MD.mName = 'Bit Flag Renderer'
MD.mDescription = bitflagrenderer.DESCRIPTION
MD.mTags = ['Raster']
MD.mCategory = 'Analysis'
MD.mAuthor = 'Benjamin Jakimow, Earth Observation Lab, Humboldt-Universität zu Berlin'
MD.mIcon = 'bitflagrenderer/icons/bitflagimage.png'
MD.mHomepage = bitflagrenderer.URL_HOMEPAGE
MD.mAbout = aboutText
MD.mTracker = bitflagrenderer.URL_ISSUE_TRACKER
MD.mRepository = bitflagrenderer.URL_REPOSITORY
MD.mQgisMinimumVersion = '3.28'
MD.mEmail = 'benjamin.jakimow@geo.hu-berlin.de'

PLUGIN_DIR_NAME = 'BitFlagRenderer'


########## End of config section

def scantree(path, pattern=re.compile('.$')) -> Iterator[pathlib.Path]:
    """
    Recursively returns file paths in directory
    :param path: root directory to search in
    :param pattern: str with required file ending, e.g. ".py" to search for *.py files
    :return: pathlib.Path
    """
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path, pattern=pattern)
        elif entry.is_file and pattern.search(entry.path):
            yield pathlib.Path(entry.path)


def create_plugin():
    DIR_REPO = pathlib.Path(__file__).resolve().parents[1]
    assert (DIR_REPO / '.git').is_dir()

    DIR_DEPLOY = DIR_REPO / 'deploy'

    try:
        import git
        REPO = git.Repo(DIR_REPO)
        currentBranch = REPO.active_branch.name
    except Exception as ex:
        currentBranch = 'TEST'
        print('Unable to find git repo. Set currentBranch to "{}"'.format(currentBranch))

    timestamp = datetime.datetime.now().isoformat().split('.')[0]

    BUILD_NAME = '{}.{}.{}'.format(__version__, timestamp, currentBranch)
    BUILD_NAME = re.sub(r'[:-]', '', BUILD_NAME)
    BUILD_NAME = re.sub(r'[\\/]', '_', BUILD_NAME)
    PLUGIN_DIR = DIR_DEPLOY / PLUGIN_DIR_NAME
    PLUGIN_ZIP = DIR_DEPLOY / f'{PLUGIN_DIR_NAME}.{BUILD_NAME}.zip'

    if PLUGIN_DIR.is_dir():
        shutil.rmtree(PLUGIN_DIR)
    os.makedirs(PLUGIN_DIR, exist_ok=True)

    PATH_METADATAFILE = PLUGIN_DIR / 'metadata.txt'
    MD.mVersion = BUILD_NAME
    MD.writeMetadataTxt(DIR_PKG / 'metadata.txt')
    MD.writeMetadataTxt(PATH_METADATAFILE)

    # 1. (re)-compile all enmapbox resource files

    from scripts.compile_resourcefiles import compileResources
    compileResources()

    # copy python and other resource files
    pattern = re.compile(r'\.(py|svg|png|txt|ui|tif|qml|md|js|css|json)$')
    files = list(scantree(DIR_PKG, pattern=pattern))
    files.extend(list(scantree(DIR_RESOURCES / 'bitflagschemes', pattern=re.compile(r'.*\.xml$'))))
    files.extend(list(scantree(DIR_RESOURCES / 'exampledata', pattern=pattern)))
    files.extend(list(scantree(DIR_RESOURCES / 'icons', pattern=pattern)))
    files.append(DIR_RESOURCES / 'bitflagrenderer.qrc')
    files.append(DIR_RESOURCES / 'bitflagrenderer_rc.py')
    files.append(DIR_PKG / '__init__.py')
    files.append(DIR_REPO / '__init__.py')
    files.append(DIR_REPO / 'ABOUT.md')
    files.append(DIR_REPO / 'CHANGELOG.md')
    files.append(DIR_REPO / 'LICENSE.md')
    files.append(DIR_REPO / 'requirements.txt')

    for fileSrc in files:
        assert fileSrc.is_file()
        fileDst = PLUGIN_DIR / fileSrc.relative_to(DIR_REPO)
        os.makedirs(fileDst.parent, exist_ok=True)
        shutil.copy(fileSrc, fileDst.parent)

    # update metadata version

    f = open(DIR_REPO / 'bitflagrenderer' / '__init__.py')
    lines = f.read()
    f.close()
    lines = re.sub(r'(__version__\W*=\W*)([^\n]+)', r'__version__ = "{}"\n'.format(BUILD_NAME), lines)
    f = open(PLUGIN_DIR / 'bitflagrenderer' / '__init__.py', 'w')
    f.write(lines)
    f.flush()
    f.close()

    createCHANGELOG(PLUGIN_DIR)

    # 5. create a zip
    print('Create zipfile...')
    zipdir(PLUGIN_DIR, PLUGIN_ZIP)

    # 7. install the zip file into the local QGIS instance. You will need to restart QGIS!
    if True:
        info = []
        info.append(f'\n### To update/install the BitFlagRenderer, run this command on your QGIS Python shell:\n')
        info.append('from pyplugin_installer.installer import pluginInstaller')
        info.append('pluginInstaller.installFromZipFile(r"{}")'.format(PLUGIN_ZIP))
        info.append('#### Close (and restart manually)\n')
        # print('iface.mainWindow().close()\n')
        info.append('QProcess.startDetached(QgsApplication.arguments()[0], [])')
        info.append('QgsApplication.quit()\n')
        info.append('## press ENTER\n')

        print('\n'.join(info))

    print('Finished')



def markdownToHTML(path_md: Union[str, pathlib.Path]) -> str:
    path_md = pathlib.Path(path_md)

    html = None
    if not path_md.is_file():
        for s in ['.md', '.rst']:
            p = path_md.parent / (os.path.splitext(path_md.name)[0] + s)
            if p.is_file():
                path_md = p
                break

    if path_md.name.endswith('.rst'):

        assert path_md.is_file(), path_md
        overrides = {'stylesheet': None,
                     'embed_stylesheet': False,
                     'output_encoding': 'utf-8',
                     }

        buffer = io.StringIO()
        html = docutils.core.publish_file(
            source_path=path_md,
            writer_name='html5',
            destination=buffer,
            settings_overrides=overrides)
    elif path_md.name.endswith('.md'):
        with open(path_md, 'r', encoding='utf-8') as f:
            md = f.read()
        html = markdown.markdown(md)
    else:
        raise Exception(f'Unsupported file: {path_md}')
    return html


def createCHANGELOG(dirPlugin):
    """
    Reads the CHANGELOG.md and creates the deploy/CHANGELOG (without extension!) for the QGIS Plugin Manager
    :return:
    """

    pathMD = os.path.join(DIR_REPO, 'CHANGELOG.md')
    pathCL = os.path.join(dirPlugin, 'CHANGELOG')

    html = markdownToHTML(pathMD)
    # make html compact
    # remove newlines as each line will be shown in a table row <tr>
    # see qgspluginmanager.cpp
    html = html.replace('\n', '')

    with open(pathCL, 'w', encoding='utf-8') as f:
        f.write(html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create the BitFlagRenderer Plugin')
    args = parser.parse_args()
    create_plugin()
    exit()
