import pathlib

from bitflagrenderer import DIR_RESOURCES
from qgis.testing import start_app
start_app()
from tests.qgispluginsupport.qps.resources import compileResourceFiles

def compileResources():

    directories = [DIR_RESOURCES]
    for d in directories:
        compileResourceFiles(d)

    print('Finished')


if __name__ == "__main__":
    compileResources()
