import copy
import json
import itertools
import os
import fiona
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import to_geojson
from pathlib import Path
import numpy as np
from pyproj import Transformer
import requests
from urllib.parse import urljoin

import mapbox_vector_tile
import mercantile # utility for converting between XYZ indices and lat/lon bounds

import logging
logger = logging.getLogger("statmagic_backend")


def boundingBoxToOffsets(bbox, geot):
    col1 = int((bbox[0] - geot[0]) / geot[1])
    col2 = int((bbox[1] - geot[0]) / geot[1]) + 1
    row1 = int((bbox[3] - geot[3]) / geot[5])
    row2 = int((bbox[2] - geot[3]) / geot[5]) + 1
    return [row1, row2, col1, col2]


def geotFromOffsets(row_offset, col_offset, geot):
    new_geot = [geot[0] + (col_offset * geot[1]),
                geot[1],
                0.0,
                geot[3] + (row_offset * geot[5]),
                0.0,
                geot[5]]
    return new_geot


def download_tiles(tile_indices, tileserver, service):
    r"""
    Download Mapbox tiles from a particular tile server. Defaults to Macrostrat
    using the ``carto`` service.

    Parameters
    ----------
    tile_indices : array-like
        Set of tile XYZ indices where, for each tile, the data is ordered
        ``[z,x,y]`` where ``z`` is zoom; ``x``, ``y`` are image indices.
    tileserver : str
        Tile server URL
    service : str
        Which tile service to use from the tile server

    Returns
    -------
    mapbox_tiles : list
        Raw (unprocessed) output from tileserver

    Notes
    -----
    In Macrostrat's tile server, the XYZ indices are specified in the URL
    in this order: ``/{z}/{x}/{y}``, where

        ``z`` = zoom level
        ``x`` = tile x index
        ``y`` = tile y index (starting at top)

    Georegistration for now is done by pinning corners to the tile bounds (which
    we can get from mercantile). Registration precision improves the further zoomed
    in you are:

    .. table::

        ==========  ==================
        Zoom level  Observed precision
        ==========  ==================
        4           15-km
        5           8-km
        6           4-km
        ==========  ==================

    *  lower zoom level are more zoomed out
    ** i.e. vertices can be off by this much at this zoom level
    """
    mapbox_tiles = []
    base_url = urljoin(tileserver, service) + "/"
    for tile_index in tile_indices:
        tile_str = [str(x) for x in tile_index]

        # Set URL of the tile to be downloaded
        url = urljoin(base_url, "/".join(tile_str))
        # TODO: use urllib instead of pathlib

        # Retrieve tile from URL
        mapbox_tile = requests.get(url).content
        mapbox_tiles.append(mapbox_tile)

    return mapbox_tiles


def decode_protobuf_to_geojson_wgs84(tile, layername, bounds, tilesize):
    """
    Decodes a Google protobuf binary object representing a vector tile return
    from a MapBox tile server into a vector represented as a geoJSON dict in
    EPSG 4326 (WGS 84) map projection.
    
    Parameters
    ----------
    tile : Google protobuf binary
        Object returned from Mapbox vector tile server
    layername : str
        Name of the layer to pull out of response
    bounds : Object returned by mercantile.bounds() function
        Has north, south, east, west attributes indicating lat/lon bounds
    tilesize : int
        Size of the tile returned by the tile server in pixels

    Returns
    -------
    data : dict
        Dict representing GeoJSON data
    """

    def process_coord_pair(coord_pair):
        """ Scales relative coordinates to known lat/lon bounds. """
        return [
            round(float(coord_pair[0]) / float(tilesize) * (
                        bounds.east - bounds.west) + bounds.west, 5),
            round(float(coord_pair[1]) / float(tilesize) * (
                        bounds.north - bounds.south) + bounds.south, 5)
        ]

    # Decode to dict and pull out the GeoJSON for the target layer
    data_decoded = mapbox_vector_tile.decode(tile)
    #logger.debug(list(data_decoded.keys()))
    if layername not in data_decoded:
        logger.debug(f'\t\tLayer name "{layername}" not present in this data. Skipping...')
        return None

    data = data_decoded[layername]

    # Unwrap the geometry and scale coordinates to the lat/lon bounds
    fnews = []
    for feature in data['features']:
        fnew = copy.deepcopy(feature)
        #logger.debug(fnew)
        coords = fnew['geometry']['coordinates']
        coords_new = []

        # Process coords for lines
        if fnew['geometry']['type'] == 'LineString':
            #line_new = []
            for coord_pair in coords:
                coords_new.append(process_coord_pair(coord_pair))


        # Process coords for polygons
        else:
            for poly in coords:
                poly_new = []
                for part in poly:
                    if type(part[0]) == list:
                        part_new = []
                        for coord_pair in part:
                            part_new.append(process_coord_pair(coord_pair))
                        poly_new.append(part_new)
                    else:
                        poly_new.append(process_coord_pair(part))
                coords_new.append(poly_new)

        fnew['geometry']['coordinates'] = coords_new
        fnews.append(fnew)

    data['features'] = fnews

    return data


def process_tiles(tiles, tile_indices, outdir, layername, tilesize):
    """
    Convert Mapbox tiles to a format that can be used by QGIS in standard
    processing operations. This implementation converts to GeoJSON vector
    format but other utilities can be used to convert it to raster instead.

    Parameters
    ----------
    tiles : list
        Mapbox tile objects
    tile_indices : array-like
        Set of tile XYZ indices where, for each tile, the data is ordered
        ``[z,x,y]`` where ``z`` is zoom; ``x``,``y`` are image indices.
    outdir : str or Path
        Directory in which to save outputs
    layername : str
        Name of the layer to pull out of response
    tilesize : int
        Size of the tile returned by the tile server in pixel

    Returns
    -------
    js_paths : list
        List of str's representing output geojson file paths
    """
    # TODO: could potentially be useful to return in-memory objects
    #       instead of / in addition to writing the output to files

    js_paths = []

    # Process each tile
    for tile_index, tile in zip(tile_indices, tiles):
        tile_str = [str(x) for x in tile_index]

        # # Set paths to output files
        basename = Path(outdir, "-".join(tile_str))
        js_path = basename.with_suffix(".json")

        # Get lat/lon bounds of a tile by [z,x,y] indices
        bounds = mercantile.bounds((tile_index[1], tile_index[2], tile_index[0]))

        # Convert to GeoJSON and georegister by scaling to tile bounds
        data = decode_protobuf_to_geojson_wgs84(tile, layername, bounds, tilesize)

        if not data:
            continue

        # Save the GeoJSON to file
        if not js_path.exists():
            js_path.parent.mkdir(parents=True, exist_ok=True)
        with open(js_path, 'w') as f:
            f.write(json.dumps(data))

        js_paths.append(js_path)

    return js_paths



def get_tile_xyz_by_ll(lat,lon,zoom_level=7):
    """
    Returns tile XYZ for the given latitude, longitude, and zoom level

    Parameters
    ----------
    lat : float
        Latitude
    lon : float
        Longitude
    zoom_level : int, optional
        Zoom level

    Returns
    -------
    mercantile.Tile

    Notes
    -----
    This seems to be agnostic of the particular tile server or layer, i.e. all
    mapbox vector tile servers must use the exact same indexing coordinates.
    """
    return mercantile.tile(lon,lat,zoom_level)


def get_tiles_for_ll_bounds(n,s,e,w,zoom_level=7):
    """
    Takes in latitude and longitude bounds and returns a list of tiles (defined
    by [z,x,y] indices) for the provided zoom_level within those bounds.

    n : float
        Latitude indicating northern bounds of BBOX used to clip features
    s : float
        Latitude indicating northern bounds of BBOX used to clip features
    e : float
        Longitude indicating eastern bounds of BBOX used to clip features
    w : float
        Longitude indicating western bounds of BBOX used to clip features

    zoom_level : int
        Vector tile server zoom level (higher = more zoomed in)

    Returns
    -------
    tile_indices : list
        List of 3 element lists that define tile indices as (z,x,y) that can be
        fed into *download_tiles*, e.g.:

        .. code::

            [
                [7,42,42],
                [7,42,43],
                [7,42,44],
            ]

    Notes
    -----
    :meth:`mercantile.tile` returns just a single tile by a point lat/lon, so in
    order to get ALL tiles within a bounding box, we have to iterate searches
    over a grid of lat/lon point within the bounds. Only the unique set of tiles
    is retained. Grid size is determined by ``zoom_level``:

    .. table::

        ==========  ===============  =========================
        Zoom level  Tile size        Grid resolution
        ==========  ===============  =========================
        5           11 - 18 degrees  10 degrees
        6           5 -  9 degrees   4 degrees
        7           2 -  3 degrees   1 degree (~100 km)
        8           ? -  ? degrees   0.25 degree (~25 km)
        9                            0.0625 degrees (~6.25 km)
        10                           0.016 degrees (~1.6 km)
        11                           0.004 degrees (~400 m)
        ==========  ===============  =========================

    """
    logger.debug("testing the log")

    # Default search grid resolution
    grid_res_degrees = 10

    # Dict mapping zoom level (int) to grid resolution (degrees)
    zoom_to_gridres = {
        6: 4,
        7: 1,
        8: 0.25,
        9: 0.0625,
        10: 0.016,
        11: 0.004
    }

    if zoom_level in zoom_to_gridres:
        grid_res_degrees = zoom_to_gridres[zoom_level]

    # Gather tiles within the bounds
    tiles = []
    for lon in np.arange(w,e+grid_res_degrees,grid_res_degrees):
        for lat in np.arange(s,n+grid_res_degrees,grid_res_degrees):
            tiles.append(get_tile_xyz_by_ll(lat,lon,zoom_level))

    # Return the set (unique tiles), formatted for input to process_tiles
    return [[x.z,x.x,x.y] for x in set(tiles)]



def dissolve_vector_files_by_property(
        vector_files,
        property_name,
        valid_geom_types,
        output_file,
        n=None,s=None,e=None,w=None
    ):
    """
    Takes in a list of geospatial vector files and outputs a single vector file
    (same format as inputs) containing all features of the input files, with
    boundaries between features of common property name dissolved.

    Optional n,s,e,w parameters indicate lat/lon BBOX bounds by which to clip
    features. If not included, features will not be clipped.

    Parameters
    ----------
    vector_files : list
        List of str's representing geojson file paths
    property_name : str
        Name of the feature property in the geoJSON to dissolve features by
    valid_geom_types : list of str's
        List of valid GeoJSON geometry types for the given layer
    output_file : str
        File path for the output file
    n : float, optional
        Latitude indicating northern bounds of BBOX used to clip features
    s : float, optional
        Latitude indicating northern bounds of BBOX used to clip features
    e : float, optional
        Longitude indicating eastern bounds of BBOX used to clip features
    w : float, optional
        Longitude indicating western bounds of BBOX used to clip features

    Notes
    -----
    Returns nothing (output is written to file)

    """

    if not vector_files:
        logger.debug('No vector data to dissolve, skipping...')
        return

    # If clip bounds are provided, create the bbox geometry to clip to
    bbox_geom = None
    if n and s and e and w:
        bbox_geom = Polygon((
            (w,n),
            (w,s),
            (e,s),
            (e,n),
            (w,n),
        ))

    # Collect geometry features from all the input files
    features = []
    for vector_file in vector_files:
        with fiona.open(vector_file) as invector:
            meta = invector.meta
            features += invector

    # Sort the features by the property
    e = sorted(features, key=lambda k: k['properties'][property_name])

    # Loop through and combine geometry features by group property
    features_new = [] # var to store the dissolved features
    for key, group in itertools.groupby(
            e, key=lambda x: x['properties'][property_name]
        ):

        properties, geom = zip(
            *[(feature['properties'], make_valid(shape(feature['geometry'])))
              for feature in group]
        )

        # This function handles combining the coordinates into a single feature
        g = mapping(unary_union(geom))

        # Perform the clip here
        if bbox_geom:
            g = json.loads(to_geojson(shape(g).intersection(bbox_geom)))
        #logger.debug(g)

        # Wrap non-collections to resemble a collection so we don't need
        # multiple processing procedures for collections and non-collections
        if g['type'] != 'GeometryCollection':
           g = {'geometries': [g]}


        for g0 in g['geometries']:

            # Skip empty features
            if len(g0['coordinates']) == 0 or len(g0['coordinates'][0]) == 0:
                continue

            # Skip lines and points
            if g0['type'] not in valid_geom_types:#('Polygon','MultiPolygon','LineString'):
                continue

            # Convert any Polygon feature types to MultiPolygon (output file will
            # be MultiPolygon type; see below)
            if g0['type'] == 'Polygon':
                g0['type'] = 'MultiPolygon'
                g0['coordinates'] = [g0['coordinates']]

            if g0['type'] == 'LineString':
                g0['type'] = 'MultiLineString'
                g0['coordinates'] = [g0['coordinates']]

            # Store newly created dissolved features
            features_new.append({
                'geometry': g0,
                'properties': properties[0]
            })

            # Store type for writing output
            gtype = g0['type']

    # Update the geometry type from Polygon to MultiPolygon so that it can
    # handle cases where adjacent tile coords don't line up precisely
    gtype = [x for x in valid_geom_types if 'Multi' in x][0]
    meta['schema']['geometry'] = gtype#'MultiPolygon'
    with fiona.open(output_file, 'w', **meta) as output:
        for feature in features_new:
            output.write(feature)


if __name__ == "__main__":
    # Processing directory to store output files
    processing_dir = Path.home() / "PROCESSING/macrostrat/"

    # Vector tile layers to download
    layers = [
        { # vv polygon map units
            'layername': 'units',
            'dissolve_by_property': 'map_id',
            'valid_geom_types': ['Polygon','MultiPolygon']
        },
        {# vv fault lines
            'layername': 'lines',
            'dissolve_by_property': 'line_id',
            'valid_geom_types': ['LineString','MultiLineString']
        },
    ]


    ########
    # Two options for setting tile_indices to process:

    # OPTION 1: manually define
    # Set of tiles by XYZ indices; order is: z(zoom), x(x index), y(y index)
    tile_indices = (
        [7,42,42],# z, x, y
        #[9,600,300],
    )

    bounds = {}
    # # OPTION 2: set lat/lon bounds; tile list will be retrieved
    # bounds = {
    #     'n': 43.0,
    #     's': 40.9,
    #     'e': -59,
    #     'w': -62,
    # }
    #
    bounds = {
        'n': 42.4046340196102,
        's': 40.35045988370135,
        'e': -93.39360118961542,
        'w': -97.14894692014128
    }

    tile_indices = get_tiles_for_ll_bounds(**bounds, zoom_level=10)

    ########
    # Process tile list

    mapbox_tiles = download_tiles(tile_indices, "https://dev.macrostrat.org/tiles/", "carto")

    for layer in layers:
        logger.debug(f'\n\tProcessing layer: {layer["layername"]}')

        js_paths = process_tiles(
            mapbox_tiles, tile_indices, processing_dir, layer['layername'], 4096
        )

        dissolve_vector_files_by_property(
            js_paths,
            layer['dissolve_by_property'],
            layer['valid_geom_types'],
            os.path.join(processing_dir,f'test_dissolve_{layer["layername"]}.json'),
            **bounds
        )
    pass