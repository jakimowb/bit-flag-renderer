import argparse
import pathlib
import re
import site

from qps.utils import file_search

site.addsitedir(pathlib.Path(__file__).parents[1])

DIR_REPO = pathlib.Path(__file__).parents[1]

DIR_EXAMPLEDATA = DIR_REPO / 'bitflagrenderer' / 'exampledata'
assert DIR_EXAMPLEDATA.is_dir()
PATH_INIT = DIR_EXAMPLEDATA / '__init__.py'


def update_init(
        use_pathlib: bool = True,
        overwrite: bool = False):
    assert DIR_EXAMPLEDATA.is_dir()

    if not overwrite and PATH_INIT.is_file():
        raise Exception(f'File already exists: {PATH_INIT}.\nRun with option -o --overwrite')

    rx = re.compile(r'.*\.(tif|gpkg|qml|csv|pkl|json)$')

    FILES = dict()
    for file in file_search(DIR_EXAMPLEDATA, rx, recursive=True):
        path = pathlib.Path(file)
        part = path.relative_to(DIR_EXAMPLEDATA)

        varname = re.sub(r'[/\-*?.]', '_', part.as_posix())
        if use_pathlib:
            FILES[path] = f"{varname} = root / '{part}'"
        else:
            FILES[path] = f"{varname} = (root / '{part}').as_posix()"

    lines = ['#  autogenerated file. ',
             f'#  changes will be overwritten when running {pathlib.Path(__file__).relative_to(DIR_REPO)}',
             'import pathlib',
             'root = pathlib.Path(__file__).parent',
             '']
    for file in FILES.values():
        lines.append(file)
    lines.append('')

    with open(PATH_INIT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == "__main__":
    part = PATH_INIT.relative_to(DIR_REPO)
    parser = argparse.ArgumentParser(description=f'Updates path variable in {part}')
    parser.add_argument('-o', '--overwrite',
                        required=False,
                        default=True,
                        help='Overwrite existing __init__.py',
                        action='store_true')
    parser.add_argument('-p', '--pathlib',
                        required=False,
                        default=False,
                        help='Makes file paths available as pathlib.Path',
                        action='store_true')

    args = parser.parse_args()

    update_init(use_pathlib=args.pathlib, overwrite=args.overwrite)