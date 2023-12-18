import numpy as np


from statmagic_backend.geo.transform import geotFromOffsets, boundingBoxToOffsets


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


def calc_array_mode(pred_list):
    clstack = np.stack(pred_list)

    # https://stackoverflow.com/questions/12297016/how-to-find-most-frequent-values-in-numpy-ndarray
    u, indices = np.unique(clstack, return_inverse=True)
    mode = u[np.argmax(np.apply_along_axis(np.bincount, 0, indices.reshape(clstack.shape),
                                           None, np.max(indices) + 1), axis=0)]
    return mode

def nums3(msdL, sdval):
    lowhigh = []
    for i in msdL:
        low = i[0] - (sdval * i[1])
        high = i[0] + (sdval * i[1])
        lowhigh.append([low, high])
    return lowhigh

def MinMaxPop(array):
    return array[np.where(np.logical_and(array != np.min(array), array != np.max(array)))]

def RasMatcha(vlistitem, RasterDataSet):
    band, mean, pm = [vlistitem[0], vlistitem[1], vlistitem[3]]
    rbds = RasterDataSet.GetRasterBand(band).ReadAsArray()
    low = mean - pm
    high = mean + pm
    bandmatch = np.logical_and(rbds < high, rbds > low)
    return bandmatch

def RasBoreMatch(vlistitem, RasterDataSet):
    band, min, max = [vlistitem[0], vlistitem[1], vlistitem[2]]
    rbds = RasterDataSet.GetRasterBand(band).ReadAsArray()
    bandmatch = np.logical_and(rbds < max, rbds > min)
    return bandmatch

def sdMatchStack(datastack, meanstdlist, sdval):
    matchbandlist = []
    for band, meadSD in zip(np.rollaxis(datastack, 0), meanstdlist):
        mn = meadSD[0]
        std = meadSD[1] * sdval
        hi = mn + std
        low = mn - std
        bandmatch = np.logical_and(band < hi, band > low)
        matchbandlist.append(bandmatch)

    boolstack = np.vstack([matchbandlist])
    allmatch = np.all(boolstack, axis=0).astype(np.uint8)
    return allmatch

def sdMatchSomeInStack(datastack, meanstdlist, sdval, minNumMatch):
    matchbandlist = []
    if minNumMatch > 0:
        for band, meadSD in zip(np.rollaxis(datastack, 0), meanstdlist):
            mn = meadSD[0]
            std = meadSD[1] * sdval
            hi = mn + std
            low = mn - std
            bandmatch = np.logical_and(band < hi, band > low)
            matchbandlist.append(bandmatch.astype(np.uint8))

        boolstack = np.vstack([matchbandlist])
        nummatch = sum(boolstack)
        madeits = np.where(nummatch >= minNumMatch, 1, 0)
        return madeits
    else:
        for band, meadSD in zip(np.rollaxis(datastack, 0), meanstdlist):
            mn = meadSD[0]
            std = meadSD[1] * sdval
            hi = mn + std
            low = mn - std
            bandmatch = np.logical_and(band < hi, band > low)
            matchbandlist.append(bandmatch)

        boolstack = np.vstack([matchbandlist])
        allmatch = np.all(boolstack, axis=0).astype(np.uint8)
        return allmatch


def placeLabels_inRaster(labels1D, bool_arr, ras_dict, dtype, return_labels=False):
    labels = np.zeros_like(bool_arr).astype(dtype)
    labels[~bool_arr] = labels1D
    labels[bool_arr] = 0

    preds = labels.reshape(ras_dict['sizeY'], ras_dict['sizeX'], 1)
    classout = np.transpose(preds, (0, 1, 2))[:, :, 0]
    if return_labels:
        return classout, labels
    else:
        return classout
