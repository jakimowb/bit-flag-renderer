import pathlib
import unittest
import re

from bitflagrenderer import DIR_REPO


class RepoTestCases(unittest.TestCase):
    def test_imports(self):
        """
        Ensure that QPS is not used inside /bitflagrenderer
        """

        from qps.utils import file_search

        rxTest1 = re.compile(r'^ *from.*[.]qps(\..*)? import.*')
        rxTest2 = re.compile(r'^ *import.*[.]qps(\..*)?')

        tests = [rxTest1, rxTest2]
        errors = []
        DIR_PKG = DIR_REPO / 'bitflagrenderer'
        for path in file_search(DIR_PKG, '*.py', recursive=True):
            path = pathlib.Path(path)
            with open(path, 'r', encoding='utf-8') as f:
                lastLine = None
                for i, line in enumerate(f.readlines()):
                    for rx in tests:
                        if rx.search(line):
                            errors.append(f'File "{path}", line {i + 1}, "{line.strip()}"')
                    lastLine = line
        self.assertTrue(len(errors) == 0, msg=f'{len(errors)} Absolute imports:\n' + '\n'.join(errors))


if __name__ == '__main__':
    unittest.main()
