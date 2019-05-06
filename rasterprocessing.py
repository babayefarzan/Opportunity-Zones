```
To determine potential energy generation in IRS Qualified Opportunity Zones, potentially developable areas within zones must be identified. 
Identify developable areas by extracting land covers/uses to be excluded, including: 
* USFS Inventoried Roadless Areas  
* BLM Areas of Critical Ecological Concern  
* National parks, landmarks, and other protected federal lands
* Certain land cover types (National Land Cover Dataset, USGS)
* Built-up urban areas (Global Human Settlement Layers, GHSL > .5)
* Slope > 5% at 30 meter scale (Shuttle Radar Topopgraphy Mission)
```

# GET SLOPE IN GOOGLE EARTH ENGINE
```
var soz = ee.FeatureCollection('ft:1AtgfW9U_Nmqe0HBjSpn8shbYUisdbSBIga5nRvX6');

var conus_landmass = ee.Image("users/dylanhatlas/NREL/conus_landmass");

var tracts = ee.FeatureCollection("TIGER/2010/Tracts_DP1");
// var soz: Fusion Table "soz" (8763 rows, 4 columns)
// var roi = ee.Feature(soz, {geometry:'geometry'});

print('soz loaded')
var dataset = ee.Image('USGS/SRTMGL1_003');
var elevation = dataset.select('elevation');
var slope = ee.Terrain.slope(elevation);
var slopeClass = ee.Image(0)
slopeClass = slopeClass.where(slope.gt(1.6),1)// only include pixels < 5%
Map.setCenter(-105, 36.2841, 4.5);
// Map.addLayer(slope, {min: 0, max: 1.5}, 'slope');
// Map.addLayer(slopeClass, {}, 'acceptableslope');
Map.addLayer(soz, {}, 'soz');
var scale = slope.projection().nominalScale();
print('SCALE IN METERS', scale);
var clippedSlope = slopeClass.clip(soz);
// Map.addLayer(clippedSlope, {}, 'clippedSlope');

// Export slope to G Drive
Export.image.toDrive({
  image: clippedSlope.int8(),
  description: "exclude",
  folder: "gee",
  region: conus_landmass.geometry().bounds(),
  maxPixels:1e13,
  // region: ee.Feature(soz).geometry().bounds(),
  // region: clippedSlope.geometry(), 
  scale: 30,
  fileFormat: 'GeoTIFF'
});
```

import numpy as np
import gdal, os, rasterio, time

### Get info about raster w/o graphic preview (too big for memory) 
def describeraster(raster):
  filepath = "/projects/kwaechte/data/rev_qoz/"+str(raster)+".tif"
  data = rasterio.open(filepath)
  print("META:\n", data.meta)
  array = data.read()
  stats = []
  for band in array:
    stats.append({'min':band.min(), 'max':band.max(), 'mean':band.mean(), 'unique': numpy.unique(band)})
  print(filepath+" DESCRIPTION:\n", stats)
  pixelSizeX, pixelSizeY = data.res
  print('RESOLUTION (x,y):', pixelSizeX, pixelSizeY)


python gdal_reclassify.py /projects/kwaechte/data/rev_qoz/usa_esri_parks.tif /projects/kwaechte/data/rev_qoz/parks_reclass.tif -c "==255, ==1" -r "0, 1"
python gdal_reclassify.py /projects/kwaechte/data/rev_qoz/usa_usfs_ira.tif /projects/kwaechte/data/rev_qoz/usfsira_reclass.tif -c "==255, ==1" -r "0, 1"
python gdal_reclassify.py /projects/kwaechte/data/rev_qoz/usa_blm_acec.tif /projects/kwaechte/data/rev_qoz/blmacec_reclass.tif -c "==255, ==1" -r "0, 1"
python gdal_reclassify.py /projects/kwaechte/data/rev_qoz/usa_esri_landmarks.tif /projects/kwaechte/data/rev_qoz/landmarks_reclass.tif -c "==255, ==1" -r "0, 1"
gdal_calc.py -A '/projects/kwaechte/data/rev_qoz/t5_reclass.tif' -B '/projects/kwaechte/data/rev_qoz/t2_reclass.tif' --outfile='/projects/kwaechte/data/rev_qoz/f1.tif' --calc="A+B" --NoDataValue=0
gdal_calc.py -A '/projects/kwaechte/data/rev_qoz/t3_reclass.tif' -B '/projects/kwaechte/data/rev_qoz/t1_reclass.tif' --outfile='/projects/kwaechte/data/rev_qoz/f2.tif' --calc="A+B" --NoDataValue=0
gdal_calc.py -A '/projects/kwaechte/data/rev_qoz/f2_reclass.tif' -B '/projects/kwaechte/data/rev_qoz/f1_reclass.tif' --outfile='/projects/kwaechte/data/rev_qoz/f3.tif' --calc="A+B" --NoDataValue=0


## chunk data (too big/too much mem to process in 1 go)
# input = compressed exclusion raster
width = 48640
height = 33792
tilesize = 4096
gdal_string = []
for i in range(0, width, tilesize):
    for j in range(0, height, tilesize):
        gdaltranString = "gdal_translate -of GTIFF -srcwin "+str(i)+", "+str(j)+", "+str(tilesize)+", "+str(tilesize)+" /projects/kwaechte/data/rev_qoz/exclusion_c.tif n_"+str(i)+"_"+str(j)+".tif"
        gdal_string.append(gdaltranString)
        os.system(gdaltranString)
        print(time.ctime()," | ", i, j)

# make a polygon representation of raster footprints: Use footprints coverage to see if any gaps remain in coverage.
gdaltindex /projects/kwaechte/data/rev_qoz/exclusion/footprints.shp /projects/kwaechte/data/rev_qoz/exclusion/*.tif

# for raster chunks directory, convert all to polygons (gdal_polygonize derivative) GeoJSONs
for filename in /projects/kwaechte/data/rev_qoz/slope/*.tif; do gdal_polygonize.py $filename -f "GeoJSON" ${filename::-4}.geojson; done
