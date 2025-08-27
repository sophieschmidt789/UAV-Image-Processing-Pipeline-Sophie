from qgis.core import *
from qgis.utils import *
from PyQt5.QtCore import *
from qgis.analysis import *
from qgis.gui import *
import numpy as np

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--srcRaster", required=True,
    help="source raster file")
args = ap.parse_args()
sourceRaster = args.srcRaster

QgsApplication.setPrefixPath("C:/OSGeo4W64/apps/qgis", True)
qgs = QgsApplication([], False)
# load providers
qgs.initQgis()
crs = QgsCoordinateReferenceSystem("EPSG:4326")

orthoTiffInfo = QFileInfo(sourceRaster)
orthoTiffBaseName = orthoTiffInfo.baseName()
orthoTiffLayer = QgsRasterLayer(sourceRaster, orthoTiffBaseName)

orthoTiffLayer.renderer().setRedBand(3)
orthoTiffLayer.renderer().setGreenBand(2)
orthoTiffLayer.renderer().setBlueBand(1)

renderer = orthoTiffLayer.renderer()
provider = orthoTiffLayer.dataProvider()

layer_extent = orthoTiffLayer.extent()
uses_band = renderer.usesBands()
# print(uses_band)

redType = renderer.dataType(uses_band[0])
redStats = provider.bandStatistics(uses_band[0], QgsRasterBandStats.All, layer_extent, 0)

greenType = renderer.dataType(uses_band[1])
greenStats = provider.bandStatistics(uses_band[1], QgsRasterBandStats.All, layer_extent, 0)

blueType = renderer.dataType(uses_band[2])
blueStats = provider.bandStatistics(uses_band[2], QgsRasterBandStats.All, layer_extent, 0)

pixMin = np.max([redStats.minimumValue, greenStats.minimumValue, blueStats.minimumValue])
pixMax = np.min([redStats.maximumValue, greenStats.maximumValue, blueStats.maximumValue])
# pixMin = 2500
# pixMax = 18000

contrast_enhancement = QgsContrastEnhancement.StretchToMinimumMaximum

redEnhancement = QgsContrastEnhancement(redType)
redEnhancement.setContrastEnhancementAlgorithm(contrast_enhancement,True)
redEnhancement.setMinimumValue(pixMin)
redEnhancement.setMaximumValue(pixMax)
orthoTiffLayer.renderer().setRedContrastEnhancement(redEnhancement)

greenEnhancement = QgsContrastEnhancement(greenType)
greenEnhancement.setContrastEnhancementAlgorithm(contrast_enhancement,True)
greenEnhancement.setMinimumValue(pixMin)
greenEnhancement.setMaximumValue(pixMax)
orthoTiffLayer.renderer().setGreenContrastEnhancement(greenEnhancement)

blueEnhancement = QgsContrastEnhancement(blueType)
blueEnhancement.setContrastEnhancementAlgorithm(contrast_enhancement,True)
blueEnhancement.setMinimumValue(pixMin)
blueEnhancement.setMaximumValue(pixMax)
orthoTiffLayer.renderer().setBlueContrastEnhancement(blueEnhancement)

orthoTiffLayer.triggerRepaint()

extent = orthoTiffLayer.extent()
width = orthoTiffLayer.width()
height = orthoTiffLayer.height()
renderer = orthoTiffLayer.renderer()
provider = orthoTiffLayer.dataProvider()
crs = orthoTiffLayer.crs()     

pipe = QgsRasterPipe()
pipe.set(provider.clone())        
pipe.set(renderer.clone())

file_writer = QgsRasterFileWriter(str(sourceRaster).replace(".tif","_rgb_render.tif"))
file_writer.writeRaster(pipe, width, height, provider.extent(), crs)


qgs.exitQgis()



