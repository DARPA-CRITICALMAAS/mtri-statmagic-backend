import rasterio as rio
import numpy as np
from rasterio.warp import reproject
from pathlib import Path
from sklearn.preprocessing import StandardScaler
import rioxarray
import concurrent.futures


def match_raster_to_template(template_path, input_raster_path, resampling_method, band, num_threads=1):
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
    print(f'read {input_raster_path}')
    print(f"count: {in_raster.count}")

    if band == "all":
        print('reading full')
        in_array = in_raster.read()
    else:
        print(f'reading band {band}')
        in_array = np.expand_dims(in_raster.read(band+1), 0)
    print(f'shape: {in_array.shape}')

    # Create an array in the shape of the template to reproject into and execute reprojections
    new_ds = np.empty(shape=(in_array.shape[0], base_shape[0], base_shape[1]))

    reproj_arr = reproject(in_array, new_ds,
                           src_transform=in_raster.transform, dst_transform=base_transform,
                           src_crs=in_raster.crs, dst_crs=base_crs,
                           src_nodata=in_raster.nodata, dst_nodata=base_nodata,
                           resampling=resampling_method, num_threads=num_threads)[0]
    out_arr = np.where(template_array == base_nodata, base_nodata, reproj_arr)

    return out_arr


def match_and_stack_rasters(template_path, input_raster_paths_list, resampling_method_list, band_id_list, num_threads=1):
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
    # reprojected_arrays = []
    # for raster_path, rs_method in zip(input_raster_paths_list, resampling_method_list):
    #     reprojected_array = match_raster_to_template(template_path, raster_path, rs_method, num_threads=num_threads)
    #     reprojected_arrays.append(reprojected_array)
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        reprojected_arrays = list(executor.map(lambda args: match_raster_to_template(*args),
                                               zip([template_path] * len(input_raster_paths_list),
                                                   input_raster_paths_list,
                                                   resampling_method_list,
                                                   band_id_list,
                                                   [num_threads] * len(input_raster_paths_list))))
    # array_stack = np.vstack(reprojected_arrays).astype('float32')

    # return array_stack
    return reprojected_arrays


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

    # Check that if there is only one layer in the raster (eg. just got built) then to remove it
    nodata = data_raster.nodata
    tarr = data_raster.read(1)
    arr = np.where(tarr == nodata, np.nan, tarr)
    arr = arr[~np.isnan(arr)]
    isAltered = np.all(arr == 1)

    data_raster.close()

    # Todo: Find a better way to do this. A user might just add one band first, and then another
    # if current_band_count == 1:
    if isAltered:
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


def drop_selected_layers_from_raster(data_raster_filepath, drop_idxs):
    """
    Removes selected bands from the data raster.

    Parameters
    ----------
    data_raster_filepath : str
        Path to the data raster
    drop_idxs : list
        Bands to remove

    Notes
    -----
    No return value. Overwrites the raster file.

    """
    data_raster = rio.open(data_raster_filepath)
    num_bands_current = data_raster.count  # The number of bands in the current raster
    number_bands_new = num_bands_current - len(
        drop_idxs)  # The number of bands that will be kept (list of bands is actually list of keepers)
    current_descriptions = list(data_raster.descriptions)  # The current band descriptions
    full_idx = [x for x in range(num_bands_current)]
    keep_idxs = [x for x in full_idx if x not in drop_idxs]
    updated_descs = [current_descriptions[i] for i in keep_idxs]
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


def match_cogList_to_template_andStack(template_path: str, cog_paths: list, method_list: list) -> np.ndarray:
    """
    Function to match a list of COG arrays to a template using rasterio, rioxarray, and numpy operations.

    Parameters:
    - template_path: str, path to the template COG file
    - cog_paths: list, list of paths to the COG files to match
    - rs_list: list, list of resampling methods for reprojection

    Returns:
    - out_arr: np.ndarray, matched and stacked array with nodata masking applied
    """
    template_ds = rioxarray.open_rasterio(template_path)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        matched_arrays = list(executor.map(_process_cog, cog_paths, method_list, [template_ds] * len(cog_paths)))

    # array_stack = np.vstack(matched_arrays).astype('float32')
    # # Apply nodata masking
    # template_array = template_ds.to_numpy()
    # out_arr = np.where(template_array == template_ds._FillValue, template_ds._FillValue, array_stack)
    #
    # return out_arr
    return matched_arrays


def _process_cog(ras_url, method, template_ds):
    ds = rioxarray.open_rasterio(ras_url)
    ds_matched = ds.rio.reproject_match(template_ds, resampling=method).to_numpy()
    return ds_matched


def parse_raster_processing_table_elements(raster_paths, source_list, method_list):
    local_paths = []
    local_methods = []
    local_bands = []
    local_descs = []
    cog_paths = []
    cog_methods = []
    cog_descs = []
    original_order = []
    local_order = []
    cog_order = []
    for idx, (path, source) in enumerate(zip(raster_paths, source_list)):
        # Maybe the best way to do this is and take advantage of the parallel processing is to use this to construct
        # 1) a list of cog_paths and methods to pass to match_cogList_to_template_andStack
        # 2) a list of local paths  to pass to match and stack rasters
        # Would end up with 2 3d ndarrays that would need to get shuffled and stacked accordingly
        print('---------------')
        print(idx)
        print(path)
        print(source)
        # print(description_list[idx])
        if source == 'Qgs':
            print('process local')
            local_paths.append(path)
            local_methods.append(method_list[idx])
            local_bands.append('all')
            local_order.append(idx)
            # local_descs.append(description_list[idx])
        elif source == 'CloudFront':
            print('cog rioxarray')
            cog_paths.append(path)
            cog_methods.append(method_list[idx])
            cog_order.append(idx)
            # cog_descs.append(description_list[idx])
        else:
            print('parse file path and process local')
            band_str = path.split('_')[-1]
            band_idx = int(band_str)
            p = path[0:-(len(band_str)+1)]
            # p = "".join(path.split("_")[0:-1])
            local_paths.append(p)
            local_methods.append(method_list[idx])
            local_bands.append(band_idx)
            local_order.append(idx)
            # local_descs.append(description_list[idx])
        original_order.append(idx)
    local_dict = {'paths': local_paths, 'methods': local_methods, 'band': local_bands, 'descs': local_descs}
    cog_dict = {'paths': cog_paths, 'methods': cog_methods, 'descs': cog_descs}
    order_dict = {'local': local_order, 'cog': cog_order, 'full': original_order}
    return local_dict, cog_dict, order_dict


def reorder_array_lists_to_stack(local_array_list, cog_array_list, order):
    full_array_list = []
    for x in order['full']:
        print("----------------------------------------")
        print(x)
        if x in order['local']:
            print(f"local: {order['local']}")
            idx = order['local'].index(x)
            print(idx)
            full_array_list.append(local_array_list[idx])
        elif x in order['cog']:
            print(f"cog: {order['cog']}")
            idx = order['cog'].index(x)
            print(idx)
            full_array_list.append(cog_array_list[idx])
        else:
            print('somethign wrong')
    array_stack = np.vstack(full_array_list).astype('float32')
    return array_stack


def apply_template_mask_to_array(template_path, array_stack):
    base_raster = rio.open(template_path)
    base_nodata = base_raster.nodata
    template_array = base_raster.read()
    out_arr = np.where(template_array == base_nodata, base_nodata, array_stack)
    return out_arr


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
