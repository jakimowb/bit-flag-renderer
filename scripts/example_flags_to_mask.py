import pathlib
import numpy as np
from osgeo import gdal
ROOT = pathlib.Path(__file__).parents[1]

pathBQA = ROOT / 'exampledata' / 'LC08_L1TP_227065_20191129_20191216_01_T1.BQA.subset.tif'

assert pathBQA.is_file()

ds: gdal.Dataset = gdal.Open(pathBQA.as_posix())
array = ds.ReadAsArray()
