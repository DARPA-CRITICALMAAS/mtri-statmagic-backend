import math
from numbers import Number
import numpy as np
import rasterio as rio
from rasterio.transform import from_origin
from rasterio.features import rasterize
import geopandas as gpd
from typing import Optional

def get_array_shape_from_bounds_and_res(bounds: np.ndarray, pixel_size: Number):

    # upack the bounding box
    coord_west, coord_south, coord_east, coord_north = bounds[0], bounds[1], bounds[2], bounds[3]

    # Need to get the array shape from resolution
    raster_width = math.ceil(abs(coord_west - coord_east) / pixel_size)
    raster_height = math.ceil(abs(coord_north - coord_south) / pixel_size)

    return raster_width, raster_height, coord_west, coord_north


def create_template_raster_from_bounds_and_resolution(bounds, target_crs, pixel_size, output_path, clipping_gdf):

    raster_width, raster_height, coord_west, coord_north = get_array_shape_from_bounds_and_res(bounds, pixel_size)
    out_array = np.full((1, raster_height, raster_width), 0, dtype=np.float32)
    out_transform = from_origin(coord_west, coord_north, pixel_size, pixel_size)
    # TODO: Figure out how to make the clipping gdf and if it is a geodataframe, then if indent the next three lines
    # This should really only get done if the polygon != bounds
    shapes = ((geom) for geom in clipping_gdf.geometry)
    # This fill parameter doesn't seem to be working as I expect
    masking_array = rasterize(shapes=shapes, fill=np.finfo('float32').min, out=out_array, transform=out_transform, default_value=1)
    out_array = np.where(masking_array == 1, 1, 0).astype(np.float32)

    out_meta = {
        "width": raster_width,
        "height": raster_height,
        "count": 1,
        "dtype": out_array.dtype,
        "crs": target_crs,
        "transform": out_transform,
        "nodata": np.finfo('float32').min,
    }

    new_dataset = rio.open(output_path, 'w', driver='GTiff', **out_meta)
    new_dataset.write(out_array)
    new_dataset.close()

# def create_template_raster_from_bounds_and_resolution(
#         bounds: np.ndarray,
#         target_crs: rio.crs.CRS,
#         pixel_size: int,
#         output_path: str,
#         clipping_gdf: gpd.GeoDataFrame):
#
#     raster_width, raster_height, coord_west, coord_north = get_array_shape_from_bounds_and_res(bounds, pixel_size)
#     out_array = np.full((1, raster_height, raster_width), 1, dtype=np.float32)
#     out_transform = from_origin(coord_west, coord_north, pixel_size, pixel_size)
#     # TODO: Figure out how to make the clipping gdf and if it is a geodataframe, then if indent the next three lines
#     masking_shape = clipping_gdf.geometry[0]
#     masking_array = rio.features.rasterize((masking_shape, 1), fill=0, out=out_array.copy(), transform=out_transform)
#     out_array = np.where(masking_array == 1, 1, 0)
#
#     out_meta = {
#         "width": raster_width,
#         "height": raster_height,
#         "count": 1,
#         "dtype": out_array.dtype,
#         "crs": target_crs,
#         "transform": out_transform,
#         "nodata": np.finfo('float32').min,
#     }
#
#     new_dataset = rio.open(output_path, 'w', driver='GTiff', **out_meta)
#     new_dataset.write(out_array)
#     new_dataset.close()

def print_memory_allocation_from_resolution_bounds(bounds, pixel_size, bit=4):
    ht, wid = get_array_shape_from_bounds_and_res(bounds, pixel_size)[0:2]
    bytesize = ht * wid * bit
    statement = f"Each layer will be approximately {round(bytesize * 0.000001, 2)} MB"
    print(statement)
    print(f'height: {ht}, wid: {wid}')
    return statement
