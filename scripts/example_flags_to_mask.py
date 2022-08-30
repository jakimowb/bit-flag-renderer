from osgeo import gdal

from bitflagrenderer.exampledata import LC08_L1TP_227065_20191129_20191216_01_T1_BQA_subset_tif as pathBQA

assert pathBQA.is_file()

ds: gdal.Dataset = gdal.Open(pathBQA.as_posix())
array = ds.ReadAsArray()
