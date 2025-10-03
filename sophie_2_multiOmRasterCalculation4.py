'''
Created on Oct 9, 2018

Revised on Nov 16, 2023

updated on May 9, 2024 by K.

@author: xuwang
'''
# import os
from qgis.core import *
from qgis.utils import *
from PyQt5.QtCore import *
from qgis.analysis import *
from qgis.gui import *
import os
import argparse

QgsApplication.setPrefixPath("C:/OSGeo4W64/apps/qgis", True)
qgs = QgsApplication([], False)
# load providers
qgs.initQgis()
crs = QgsCoordinateReferenceSystem("EPSG:4326")

#------------------------------------------------------------------------
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--srcFolder", required=True,
    help="source images")
#==============
# ap.add_argument("-t", "--targetFolder", required=True,
#     help="target folder")
#==============
args = ap.parse_args()
filePath = args.srcFolder
# targetPath = args.targetFolder
# Create list of all images
exten = 'ortho.tif'
imList=[]
for dirpath, dirnames, files in os.walk(filePath):
    for name in files:
        if name.lower().endswith(exten):
            imList.append(os.path.join(dirpath, name))
print("Total images in the path: %d" % len(imList))

for im in imList:
# Raster layer define
    orthoTiffInfo = QFileInfo(im)
    orthoTiffBaseName = orthoTiffInfo.baseName()
    orthoTiffLayer = QgsRasterLayer(im, orthoTiffBaseName)
    if not orthoTiffLayer.isValid():
        print("Layer failed to load!")
    # Tiff saving define
    imFileName = str(im)

    # update on May 30 2024
    atsaviTiff = imFileName.replace(".tif","_ATSAVI.tif")
    ari2Tiff = imFileName.replace(".tif","_ARI2.tif")
    arvi2Tiff = imFileName.replace(".tif","_ARVI2.tif")
    blueTiff = imFileName.replace(".tif","_B.tif")
    bndviTiff = imFileName.replace(".tif", "_BNDVI.tif")
    ccciTiff = imFileName.replace(".tif","_CCCI.tif")
    ciTiff = imFileName.replace(".tif", "_CI.tif")
    cigTiff = imFileName.replace(".tif","_CIG.tif")
    cireTiff = imFileName.replace(".tif","_CIRE.tif")
    civeTiff = imFileName.replace(".tif", "_CIVE.tif")
    cviTiff = imFileName.replace(".tif","_CVI.tif")
    dviTiff = imFileName.replace(".tif", "_DVI.tif")
    eviTiff = imFileName.replace(".tif","_EVI.tif")
    evi2Tiff = imFileName.replace(".tif", "_EVI2.tif")
    exgTiff = imFileName.replace(".tif", "_ExG.tif")
    gariTiff = imFileName.replace(".tif", "_GARI.tif")
    gbndviTiff = imFileName.replace(".tif", "_GBNDVI.tif")
    grndviTiff = imFileName.replace(".tif", "_GRNDVI.tif")
    gdviTiff = imFileName.replace(".tif","_GDVI.tif")
    gemiTiff = imFileName.replace(".tif", "_GEMI.tif")
    gliTiff = imFileName.replace(".tif","_GLI.tif")
    greenTiff = imFileName.replace(".tif","_G.tif")
    grviTiff = imFileName.replace(".tif", "_GRVI.tif")
    gsaviTiff = imFileName.replace(".tif","_GSAVI.tif")
    hueTiff = imFileName.replace(".tif", "_H.tif")
    ifTiff = imFileName.replace(".tif", "_IF.tif")
    ioTiff = imFileName.replace(".tif", "_IO.tif")
    ipviTiff = imFileName.replace(".tif", "_IPVI.tif")
    intensityTiff = imFileName.replace(".tif", "_I.tif")
    logRTiff = imFileName.replace(".tif", "_LogR.tif")
    msrNirRedTiff = imFileName.replace(".tif", "_MSRNirRed.tif")
    msaviTiff = imFileName.replace(".tif","_MSAVI.tif")    
    ndviTiff = imFileName.replace(".tif","_NDVI.tif")
    ndviRededgeTiff = imFileName.replace(".tif", "_NDVIrededge.tif")
    ndreTiff = imFileName.replace(".tif","_NDRE.tif")
    ngrdiTiff = imFileName.replace(".tif","_NGRDI.tif")
    nirTiff = imFileName.replace(".tif","_NIR.tif")
    normGTiff = imFileName.replace(".tif", "_NormG.tif")
    normNIRTiff = imFileName.replace(".tif", "_NormNIR.tif")
    normRTiff = imFileName.replace(".tif", "_NormR.tif")
    osaviTiff = imFileName.replace(".tif","_OSAVI.tif")
    pndviTiff = imFileName.replace(".tif", "_PNDVI.tif")
    rbndviTiff = imFileName.replace(".tif", "_RBNDVI.tif")
    redEdgeTiff = imFileName.replace(".tif","_RE.tif")
    redTiff = imFileName.replace(".tif","_R.tif")
    rgrTiff = imFileName.replace(".tif", "_RGR.tif")
    riTiff = imFileName.replace(".tif", "_RI.tif")
    rri1Tiff = imFileName.replace(".tif", "_RRI1.tif")
    rri2Tiff = imFileName.replace(".tif", "_RRI2.tif")
    sqrtIRRTiff = imFileName.replace(".tif", "_SQRTIRR.tif")
    srNIRRedTiff = imFileName.replace(".tif", "_SRNIRRed.tif")
    tndviTiff = imFileName.replace(".tif", "_TNDVI.tif")
    wdrviTiff = imFileName.replace(".tif", "_WDRVI.tif")
    
    # Define each band within the ortho raster layer
    entries = []
    
    # Define red band
    redBand = QgsRasterCalculatorEntry()
    redBand.ref = orthoTiffLayer.name()+'@3'
    redBand.raster = orthoTiffLayer
    redBand.bandNumber = 3
    entries.append(redBand)
    
    # Define green band
    greenBand = QgsRasterCalculatorEntry()
    greenBand.ref = orthoTiffLayer.name()+'@2'
    greenBand.raster = orthoTiffLayer
    greenBand.bandNumber = 2
    entries.append(greenBand)
    
    # Define blue band
    blueBand = QgsRasterCalculatorEntry()
    blueBand.ref = orthoTiffLayer.name()+'@1'
    blueBand.raster = orthoTiffLayer
    blueBand.bandNumber = 1
    entries.append(blueBand)
    
    # Define redEdge band
    redEdgeBand = QgsRasterCalculatorEntry()
    redEdgeBand.ref = orthoTiffLayer.name()+'@4'
    redEdgeBand.raster = orthoTiffLayer
    redEdgeBand.bandNumber = 4
    entries.append(redEdgeBand)
    
    # Define Nir band
    nirBand = QgsRasterCalculatorEntry()
    nirBand.ref = orthoTiffLayer.name()+'@5'
    nirBand.raster = orthoTiffLayer
    nirBand.bandNumber = 5
    entries.append(nirBand)
    
    # Generate red Tiff
    genRed = QgsRasterCalculator(redBand.ref,
        redTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genRed.processCalculation()
    
    # Generate green Tiff
    genGreen = QgsRasterCalculator(greenBand.ref,
        greenTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genGreen.processCalculation()
    
    # Generate blue Tiff
    genBlue = QgsRasterCalculator(blueBand.ref,
        blueTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genBlue.processCalculation()
    
    # Generate redEdge Tiff
    genRedEdge = QgsRasterCalculator(redEdgeBand.ref,
        redEdgeTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genRedEdge.processCalculation()
    
    # Generate Nir Tiff
    genNir = QgsRasterCalculator(nirBand.ref,
        nirTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genNir.processCalculation()
    
    # Generate NDVI Tiff
    genNDVI = QgsRasterCalculator('( '+nirBand.ref+' - '+redBand.ref+' ) / ( '+nirBand.ref+' + '+redBand.ref+' )',
        ndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genNDVI.processCalculation()
    
    # Generate NDRE Tiff
    genNDRE = QgsRasterCalculator('( ' +nirBand.ref+ ' - ' +redEdgeBand.ref+ ' ) / ( ' +nirBand.ref+ ' + ' +redEdgeBand.ref+ ' )',
        ndreTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genNDRE.processCalculation()
    
    # Generate CCCI Tiff
    genCCCI = QgsRasterCalculator(
        '( ' + nirBand.ref + ' - ' + redEdgeBand.ref + ' ) * ( ' +nirBand.ref+ ' + ' +redBand.ref+ ' ) / ( '
        + nirBand.ref + ' + ' + redEdgeBand.ref + ' ) / ( ' +nirBand.ref+ ' - ' +redBand.ref+ ' )' ,
        ccciTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries)
    genCCCI.processCalculation()

    # # Generate RVI Tiff
    # genMRVI = QgsRasterCalculator( '( ' + nirBand.ref+ ' ) / ( ' +redBand.ref+ ' )',
        # mrviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    # genMRVI.processCalculation()

    # Generate ExG Tiff (https://plantmethods.biomedcentral.com/articles/10.1186/s13007-019-0402-3/tables/6)
    #genExG = QgsRasterCalculator('2 * ' +greenBand.ref+ ' - ' +redBand.ref+ ' - ' +blueBand.ref,
      #  exgTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genExG.processCalculation()

    # Generate CIVE Tiff (https://www.redalyc.org/journal/4457/445758367004/html/)
    genCIVE = QgsRasterCalculator('0.441 * ' +redBand.ref+ ' - 0.811 * ' +greenBand.ref+ ' + 0.385 * ' +blueBand.ref+ ' + 18.78745',
        civeTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    genCIVE.processCalculation()

    # Generate ATSAVI Tiff (Adjusted transformed soil-adjusted VI)
  #  numerator_part1 = '1.22 * (' + nirBand.ref + ' - 1.22 * ' + redBand.ref + ' - 0.03)'
  #  denominator_part1 = '1.22 * ' + nirBand.ref + ' + ' + redBand.ref
   # denominator_part2 = ' - 1.22 * 0.03 + 0.08 * (1 + 1.22 * 1.22)'

   # formula = numerator_part1 + '/(' + denominator_part1 + denominator_part2 + ')'

   # genATSAVI = QgsRasterCalculator(
     #   formula,
     #   atsaviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries
   # )
   # genATSAVI.processCalculation()
    
    # Generate OSAVI Tiff
  #  genOSAVI = QgsRasterCalculator(
  #      '( ' + nirBand.ref + ' - ' + redBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + redBand.ref + ' + 0.16 ) * ( 1 + 0.16 )',
  #      osaviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries)
  #  genOSAVI.processCalculation()

    # Generate GDVI Tiff (Generalized Difference Vegetation Index )
#    genGDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - ' + greenBand.ref + ' )',    
 #       gdviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genGDVI.processCalculation()

    # Generate GLI Tiff (Green leaf Index )
  #  genGLI = QgsRasterCalculator('(2 * ' + greenBand.ref + ' - ' + redBand.ref + ' - ' + blueBand.ref + ') / (2 * ' + greenBand.ref + ' + ' + redBand.ref + ' + ' + blueBand.ref + ')',   
  #      gliTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genGLI.processCalculation()
    
    # Generate GSAVI Tiff (Green Soil Adjusted Vegetation Index)
  #  genGSAVI = QgsRasterCalculator('( ' + nirBand.ref + ' - ' + greenBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + greenBand.ref + ' + 0.5 ) * (1.5)',   
#        gsaviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genGSAVI.processCalculation()    

    # Generate NGRDI Tiff (Normalized Difference Green/Red Normalized green red difference index)
  #  genNGRDI = QgsRasterCalculator('( ' + greenBand.ref + ' - ' + redBand.ref + ' ) / ( ' + greenBand.ref + ' + ' + redBand.ref + ' )',   
   #     ngrdiTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genNGRDI.processCalculation()    

    # Generate ARI2 Tiff (Anthocyanin Reflectance Index 2)
   # genARI2 = QgsRasterCalculator('(1 / (' + greenBand.ref + ') - 1 / (' + redEdgeBand.ref + ')) * ( ' + nirBand.ref + ')',
    #    ari2Tiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genARI2.processCalculation()  

	# Generate ARVI2 Tiff
   # genARVI2 = QgsRasterCalculator('-0.18 + 1.17 * (( ' + nirBand.ref + ' - ' + redBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + redBand.ref + ' ))',
	#	arvi2Tiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries)
#    genARVI2.processCalculation()

	# Generate CI Tiff (Color Index)
 #   genCI = QgsRasterCalculator('( ' + redBand.ref + ' - ' + blueBand.ref + ' ) / ( ' + redBand.ref + ' )',
  #      ciTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genCI.processCalculation()

    # Generate CIG Tiff (Chlorophyll Index Green)
    #genCIG = QgsRasterCalculator('( ' + nirBand.ref + ' / ' + greenBand.ref + ' ) - 1',
     #   cigTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genCIG.processCalculation()  

    # Generate CIRE Tiff (Chlorophyll Index Red Edge)
   # genCIRE = QgsRasterCalculator('(' + nirBand.ref + ' / ' + redEdgeBand.ref + ') - 1',
    #    cireTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genCIRE.processCalculation()
    
    # Generate CVI Tiff Chlorophyll vegetation index
   # genCVI = QgsRasterCalculator('( ' + nirBand.ref + ' * ( ' + redBand.ref + ' ) / ( ' + greenBand.ref + ' * ' + greenBand.ref + ' ))',
	#	cviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    #genCVI.processCalculation()

    # Generate EVI Tiff (Enhanced Vegetation Index)
   # genEVI = QgsRasterCalculator('2.5 * (( ' + nirBand.ref + ' - ' + redBand.ref + ' ) / (( ' + nirBand.ref + ' + 6 * ' + redBand.ref + ' - 7.5 * ' + blueBand.ref + ' ) + 1))',
    #    eviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genEVI.processCalculation()

	# Generate EVI2 Tiff (Enhanced Vegetation Index 2)
    #genEVI2 = QgsRasterCalculator('2.4 * ( ' + nirBand.ref + ' - ' + redBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + redBand.ref + ' + 1 )',
    #    evi2Tiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    #genEVI2.processCalculation()

	# Generate GARI Tiff (Green Atmospherically Resistant Vegetation Index)
    #genGARI = QgsRasterCalculator('( ' + nirBand.ref + ' - (' + greenBand.ref + ' - (' + blueBand.ref + ' - ' + redBand.ref + ')) ) / ( ' + nirBand.ref + ' - (' + greenBand.ref + ' + (' + blueBand.ref + ' - ' + redBand.ref + ')) )',
	#	gariTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    #genGARI.processCalculation()

	# Generate GBNDVI Tiff (Green-Blue NDVI)
    #genGBNDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - (' + greenBand.ref + ' + ' + blueBand.ref + ') ) / ( ' + nirBand.ref + ' + (' + greenBand.ref + ' + ' + blueBand.ref + ') )',
	#	gbndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genGBNDVI.processCalculation()

	# Generate GRNDVI Tiff (Green-Red NDVI)
   # genGRNDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - (' + greenBand.ref + ' + ' + redBand.ref + ') ) / ( ' + nirBand.ref + ' + (' + greenBand.ref + ' + ' + redBand.ref + ') )',
#		grndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genGRNDVI.processCalculation()

	# Generate GEMI Tiff (Global Environmental Monitoring Index)
  #  part1 = '2 * ((' + nirBand.ref + ' ^ 2) - (' + redBand.ref + ' ^ 2))'
   # part2 = '1.5 * ' + nirBand.ref + ' + 0.5 * ' + redBand.ref
    #numerator = part1 + ' + ' + part2
    #denominator = nirBand.ref + ' + ' + redBand.ref + ' + 0.5'
   # fraction = '(' + numerator + ')/(' + denominator + ')'
   # gemi_part1 = '(' + fraction + ')*(1 - 0.25*(' + fraction + '))'
   # gemi_part2 = '(' + redBand.ref + ' - 0.125)/(1 - ' + redBand.ref + ')'
   # gemi_formula = gemi_part1 + ' - ' + gemi_part2

   # genGEMI = QgsRasterCalculator(
   #     gemi_formula,
   #     gemiTiff,
   #     'GTiff',
   #     orthoTiffLayer.extent(),
   #     orthoTiffLayer.width(),
   #     orthoTiffLayer.height(),
   #     entries
    #)
    #genGEMI.processCalculation()

    # Generate H Tiff (Hue)
    #genH = QgsRasterCalculator('atan((2 * ' + redBand.ref + ' - ' + greenBand.ref + ' - ' + blueBand.ref + ') / (30.5 * (' + greenBand.ref + ' - ' + blueBand.ref + ')))',
    #    hueTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    #genH.processCalculation()

	# Generate IPVI Tiff (Infrared Percentage Vegetation Index)
  #  genIPVI = QgsRasterCalculator('( ' + nirBand.ref + ' / (( ' + nirBand.ref + ' + ' + redBand.ref + ' ) / 2) ) * (( ' + nirBand.ref + ' - ' + redBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + redBand.ref + ' ) + 1)',
#		ipviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genIPVI.processCalculation()

	# Generate I Tiff (Intensity)
  #  genIntensity = QgsRasterCalculator('(1 / 30.5) * (' + redBand.ref + ' + ' + greenBand.ref + ' + ' + blueBand.ref + ')',
	#	intensityTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
#    genIntensity.processCalculation()
    
    # Generate MSAVI  Tiff (Modified Soil Adjusted Vegetation Index)
 #   genMSAVI = QgsRasterCalculator('((2 * ' + nirBand.ref + ' + 1) - ((((2 * ' + nirBand.ref + ' + 1) ^ 2) - 8 * (' + nirBand.ref + ' - ' + redBand.ref + ')) ^ (1/2))) / 2',
  #      msaviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genMSAVI.processCalculation()
    
	# Generate LogR Tiff (Log Ratio)
 #   genLogR = QgsRasterCalculator('log10(' + nirBand.ref + ' / ' + redBand.ref + ')',
	#	logRTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genLogR.processCalculation()

	# Generate MSRNir/Red Tiff (Modified Simple Ratio NIR/RED)
    #genMSRNirRed = QgsRasterCalculator('(( ' + nirBand.ref + ' / ' + redBand.ref + ' ) - 1) / (sqrt( ' + nirBand.ref + ' / ' + redBand.ref + ' ) + 1)',
#		msrNirRedTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genMSRNirRed.processCalculation()

	# Generate Norm G Tiff (Normalized Green)
  #  genNormG = QgsRasterCalculator('(' + greenBand.ref + ') / (' + nirBand.ref + ' + ' + redBand.ref + ' + ' + greenBand.ref + ')',
	#	normGTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genNormG.processCalculation()

	# Generate Norm NIR Tiff (Normalized Near-Infrared)
  #  genNormNIR = QgsRasterCalculator('(' + nirBand.ref + ') / (' + nirBand.ref + ' + ' + redBand.ref + ' + ' + greenBand.ref + ')',
#		normNIRTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genNormNIR.processCalculation()

	# Generate Norm R Tiff (Normalized Red)
  #  genNormR = QgsRasterCalculator('(' + redBand.ref + ') / (' + nirBand.ref + ' + ' + redBand.ref + ' + ' + greenBand.ref + ')',
#		normRTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genNormR.processCalculation()

	# Generate BNDVI Tiff (Blue-normalized difference vegetation index)
  #  genBNDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - ' + blueBand.ref + ' ) / ( ' + nirBand.ref + ' + ' + blueBand.ref + ' )',
	#	bndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genBNDVI.processCalculation()

	# Generate RI Tiff (Redness Index)
    #genRI = QgsRasterCalculator('( ' + redBand.ref + ' - ' + greenBand.ref + ' ) / ( ' + redBand.ref + ' + ' + greenBand.ref + ' )',
	#	riTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
    #genRI.processCalculation()

	# Generate NDVI Rededge Tiff (Normalized Difference Rededge/Red)
  #  genNDVIRededge = QgsRasterCalculator('( ' + redEdgeBand.ref + ' - ' + redBand.ref + ' ) / ( ' + redEdgeBand.ref + ' + ' + redBand.ref + ' )',
	#	ndviRededgeTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genNDVIRededge.processCalculation()

	# Generate PNDVI Tiff (Pan NDVI)
#    genPNDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - (' + greenBand.ref + ' + ' + redBand.ref + ' + ' + blueBand.ref + ') ) / ( ' + nirBand.ref + ' + (' + greenBand.ref + ' + ' + redBand.ref + ' + ' + blueBand.ref + ') )',
#		pndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genPNDVI.processCalculation()

	# Generate RBNNDVI Tiff (Red-Blue NDVI)
  #  genRBNDVI = QgsRasterCalculator('( ' + nirBand.ref + ' - (' + redBand.ref + ' + ' + blueBand.ref + ') ) / ( ' + nirBand.ref + ' + (' + redBand.ref + ' + ' + blueBand.ref + ') )',
#		rbndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genRBNDVI.processCalculation()

	# Generate IF Tiff (Shape Index)
  #  genIF = QgsRasterCalculator('(2 * ' + redBand.ref + ' - ' + greenBand.ref + ' - ' + blueBand.ref + ') / (' + greenBand.ref + ' - ' + blueBand.ref + ')',
#		ifTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genIF.processCalculation()

#	# Generate GRVI Tiff (Green Ratio Vegetation Index)
 #   genGRVI = QgsRasterCalculator('(' + nirBand.ref + ') / (' + greenBand.ref + ')',
	#	grviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genGRVI.processCalculation()

	# Generate DVI Tiff (Difference Vegetation Index)
#    genDVI = QgsRasterCalculator('(' + nirBand.ref + ') / (' + redBand.ref + ')',
#		dviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genDVI.processCalculation()

	# Generate RRI1 Tiff (RedEdge Ratio Index 1)
  #  genRRI1 = QgsRasterCalculator('(' + nirBand.ref + ') / (' + redEdgeBand.ref + ')',
	#	rri1Tiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genRRI1.processCalculation()

	# Generate IO Tiff (Simple Ratio Red/Blue Iron Oxide Iron Oxide)
   # genIO = QgsRasterCalculator('(' + redBand.ref + ') / (' + blueBand.ref + ')',
#		ioTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genIO.processCalculation()

	# Generate RGR Tiff (Red-Green Ratio)
  #  genRGR = QgsRasterCalculator('(' + redBand.ref + ') / (' + greenBand.ref + ')',
	#	rgrTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genRGR.processCalculation()

	# Generate SR NIR/Red Tiff (Simple Ratio NIR/Red)
   # genSR = QgsRasterCalculator('(' + nirBand.ref + ') / (' + redBand.ref + ')',
    #    srNIRRedTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genSR.processCalculation()

	# Generate RRI2 Tiff (RedEdge Ratio Index 2)
   # genRRI2 = QgsRasterCalculator('(' + redEdgeBand.ref + ') / (' + redBand.ref + ')',
	#	rri2Tiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
  #  genRRI2.processCalculation()

	# Generate SQRT(IR/R) Tiff (Square Root of Infrared/Red)
   # genSQRTIRR = QgsRasterCalculator('sqrt(' + nirBand.ref + ' / ' + redBand.ref + ')',
#		sqrtIRRTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
 #   genSQRTIRR.processCalculation()

	# Generate TNDVI Tiff (Transformed NDVI)
  #  genTNDVI = QgsRasterCalculator('sqrt((' + nirBand.ref + ' - ' + redBand.ref + ') / (' + nirBand.ref + ' + ' + redBand.ref + ') + 0.5)',
	#	tndviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
   # genTNDVI.processCalculation()

	# Generate WDRVI Tiff (Wide Dynamic Range Vegetation Index)
    #genWDRVI = QgsRasterCalculator('(0.1 * ' + nirBand.ref + ' - ' + redBand.ref + ') / (0.1 * ' + nirBand.ref + ' + ' + redBand.ref + ')',
	#	wdrviTiff, 'GTiff', orthoTiffLayer.extent(), orthoTiffLayer.width(), orthoTiffLayer.height(), entries )
#    genWDRVI.processCalculation()

qgs.exitQgis()
