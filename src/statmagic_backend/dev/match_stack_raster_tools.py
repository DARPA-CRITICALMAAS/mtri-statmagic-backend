import rasterio as rio
import numpy as np
from rasterio.warp import reproject
from pathlib import Path
from sklearn.preprocessing import StandardScaler

def match_raster_to_template(template_path, input_raster_path, resampling_method, num_threads=1):
    """
    Clip and reproject an input raster to another rasters extent, crs,
    and affine transform. There could still be some room to add in some subtle
    shifts to better match pixel edges.

    Parameters
    ----------
    template_path : str
        Path to the template raster
    input_raster_path : str
        Path to the input raster
    resampling_method : str
        Resampling method. Must conform to :meth:`rio.warp.Resampling`,
        i.e. be one of

        .. code::

            [
                'nearest', 'bilinear', 'cubic', 'cubic_spline',
                'lanczos', 'average', 'mode', 'gauss'
            ]
    num_threads : int
        Number of threads to utilize for the resampling

    Returns
    -------
    reproj_arr : ndarray
        Array representing the dimensions of the template raster

    """

    # Establish properties from the template/base raster
    base_raster = rio.open(template_path)
    base_crs = base_raster.crs
    base_nodata = base_raster.nodata
    base_shape = base_raster.shape
    base_transform = base_raster.transform
    template_array = base_raster.read()

    in_raster = rio.open(input_raster_path)
    in_array = in_raster.read()

    # Create an array in the shape of the template to reproject into and execute reprojections
    new_ds = np.empty(shape=(in_raster.count, base_shape[0], base_shape[1]))

    reproj_arr = reproject(in_array, new_ds,
                           src_transform=in_raster.transform, dst_transform=base_transform,
                           src_crs=in_raster.crs, dst_crs=base_crs,
                           src_nodata=in_raster.nodata, dst_nodata=base_nodata,
                           resampling=resampling_method, num_threads=num_threads)[0]
    out_arr = np.where(template_array == base_nodata, base_nodata, reproj_arr)
    
    return out_arr


def match_and_stack_rasters(template_path, input_raster_paths_list, resampling_method_list, num_threads=1):
    """
    Serves as the backend of the add raster layers to the data stack tool.
    Lists should be created coming from the QDialog and QListView.

    Parameters
    ----------
    template_path : str
        Path to the template raster
    input_raster_paths_list : list
        List of file paths (str) to input rasters
    resampling_method_list : list
        Resampling method to apply
    num_threads : int
        Number of threads to utilize for the resampling

    Returns
    -------
    array_stack : ndarray
        Array with dimensions (number of input files, height and width of template)

    Warnings
    --------
    Defaults to ``float32`` datatype.

    """
    reprojected_arrays = []
    # reprojected_metas = []
    for raster_path, rs_method in zip(input_raster_paths_list, resampling_method_list):
        # reprojected_array, reprojected_meta = _unify_raster_grids(template_path, raster_path, rs_method, True, True, num_threads=num_threads)
        reprojected_array = match_raster_to_template(template_path, raster_path, rs_method, num_threads=num_threads)
        reprojected_arrays.append(reprojected_array)
        # reprojected_metas.append(reprojected_meta)

    print(len(reprojected_arrays))
    array_stack = np.vstack(reprojected_arrays).astype('float32')

    return array_stack
    # return reprojected_arrays


def add_matched_arrays_to_data_raster(data_raster_filepath, matched_arrays, description_list):
    """
    Adds ``matched_arrays`` to the data raster along with their descriptions.

    Parameters
    ----------
    data_raster_filepath : str
        Path to the data raster
    matched_arrays : ndarray
        Array containing subarrays for each match
    description_list : list
        List of descriptions

    Notes
    -----
    No return value. Writes directly to the raster file.

    """
    data_raster = rio.open(data_raster_filepath)
    current_band_count = data_raster.count
    profile = data_raster.profile
    number_new_bands = matched_arrays.shape[0]
    data_raster.close()
    # Check that if there is only one layer in the raster (eg. just got built) then to remove it
    # TODO: Find a better way to do this. A user might just add one band first, and then another
    # Maybe if np.unique(is just 1 or nodata) then do it
    if current_band_count == 1:
        # Then the raster has not been populated yet and the only layer is the np zeroes
        print('updating raster layers for the first time')
        profile.update(count=number_new_bands)
        data_raster = rio.open(data_raster_filepath, 'w', **profile)
        data_raster.write(matched_arrays)
        for band, description in enumerate(description_list, 1):
            data_raster.set_band_description(band, description)
        data_raster.close()
    else:
        # Raster already has layers added and just needs more added to it
        print('adding raster layers to current data raster')
        profile.update(count=(current_band_count + number_new_bands))
        # Get the existing numpy array and add the new layers along the axis
        existing_array = rio.open(data_raster_filepath).read()
        # get the existing band descriptions as a list
        current_descriptions = list(rio.open(data_raster_filepath).descriptions)
        full_descriptions = current_descriptions + description_list
        full_array = np.vstack([existing_array, matched_arrays])
        data_raster = rio.open(data_raster_filepath, 'w', **profile)
        data_raster.write(full_array)
        for band, description in enumerate(full_descriptions, 1):
            data_raster.set_band_description(band, description)
        data_raster.close()


def drop_selected_layers_from_raster(data_raster_filepath, list_of_bands):
    """
    Removes selected bands from the data raster.

    Parameters
    ----------
    data_raster_filepath : str
        Path to the data raster
    list_of_bands : list
        Bands to remove

    Notes
    -----
    No return value. Overwrites the raster file.

    """
    data_raster = rio.open(data_raster_filepath)
    num_bands_current = data_raster.count
    number_bands_new = len(list_of_bands)
    full_idx = [x+1 for x in range(num_bands_current)]
    idxs = [int(item.split("Band ")[1].split(":")[0]) for item in list_of_bands]
    drop_idxs = [x-1 for x in full_idx if x not in idxs]
    updated_descs = [item.split(": ")[1] for item in list_of_bands]
    profile = data_raster.profile
    profile.update(count=number_bands_new)
    existing_array = data_raster.read()
    data_raster.close()
    del data_raster
    updated_array = np.delete(existing_array, drop_idxs, 0)
    data_raster = rio.open(data_raster_filepath, 'w', **profile)
    data_raster.write(updated_array)
    for band, description in enumerate(updated_descs, 1):
        data_raster.set_band_description(band, description)
    data_raster.close()


def add_selected_bands_from_source_raster_to_data_raster(data_raster_filepath, input_raster_filepath, list_of_bands,
                                                         resampling_method, num_threads=1):

    # # Establish properties from the template/base raster
    data_raster = rio.open(data_raster_filepath)
    data_crs = data_raster.crs
    data_nodata = data_raster.nodata
    data_shape = data_raster.shape
    data_transform = data_raster.transform
    base_array = data_raster.read()[0:1, :, :]

    existing_band_descs = list(data_raster.descriptions)
    print(len(existing_band_descs))
    print(f'first element is : {existing_band_descs[0]}')
    print(f'exiting band descs {existing_band_descs}')
    if existing_band_descs[0] is None:
        print('no bands ')
        existing_band_descs = []

    print(existing_band_descs)

    # Here figure out which bands will be kept from the source raster
    input_raster = rio.open(input_raster_filepath)
    num_bands_current = input_raster.count
    number_bands_new = len(list_of_bands)
    full_idx = [x + 1 for x in range(num_bands_current)]
    idxs = [int(item.split("Band ")[1].split(":")[0]) for item in list_of_bands]
    drop_idxs = [x - 1 for x in full_idx if x not in idxs]
    new_descs = [item.split(": ")[1] for item in list_of_bands]
    print(f'new descs: {new_descs}')
    # Read the input array and drop the unneeded bands
    in_array = input_raster.read()
    updated_rast = np.delete(in_array, drop_idxs, 0)
    input_raster.close()

    # Create an array in the shape of the template to reproject into and execute reprojections
    new_ds = np.empty(shape=(updated_rast.shape[0], data_shape[0], data_shape[1]))

    reproj_arr = reproject(updated_rast, new_ds,
                           src_transform=input_raster.transform, dst_transform=data_transform,
                           src_crs=input_raster.crs, dst_crs=data_crs,
                           src_nodata=input_raster.nodata, dst_nodata=data_nodata,
                           resampling=resampling_method, num_threads=num_threads)[0]
    out_arr = np.where(base_array == data_nodata, data_nodata, reproj_arr)

    profile = data_raster.profile
    # Does updating the profile here work the way it should?
    if len(existing_band_descs) > 0:
        print('already has bands')
        profile.update(count=data_raster.count + number_bands_new)
        existing_array = data_raster.read()
        data_raster_array_updated = np.vstack([existing_array, out_arr])
        existing_band_descs.extend(new_descs)
        updated_descs = existing_band_descs.copy()
    else:
        print('first addition of bands')
        data_raster_array_updated = out_arr
        profile.update(count=number_bands_new)
        updated_descs = new_descs

    data_raster.close()
    del data_raster

    print(f'updated descs: {updated_descs}')
    data_raster = rio.open(data_raster_filepath, 'w', **profile)
    data_raster.write(data_raster_array_updated)
    for band, description in enumerate(updated_descs, 1):
        data_raster.set_band_description(band, description)
    data_raster.close()


def split_cube(fp, standardize=False):
    fp = Path(fp)
    newdir = fp.parent / 'single_band_tiffs'
    if newdir.exists():
        singlebandtiffs = [str(x) for x in list(newdir.glob("*.tif"))]
        return singlebandtiffs

    newdir.mkdir()
    raster = rio.open(fp)
    file_list = []
    for idx in range(raster.count):
        meta = raster.profile.copy()
        meta.update(count=1)
        band_name = raster.descriptions[idx]
        filename = band_name.replace(" ", "_")
        path_out = (newdir / filename).with_suffix('.tif')
        arr = raster.read(idx + 1)
        if standardize:
            nodata = raster.nodata
            arr = np.where(arr == nodata, np.nan, arr)
            arr = StandardScaler().fit_transform(arr)
            arr = np.nan_to_num(arr, nan=nodata)
        arr1 = np.expand_dims(arr, axis=0)
        data_raster = rio.open(path_out, 'w', **meta)
        data_raster.write(arr1)
        data_raster.set_band_description(1, band_name)
        data_raster.close()
        file_list.append(str(path_out))

    return file_list
