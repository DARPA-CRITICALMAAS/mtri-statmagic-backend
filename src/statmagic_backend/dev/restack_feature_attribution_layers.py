import rasterio as rio
import numpy as np
from pathlib import Path


def restack_matched_layers(list_of_paths_to_matching_single_band_tifs, output_path):
    '''
    Designed to ingest SRI feature attribution outputs. These are already expected to have the same
    CRS, Affine transform, cell size, rows, and columns. Makes the name of the file without the extension become
    the band description. This will get used for plotting labels.
    Parameters
    ----------
    list_of_paths_to_matching_single_band_tifs

    Returns: None
    -------
    '''
    # Grab the metadata from the first file. ASSUMES ALL FILES ARE THE SAME
    raster = rio.open(list_of_paths_to_matching_single_band_tifs[0])
    band_count = len(list_of_paths_to_matching_single_band_tifs)
    profile = raster.profile

    array_list = []
    description_list = []
    for fp in list_of_paths_to_matching_single_band_tifs:
        description_list.append(Path(fp).stem)
        array_list.append(rio.open(fp).read())
    array_stack = np.vstack(array_list).astype('float32')
    profile.update(count=band_count)
    data_raster = rio.open(output_path, 'w', **profile)
    data_raster.write(array_stack)
    for band, description in enumerate(description_list, 1):
        data_raster.set_band_description(band, description)
    data_raster.close()


def merge_likelihood_and_uncertainty(path_to_likelihood, path_to_uncertainty):
    pass