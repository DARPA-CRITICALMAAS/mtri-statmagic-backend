import sys
from importlib import import_module
from pathlib import Path
import pickle
from pkgutil import iter_modules

from beak.models import *
from beak.utilities.io import load_model
from beak.methods.som.nextsomcore.nextsomcore import NxtSomCore
import beak.methods.som.argsSOM as asom
import beak.methods.som.argsPlot
import beak.methods.som.move_to_subfolder as mts
import beak.methods.som.plot_som_results as plot
import beak.methods.som.do_nextsomcore_save_results as dnsr

from statmagic_backend.utils import logger

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files


def parse_beak_models():
    models = {}
    model_modules = sys.modules["beak.models"]
    for submodule in iter_modules(model_modules.__path__):
        imported_submodule = import_module(f"beak.models.{submodule.name}")
        models.update(imported_submodule.models)
    pass


def get_input_filenames(*args):
    """
    Given an arbitrary number of path globs, return a list of specific paths
    fitting those glob patterns.
    
    Parameters
    ----------
    *args:
        Each positional argument should be a path glob.

    Returns
    -------
    input_filenames : list
        List of str where each element is a specific file path
    """
    globs = [arg for arg in args if arg]
    input_filenames = asom.Args().create_list_from_pattern("", globs)
    return input_filenames


def prepare_args(numerical_path, categorical_path, output_folder):
    """
    Set up basic path arguments needed by both the SOM workflow and the plots.

    Parameters
    ----------
    numerical_path : str | Path | Traversable
        Path to the numerical data (can include a glob like ``*.tif``)
    categorical_path : str | Path | Traversable
        Path to the categorical data (can include a glob like ``*.tif``)
    output_folder : str
        Path to where the user wants to save the outputs from SOM

    Returns
    -------
    input_files : list
        Result of expanding out ``numerical_path`` and ``categorical_path``.
    output_file_somspace : str
        Path to text file that will contain calculated values

        .. code::

            som_x
            som_y
            b_data1
            b_data2
            b_dataN
            umatrix

        clustered in geospace.
    outgeofile : str
        Path to text file that will contain calculated values:

        .. code::

            {X Y Z}
            data1
            data2
            ...
            dataN
            som_x
            som_y
            cluster
            b_data1
            b_data2
            ...
            b_dataN

        in geospace.
    """
    input_files = get_input_filenames(numerical_path, categorical_path)
    output_file_somspace = str(Path(output_folder) / "result_som.txt")
    outgeofile = str(Path(output_folder) / "result_geo.txt")

    return input_files, output_file_somspace, outgeofile


def beak_som_workflow(som_args):
    """
    Runs Beak's Self-Organizing Maps workflow.

    Parameters
    ----------
    som_args : dict
        Arguments passed to the internal SOM call

    Notes
    -----
    No return value. Creates output files in ``output_folder``.
    """
    # create instance of Args
    args = asom.Args()
    #---------------

    # populate args with the values passed via dictionary
    for key, value in som_args.items():
        setattr(args, key, value)

    # move existing SOM output files from previous runs into subfolder
    mts.move_som_results(args.output_folder, "old_results")

    # run SOM
    dnsr.run_SOM(args)


def plot_som_results(plot_args):
    """
    Plots the results of Beak's Self Organizing Maps workflow.

    Parameters
    ----------
    plot_args : dict
        Arguments passed to the Beak plotting utilities

    Notes
    -----
    No return value. Creates output files in ``output_folder``.
    """
    output_folder = plot_args["dir"]

    # Load cluster dictionary
    loaded_cluster_list = plot.load_cluster_dictionary(output_folder)

    # Plot and save the Davies-Bouldin Index vs Number of Clusters
    plot.plot_davies_bouldin(loaded_cluster_list, output_folder)

    argsP = beak.methods.som.argsPlot.Args()

    for key, value in plot_args.items():
        setattr(argsP, key, value)

    plot.run_plotting_script(argsP)

    subfolder_name = "plots"
    images, labels = mts.move_figures(output_folder, subfolder_name)


if __name__ == "__main__":
    parse_beak_models()
    BASE_PATH = (files("beak.data") / "LAWLEY22-EXPORT" / "EPSG_3857_RES_5000" / "CLIPPED_USC")

    numerical_path = BASE_PATH / "NUMERICAL_IMPUTED_SCALED_STANDARD" / "*.tif"
    categorical_path = BASE_PATH / "CATEGORICAL" / "**/*.tif"

    output_folder = str(files("beak.data") / "output")

    input_files, output_file_somspace, outgeofile = prepare_args(numerical_path, categorical_path, output_folder)

    som_args = {
        "input_file": input_files,
        "geotiff_input": input_files,      # geotiff_input files, separated by comma
        "som_x": 30,
        "som_y": 30,
        "epochs": 10,
        "kmeans": "true",
        "kmeans_init": 5,
        "kmeans_min": 11,
        "kmeans_max": 12,
        "neighborhood": "gaussian",
        "std_coeff": 0.5,
        "maptype": "toroid",
        # "initialcodebook": None,
        "radius0": 0,
        "radiusN": 1,
        "radiuscooling": "linear",
        "scalecooling": "linear",
        "scale0": 0.1,
        "scaleN": 0.01,
        "initialization": "random",
        "gridtype": "hexagonal",
        "output_file_somspace": output_file_somspace,
        # Additional optional parameters below:
        "outgeofile": outgeofile,
        "output_file_geospace": outgeofile
    }
    plot_args = {
        "som_x": som_args["som_x"],
        "som_y": som_args["som_y"],
        "input_file": input_files,
        "outsomfile": output_file_somspace,
        "dir": output_folder,
        "grid_type": 'rectangular',  # grid type (square or hexa), (rectangular or hexagonal)
        "redraw": 'true',  # whether to draw all plots, or only those required for clustering (true: draw all. false:draw only for clustering).
        "outgeofile": outgeofile,
        "dataType": 'grid',  # Data type (scatter or grid)
        "noDataValue": '-9999'  # noData value
    }

    beak_som_workflow(som_args)
    plot_som_results(plot_args)
