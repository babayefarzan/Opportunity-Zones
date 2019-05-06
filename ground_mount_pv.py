import scipy, time, gdal, ogr, osr, csv
import numpy as np
import numpy as np
import pandas as pd
import geopandas as gpd
import os, os.path
import rasterio
from rasterio.plot import show
from osgeo import gdal, gdalconst
import matplotlib as mpl
import matplotlib.pyplot as plt
import pyproj
from pyproj import Proj
import shapely
from sqlalchemy import create_engine
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.geometry import MultiPolygon
import pathos.multiprocessing as mp
from pathos.parallel import stats
print(time.ctime(), " | Modules loaded.")

# check for missing data
filelist = []
inputpath = '/projects/kwaechte/data/rev_qoz/exclusion/geom/'
for file in os.listdir(inputpath):
    name = file.split("geom/")[0]
    filelist.append(name)

soz = gpd.read_file('/projects/kwaechte/data/rev_qoz/soz102008.shp')
soz.crs = {'init':'epsg:102008'}
footprints = gpd.read_file('/projects/kwaechte/data/rev_qoz/exclusion/footprints.shp')
footprints.crs = {'init':'epsg:102008'}

chunkstoprocess = gpd.overlay(soz, footprints, how='identity')
covered = chunkstoprocess
covered = covered[covered.location.notnull()]
print(len(covered.location.unique()))
# covered.tail(50)
tiles = []
tiles.append(covered.location.unique())
jsonlist = []
for file in tiles[0]:
    if file.endswith('.tif'):
        fileinputname = file
        filebasename = file.replace('.tif', '.geojson')
        jsonlist.append(filebasename)
        
originalfiles = []
for file in jsonlist:
    if file.endswith('.geojson'):
        name = file.split("exclusion/")[1]
        originalfiles.append(name)

print("FILES TO PROCESS:", len(filelist), filelist[0:4], "\n")
print("ORIGINAL FILES:", len(originalfiles), originalfiles[0:4], "\n")                    

missing = list(set(originalfiles) - set(filelist))
print("MISSING FILES:", len(missing), "\n", missing)

inputfilelist = []
for file in missing:
    inputfilelist.append("/projects/kwaechte/data/rev_qoz/exclusion/"+str(file))
print(inputfilelist)

def explode(indata):
    indf = indata
    outdf = gpd.GeoDataFrame(columns=indf.columns)
    for idx, row in indf.iterrows():
        if type(row.geometry) == Polygon:
            outdf = outdf.append(row, ignore_index=True)
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row]*recs, ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom, 'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf, ignore_index=True)
    return outdf

def mp_main_worker(df_list, cores):
    global DF_LIST
    DF_LIST = df_list
    
def mp_process_worker(_id):
    inputfilelist = DF_LIST[_id].copy()
    zones = soz.copy()
    print(_id, " | FILES FOR CORE:", len(inputfilelist))
    outputpath = '/projects/kwaechte/data/rev_qoz/exclusion/geom/'
    try:
        for file in inputfilelist:
            start = time.time()
            print(_id, "| Reading ", file)
            excluded = gpd.read_file(file)
            excluded.crs = {'init':'epsg:102008'}
            excluded = excluded.loc[excluded['DN'] == 1]
            print(_id, "| Starting overlay")
            chunkerase = gpd.overlay(zones, excluded, how='intersection')
            print(_id, "| Exploding multipolygons")
            exportme = explode(chunkerase)
            exportme['area_sqkm'] = exportme['geometry'].area/1000
            #GEOID10, DN, geometry, area_sqkm
            exportme = exportme.drop("DN", axis=1)
            print(_id, "| Saving to geom folder.")
            chunkname = file.split("/")[-1]
            exportme.to_file(outputpath+chunkname, driver = 'GeoJSON')
            end = time.time()
            print(_id, "|", time.ctime(), file, "processed.", end-start, "seconds")
        return file
    
    except Exception as e:
        print(_id, time.ctime(), " | ERROR |", e, "\nFILE:", file) 

def mp_func(df, cores):
    ids = np.arange(0, cores)  
    df_list = np.array_split(df, cores) # array of dataframes
    main_worker_inputs = (df_list, cores)
    pool = mp.Pool(cores, mp_main_worker, main_worker_inputs)
    results = pool.imap_unordered(mp_process_worker, ids)
    pool.close()
    pool.join()
    results_df = []
    for result in results:
        results_df.append(result)
    needcf = pd.concat(results_df)
    print("results combined\n")
    return needcf
    
#-----------------------------RUN MULTIPROCESSING FUNCTIONS-------------------------------------------------------------------------------

needcf = mp_func(inputfilelist, 2)

#----------------------------- EXTRACT GENERATION DATA FROM reV -------------------------------------------------------------------------------

#make postgres connection
host = ''
dbase = 'dav-gis'
user = 'kwaechte'
pwd = ''
con = create_engine('postgresql://{user}:{pwd}@{host}:5432/{dbase}'.format(host=host, dbase=dbase, user=user, pwd=pwd), echo=False)
connection = con.raw_connection()

generation = rasterio.open('/projects/kwaechte/data/rev_qoz/cf/tech_outputs/generation.tif')
show(generation)

def getXY(pt):
    return (pt.x, pt.y)

filelist = []
inputpath = '/projects/kwaechte/data/rev_qoz/exclusion/geom/'
for file in os.listdir(inputpath):
    filelist.append(inputpath+file)
print("FILES TO PROCESS:", len(filelist))
# filelist = filelist[:2]
# print(filelist)
try:
    df = pd.DataFrame({'geoid': [], 'sq_km': [], 'cf': [], 'kw': [], 'kwh': []})
    for file in filelist:
        start = time.time()
        areas = gpd.read_file(file)
        areas['x'] = areas.geometry.centroid.x
        areas['y'] = areas.geometry.centroid.y
        for i, polygon in areas.iterrows():
          pt = Point(polygon.x, polygon.y)
          poly = polygon['geometry']
          shape = shapely.geometry.asShape(poly)
          pt = Point(x,y)
          if pt.within(poly):
            geoid = polygon.GEOID10
            area_sqkm = polygon.area_sqkm
            for val in generation.sample([(polygon.x, polygon.y)]):
                #print(val, ":", polygon.x, polygon.y)
                pass
            cf = val[0] / 1000
            kw = area_sqkm * 32
            kwh = (kw * 8760) / cf
            if kw >= 100:
                df = df.append({'geoid':str(geoid), 'sq_km': area_sqkm, 'cf': cf, 'kw': kw, 'kwh': kwh}, ignore_index=True)
        print(file, "appended to df at ", time.ctime())

except Exception as e:
    print(e)
print("\nROWS:", len(df))

aggregations = {'sq_km':'sum', 'cf':'mean', 'kw':'mean', 'kwh': 'mean'}
agg = df.groupby('geoid').agg(aggregations)
print("Starting export to Postgres.")
name = 'soz_groundmount_agg'
schema = 'kwaechte'
agg.to_sql(name=name, con=con, schema=schema, if_exists='replace', index=False, chunksize=20000)
print("Export as ", schema, ".", name, " completed. ", time.ctime())

# once in postgres, join to geometry and symbolize for display in Solar For All
