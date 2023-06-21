import pathlib

from bitflagrenderer import DIR_RESOURCES


def compileResources():
    from qps.resources import compileResourceFiles

    directories = [DIR_RESOURCES]
    for d in directories:
        compileResourceFiles(d)

    print('Finished')


if __name__ == "__main__":
    compileResources()
