#don't forget to set conda env (python37)

#import modules + packages
import numpy as np
import pandas as pd
import geopandas as gpd
import os, os.path
import ogr, osr, time, rasterio, csv, scipy, pyproj
from osgeo import gdal, gdalconst
import matplotlib as mpl
import matplotlib.pyplot as plt
from rasterio.plot import show, show_hist
from rasterio._crs import _CRS
from fiona.crs import from_epsg
from shapely.geometry import Polygon, MultiPolygon
print("modules loaded\n")

print("loading data\n")
soz = gpd.read_file('/projects/kwaechte/data/rev_qoz/soz102008.geojson')
soz.crs = {'init':'epsg:102008'}
print("SOZ loaded")
basepath = "/projects/kwaechte/data/rev_qoz/"
vslope = "slope_9001.tif"
slope = rasterio.open(basepath+vslope)
print("2: slope\n")
show((slope, 1), cmap='terrain')

def describeraster(raster):
    filepath = "/projects/kwaechte/data/rev_qoz/"+str(raster)+".tif"
    data = rasterio.open(filepath)
    print("META:\n", data.meta)
    array = data.read()
    stats = []
    for band in array:
        stats.append({'min':band.min(), 'max':band.max(), 'mean':band.mean(), 'unique': np.unique(band)})
    print(filepath+" DESCRIPTION:\n", stats)
    pixelSizeX, pixelSizeY = data.res
    print('RESOLUTION (x,y):', pixelSizeX, pixelSizeY)
    
describeraster('slope_9001')

single_soz = soz.geometry.explode()
print(single_soz.geom_type)
single_soz = gpd.GeoDataFrame(single_soz)


boxes = pd.DataFrame({'index': [], 'geometry': [], 'xmax': [], 'ymax': [], 'xmin': [], 'ymin': []})
for i, row in single_soz.iterrows():
    geom = row.geometry
    vertices = np.array(geom.exterior)
    # max x = east, max y = north
    east = max(vertices[:], key=lambda item:item[0])
    north = max(vertices[:], key=lambda item:item[1])
    west = min(vertices[:], key=lambda item:item[0])
    south = min(vertices[:], key=lambda item:item[1])
    xmax = east[0]
    ymax = north[1]
    xmin = west[0]
    ymin = south[1]
    bbox = box(xmin, ymin, xmax, ymax)
    boxes = boxes.append({'index': i, 'geometry': bbox, 'xmax': xmax, 'ymax': ymax, 'xmin': xmin, 'ymin': ymin}, ignore_index=True)
# #     print("Max:", coordmax, "Min:", coordmin, "East:", east, "North:", north, "South:", south, "West:", west, "\n")

crs = {'init': 'epsg:102008'}
geo = gpd.GeoDataFrame(boxes, crs=crs, geometry='geometry')

print("bounding coords generated")
geo.plot()
geo.tail(5)

### created to define extents to clip large rasters to
