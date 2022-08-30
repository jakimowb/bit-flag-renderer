"""
Initial setup of repository.
Run this script after you have cloned the Bitflagrendere repository
"""
import pathlib
import site

DIR_REPO = pathlib.Path(__file__).parents[1].resolve()


def install_qgisresources():
    localpath = DIR_REPO / 'qgisresources'

    from scripts.install_testdata import install_zipfile
    from scripts.install_testdata import URL_QGIS_RESOURCES
    install_zipfile(URL_QGIS_RESOURCES, localpath)


def setup_enmapbox_repository():
    # specify the local path to the cloned QGIS repository

    DIR_SITEPACKAGES = DIR_REPO / 'site-packages'
    DIR_QGISRESOURCES = DIR_REPO / 'qgisresources'

    site.addsitedir(DIR_REPO)

    from scripts.compile_resourcefiles import compileResources
    from scripts.install_testdata import install_qgisresources

    # 1. compile EnMAP-Box resource files (*.qrc) into corresponding python modules (*.py)
    print('Compile BitFlagRenderer resource files...')
    compileResources()

    print('Install QGIS resource files')
    install_qgisresources()
    print('EnMAP-Box repository setup finished')


if __name__ == "__main__":
    print('setup repository')
    setup_enmapbox_repository()
