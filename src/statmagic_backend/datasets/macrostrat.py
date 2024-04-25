import geopandas as gpd
from statmagic_backend.geo.transform import get_tiles_for_ll_bounds, download_tiles, process_tiles, dissolve_vector_files_by_property
from pathlib import Path

def macrostrat_from_bounds(bounds, output_path, zoom_level = 10):

    tile_indices = get_tiles_for_ll_bounds(**bounds, zoom_level=zoom_level)

    print("Now downloading Macrostrat data")
    mapbox_tiles = download_tiles(tile_indices, "https://dev.macrostrat.org/tiles/", "carto")

    print("Now converting from Mapbox to json")
    js_paths = process_tiles(mapbox_tiles, tile_indices, Path(output_path).parent, "units", 4096)

    print("Now dissolving tiles")
    dissolve_vector_files_by_property(
        js_paths,
        'map_id',
        ['Polygon', 'MultiPolygon'],
        output_path,
        **bounds
    )


if __name__ == "__main__":
    fp = "/home/efvega/Downloads/focus_areas_MagmaticNiCo.shp"


    data = gpd.read_file(fp)
    data_4326 = data.to_crs(epsg=4326, inplace=False)

    bounds = {
        'n': data_4326.bounds['maxy'].max(),
        's': data_4326.bounds['miny'].min(),
        'e': data_4326.bounds['maxx'].max(),
        'w': data_4326.bounds['minx'].min()
    }

    output_path = "/home/efvega/data/macrostrat/macrostrat.json"
    zoom_level = 3


    macrostrat_from_bounds(bounds = bounds, output_path=output_path, zoom_level=zoom_level)