import numpy as np
import pandas as pd
import geopandas as gpd
import shapely.geometry

from statmagic_backend.sparql.sparql_utils import safe_wkt_load


def csv2gpd(csvFile):
    df = pd.read_csv(csvFile)
    df_clean = df[pd.notna(df["loc_wkt"])]
    df_clean['loc_wkt'] = df_clean['loc_wkt'].apply(safe_wkt_load)
    crs = pd.unique(df_clean["loc_crs"]).item()
    gdf = gpd.GeoDataFrame(df_clean, geometry=df_clean['loc_wkt'], crs=crs)
    return gdf


if __name__ == "__main__":
    gdf = csv2gpd("/home/ajmuelle/PROCESSING/zinc_mineral_site_data.csv")
    gdf["isGeoCol"] = gdf.apply(lambda x: isinstance(x['loc_wkt'], shapely.geometry.GeometryCollection), axis=1)

    filtered_gdf = gdf[np.logical_not(gdf["isGeoCol"])]

    subset_by_columns=gdf.drop('loc_wkt', axis = 1)
    subset_by_columns.to_file("/home/ajmuelle/PROCESSING/zinc.json", driver="GeoJSON")

    pass