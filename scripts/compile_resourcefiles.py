import pathlib


def compileResources():
    from qps.resources import compileResourceFiles

    DIR_REPO = pathlib.Path(__file__).parents[1]
    directories = [DIR_REPO / 'bitflagrenderer',
                   ]
    for d in directories:
        compileResourceFiles(d)

    print('Finished')


if __name__ == "__main__":
    compileResources()
