
import pandas as pd
import numpy as np
import rasterio as rio
import rasterio.features
from scipy.ndimage import distance_transform_edt as sdist
from shapely.geometry import box, Point
import tempfile
import geopandas as gpd
from rasterio.transform import from_origin
from statmagic_backend.dev.template_raster_user_input import get_array_shape_from_bounds_and_res
import logging
logger = logging.getLogger("statmagic_backend")


# gdf = dill('/home/jagraham/Documents/Local_work/statMagic/devtest/gdf')
#
# prox_gdf = gpd.read_file("/home/jgranham/Documents/CMA_Dutchinium/faults.gpkg")
# template_file_path = '/home/jgranham/Documents/CMA_Dutchinium/Dutchinium_template_raster.tif'
# output_dir = '/home/jgranham/Documents/CMA_Dutchinium/'
# output_file_path = '/home/jgranham/Documents/CMA_Dutchinium/rasterlines1.tif'



def qgs_features_to_gdf(qgs_vector_layer, selected=False):

    if selected is True:
        sel = qgs_vector_layer.selectedFeatures()
    else:
        sel = qgs_vector_layer.getFeatures()

    columns = [f.name() for f in qgs_vector_layer.fields()] + ['geometry']

    row_list = []
    for f in sel:
        row_list.append(dict(zip(columns, f.attributes() + [f.geometry().asWkt()])))

    df = pd.DataFrame(row_list, columns=columns)
    df['geometry'] = gpd.GeoSeries.from_wkt(df['geometry'])
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    gdf = gdf.set_crs(crs=qgs_vector_layer.crs().toWkt())
    return gdf


def get_prox_features(prox_gdf, template_file_path):
    # First see if all of the chosen features are within the CMA project extent
    rast = rio.open(template_file_path)
    bounds = rast.bounds

    within_set = prox_gdf.within(box(*bounds))
    if within_set.all() == True:
        # If they are all within then can proceed using the extent of CMA project
        print('Within')
        return prox_gdf, "Within"
    else:
        print("Beyond")
    # If there are some beyond, then do the buffer and select
        width = bounds.right - bounds.left
        height = bounds.top - bounds.bottom
        diagonal_distance = (width ** 2 + height ** 2) ** 0.5
        buffer_poly = box(*bounds).buffer(diagonal_distance)

        # make the prox_gdf in the same crs as the raster
        prox_gdf.to_crs(rast.crs, inplace=True)

        # First take all features that intersect with this buffer polygon
        intesecting_features = prox_gdf[prox_gdf.geometry.intersects(buffer_poly)]

        # Check if there are features
        if len(intesecting_features) > 0:
            # There are features to continue with
            use_prox_features_gdf = intesecting_features.copy()
        else:
            # There are no features to continue with. Get the nearest featuers from each corner of the template
            minx, miny, maxx, maxy = bounds.left, bounds.bottom, bounds.right, bounds.top
            corner_points = [Point(minx, miny), Point(minx, maxy), Point(maxx, maxy), Point(maxx, miny)]
            points_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(corner_points), crs=rast.crs)
            points_gdf.to_crs(rast.crs, inplace=True)
            use_prox_features_gdf = get_nearest_features(points_gdf, prox_gdf, num_nearest=5)
            if len(use_prox_features_gdf) == 0:
                print('No features to continue with')
                print('need to exit function here and raise message')
                pass

        #
        #
        # # points = [Point(x, y) for x, y in buffer_poly.exterior.coords]
        # # points_gdf = gpd.GeoDataFrame(geometry=points, crs=rast.crs)
        # #
        # box_gdf = gpd.GeoDataFrame(geometry=[box(*bounds)], crs=rast.crs)
        # box_geom = box_gdf.geometry[0]
        #
        # prox_gdf.to_crs(box_gdf.crs, inplace=True)
        #
        # # Only want to select the features that aren't within the template bounds
        # outside_features_gdf = prox_gdf[~prox_gdf.intersects(box_geom)]
        #
        # # get the n number of nearest features to each point of the bounding box
        # nearest_features = get_nearest_features(points_gdf, outside_features_gdf, num_nearest=10)
        return use_prox_features_gdf, "Beyond"


def get_nearest_features(points_gdf, prox_gdf, num_nearest=10):
    prox_gdf.to_crs(points_gdf.crs, inplace=True)

    nearest_features_gdf_list = []
    for point in points_gdf.geometry:
        prox_gdf['distance'] = prox_gdf.geometry.distance(point)
        nearest_features = prox_gdf.loc[prox_gdf['distance'].nsmallest(num_nearest).index]
        nearest_features_gdf_list.append(nearest_features)
    nearest_features_gdf = pd.concat(nearest_features_gdf_list)

    return nearest_features_gdf


def vector_proximity_raster_upgraded(prox_gdf, template_file_path):
    # Make a temp file for the output raster
    # Consider making this into a folder in the project directory rather than a temp file?
    tfol = tempfile.mkdtemp()
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix='proximity_raster')
    output_file_path = tfile[1]
    # first get the actual set of proxinmity features to consider in the analysis
    prox_features_gdf, status = get_prox_features(prox_gdf, template_file_path)
    raster = rio.open(template_file_path)
    if status == 'Within':
        res = raster.res[0] + 1
        prox_features_gdf.to_crs(raster.crs, inplace=True)

        meta = raster.meta.copy()
        meta.update({'dtype': 'float32', 'nodata': np.finfo('float32').min, 'count': 1})

        with rio.open(output_file_path, 'w+', **meta) as out:
            out_arr = np.zeros_like(out.read(1))
            shapes = ((geom.buffer(res)) for geom in (prox_features_gdf.geometry))
            burned = rio.features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
            dists = sdist(np.logical_not(burned))
            out.write_band(1, dists)
        message = f'raster saved to {output_file_path}'
        return output_file_path, message

    elif status == 'Beyond':
        # This needs to compare the bounds of the GDF and the bounds of the Proj Extent and take the
        # Max in all directions
        prox_bounds = box(*prox_features_gdf.total_bounds)
        proj_bounds = box(*raster.bounds)
        proj_gdf = gpd.GeoDataFrame(geometry=[prox_bounds, proj_bounds], crs=raster.crs)
        bounds = proj_gdf.total_bounds
        # Get the pixel size from the template raster
        pixel_size = rio.open(template_file_path).res[0]
        target_crs = rio.open(template_file_path).crs
        raster_width, raster_height, coord_west, coord_north = get_array_shape_from_bounds_and_res(bounds, pixel_size)
        # out_array = np.full((1, raster_height, raster_width), 0, dtype=np.float32)
        out_transform = from_origin(coord_west, coord_north, pixel_size, pixel_size)

        out_meta = {
            "width": raster_width,
            "height": raster_height,
            "count": 1,
            "dtype": 'float32',
            "crs": target_crs,
            "transform": out_transform,
            "nodata": np.finfo('float32').min,
        }

        with rio.open(output_file_path, 'w+', **out_meta) as out:
            out_arr = np.zeros_like(out.read(1))
            shapes = ((geom.buffer(pixel_size)) for geom in (prox_features_gdf.geometry))
            burned = rio.features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
            dists = sdist(np.logical_not(burned)) * pixel_size
            out.write_band(1, dists)
        message = f'raster saved to {output_file_path}'
        return output_file_path, message
    else:
        print("Something Didn't Work")


def vector_proximity_raster(gdf, template_file_path):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix='proximity_raster')

    output_file_path = tfile[1]


    raster = rio.open(template_file_path)
    res = raster.res[0] + 1
    gdf.to_crs(raster.crs, inplace=True)

    # Clip the gdf by the bounds of the project.
    # Note - This may be upgraded in the future to account for distance from geometries outside the project but may
    # influence the calculations
    gdf = gdf.clip(raster.bounds)


    meta = raster.meta.copy()
    meta.update({'dtype': 'float32', 'nodata': np.finfo('float32').min, 'count': 1})

    with rio.open(output_file_path, 'w+', **meta) as out:
        out_arr = np.zeros_like(out.read(1))
        shapes = ((geom.buffer(res)) for geom in (gdf.geometry))
        burned = rio.features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
        dists = sdist(np.logical_not(burned))
        out.write_band(1, dists)
    message = f'raster saved to {output_file_path}'
    return output_file_path, message


def rasterize_vector(gdf, template_file_path, field=None):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix='rasterized_')

    output_file_path = tfile[1]

    raster = rio.open(template_file_path)
    gdf.to_crs(raster.crs, inplace=True)

    # Clip the gdf by the bounds of the project.
    # Note - This may be upgraded in the future to account for distance from geometries outside the project but may
    # influence the calculations
    gdf = gdf.clip(raster.bounds)
    gdf[field] = pd.to_numeric(gdf[field], errors='coerce')
    gdf.dropna(subset=[field], inplace=True)

    meta = raster.meta.copy()
    meta.update({'dtype': 'float32', 'nodata': np.finfo('float32').min, 'count': 1})

    with rio.open(output_file_path, 'w+', **meta) as out:
        out_arr = out.read(1)

        if field:
            shapes = ((geom, value) for geom, value in zip(gdf.geometry, gdf[field]))
        else:
            shapes = (geom for geom in (gdf.geometry))

        burned = rio.features.rasterize(shapes=shapes, fill=np.finfo('float32').min, out=out_arr, transform=out.transform)
        out.write_band(1, burned)
    message = f'raster saved to {output_file_path}'
    return output_file_path, message


