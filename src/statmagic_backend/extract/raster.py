import numpy as np

from statmagic_backend.geo.transform import geotFromOffsets, boundingBoxToOffsets
import logging
logger = logging.getLogger("statmagic_backend")


def extractBands(bands2KeepList, RasterDataSet):
    bandDataList = []
    for band in bands2KeepList:
        rbds = RasterDataSet.GetRasterBand(band).ReadAsArray()
        bandDataList.append(rbds)
    datastack = np.vstack([bandDataList])
    return datastack

def extractBandsInBounds(bands2KeepList, RasterDataSet, x, y, rows, cols):
    bandDataList = []
    for band in bands2KeepList:
        rbds = RasterDataSet.GetRasterBand(band).ReadAsArray(x, y, rows, cols)
        bandDataList.append(rbds)
    datastack = np.vstack([bandDataList])
    return datastack

def getFullRasterDict(raster_dataset):
    geot = raster_dataset.GetGeoTransform()
    cellres = geot[1]
    nodata = raster_dataset.GetRasterBand(1).GetNoDataValue()
    r_proj = raster_dataset.GetProjection()
    rsizeX, rsizeY = raster_dataset.RasterXSize, raster_dataset.RasterYSize
    raster_dict = {'resolution': cellres, 'NoData': nodata, 'Projection': r_proj, 'sizeX': rsizeX, 'sizeY': rsizeY,
                   'GeoTransform': geot}
    return raster_dict

def getCanvasRasterDict(raster_dict, canvas_bounds):
    canvas_dict = raster_dict.copy()
    canvas_bounds.asWktCoordinates()
    bbc = [canvas_bounds.xMinimum(), canvas_bounds.yMinimum(), canvas_bounds.xMaximum(), canvas_bounds.yMaximum()]
    offsets = boundingBoxToOffsets(bbc, raster_dict['GeoTransform'])
    x_off, y_off = offsets[2], offsets[0]
    new_geot = geotFromOffsets(offsets[0], offsets[2], raster_dict['GeoTransform'])
    sizeX = int(((bbc[2] - bbc[0]) / raster_dict['resolution']) + 1)
    sizeY = int(((bbc[3] - bbc[1]) / raster_dict['resolution']) + 1)

    canvas_dict['GeoTransform'] = new_geot
    canvas_dict['sizeX'] = sizeX
    canvas_dict['sizeY'] = sizeY
    canvas_dict['Xoffset'] = x_off
    canvas_dict['Yoffset'] = y_off

    return canvas_dict

def getFullRasterDict_rio(raster_dataset):
    geot = raster_dataset.transform
    cellres = raster_dataset.res[0]
    nodata = raster_dataset.nodata
    r_proj = raster_dataset.crs
    rsizeX, rsizeY = raster_dataset.shape[1], raster_dataset.shape[0]
    raster_dict = {'resolution': cellres, 'NoData': nodata, 'Projection': r_proj, 'sizeX': rsizeX, 'sizeY': rsizeY,
                   'GeoTransform': geot}
    return raster_dict

def getSubsetRasterDict_rio(raster_dict, poly_arr, poly_affine):

    # The current Canvas Dict
    subset_dict = raster_dict.copy()
    subset_dict.update({'GeoTransform': poly_affine})
    subset_dict.update({'sizeX': poly_arr.shape[2], 'sizeY': poly_arr.shape[1]})

    # This is all old and I don't think needed but will keep around for a bit
    # canvas_bounds.asWktCoordinates()
    # bbc = [canvas_bounds.xMinimum(), canvas_bounds.yMinimum(), canvas_bounds.xMaximum(), canvas_bounds.yMaximum()]
    # offsets = boundingBoxToOffsets(bbc, raster_dict['GeoTransform'])
    # x_off, y_off = offsets[2], offsets[0]
    # new_geot = geotFromOffsets(offsets[0], offsets[2], raster_dict['GeoTransform'])
    # sizeX = int(((bbc[2] - bbc[0]) / raster_dict['resolution']) + 1)
    # sizeY = int(((bbc[3] - bbc[1]) / raster_dict['resolution']) + 1)
    #
    # subset_dict['GeoTransform'] = new_geot
    # subset_dict['sizeX'] = sizeX
    # subset_dict['sizeY'] = sizeY
    # subset_dict['Xoffset'] = x_off
    # subset_dict['Yoffset'] = y_off
    return subset_dict
