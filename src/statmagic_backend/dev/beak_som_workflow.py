import sys

from beak.methods.som.nextsomcore.nextsomcore import NxtSomCore
import pickle

import beak.methods.som.argsSOM as asom

args = asom.Args()

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files


BASE_PATH = (files("beak.data") / "LAWLEY22-EXPORT" / "EPSG_3857_RES_5000" / "CLIPPED_USC")

PATH_NUMERICAL = BASE_PATH / "NUMERICAL_IMPUTED_SCALED_STANDARD" / "*.tif"
PATH_CATEGORICAL = BASE_PATH / "CATEGORICAL" / "**/*.tif"

file_patterns = [str(PATH_NUMERICAL), str(PATH_CATEGORICAL)]

#---------------
args.input_file = args.create_list_from_pattern("", file_patterns)
args.geotiff_input=args.input_file      # geotiff_input files, separated by komma

args.output_folder=str(files("beak.data") / "output")         # Folder to save som dictionary and cluster dictionary
args.output_file_somspace= args.output_folder+"/result_som.txt"   # DO NOT CHANGE! Text file that will contain calculated values: som_x som_y b_data1 b_data2 b_dataN umatrix cluster in geospace.

args.som_x = 30                # X dimension of generated SOM
args.som_y = 30               # Y dimension of generated SOM
args.epochs = 10               # Number of epochs to run

# Base parameters required for som calculation.
# Additional optional parameters below:
args.outgeofile= args.output_folder+"/result_geo.txt"             # DO NOT CHANGE!
args.output_file_geospace=args.outgeofile   # Text file that will contain calculated values: {X Y Z} data1 data2 dataN som_x som_y cluster b_data1 b_data2 b_dataN in geospace.

args.kmeans="true"          # Run k-means clustering (true, false)
args.kmeans_init = 5           # Number of initializations
args.kmeans_min = 11            # Minimum number of k-mean clusters
args.kmeans_max = 12           # Maximum number of k-mean clusters

args.neighborhood = 'gaussian'     # Shape of the neighborhood function. gaussian or bubble
args.std_coeff = 0.5               # Coefficient in the Gaussian neighborhood function
args.maptype = 'toroid'            # Type of SOM (sheet, toroid)
args.initialcodebook = None        # File path of initial codebook, 2D numpy.array of float32.
args.radius0 = 0                   # Initial size of the neighborhood
args.radiusN = 1                   # Final size of the neighborhood
args.radiuscooling = 'linear'      # Function that defines the decrease in the neighborhood size as the training proceeds (linear, exponential)
args.scalecooling = 'linear'       # Function that defines the decrease in the learning scale as the training proceeds (linear, exponential)
args.scale0 = 0.1                  # Initial learning rate
args.scaleN = 0.01                 # Final learning rate
args.initialization = 'random'     # Type of SOM initialization (random, pca)
args.gridtype = 'rectangular'      # Type of SOM grid (hexagonal, rectangular)
#args.xmlfile="none"              # SOM inputs as an xml file

args.minN = 0                  # Minimum value for normalization
args.maxN = 1                  # Maximum value for normalization
args.label = None              # Whether data contains label column, true or false

import beak.methods.som.do_nextsomcore_save_results as dnsr
import beak.methods.som.move_to_subfolder as mts

# move existing SOM output files from previous runs into subfolder
mts.move_som_results(args.output_folder, "old_results")

# run SOM
dnsr.run_SOM(args)

import beak.methods.som.plot_som_results as plot
from IPython.display import Image, display, clear_output

# Load cluster dictionary
loaded_cluster_list = plot.load_cluster_dictionary(args.output_folder)
# Plot and save the Davies-Bouldin Index vs Number of Clusters
plot.plot_davies_bouldin(loaded_cluster_list, args.output_folder)

import beak.methods.som.argsPlot
import beak.methods.som.plot_som_results as plot
import beak.methods.som.move_to_subfolder as mts

argsP = beak.methods.som.argsPlot.Args()

argsP.outsomfile= args.output_file_somspace   # som calculation somspace output text file
argsP.som_x= args.som_x         # som x dimension
argsP.som_y= args.som_y         # som y dimension
argsP.input_file= args.input_file   # Input file(*.lrn)
argsP.dir= args.output_folder            # Input file(*.lrn) or directory where som.dictionary was safet to (/output/som.dictionary)
argsP.grid_type= 'rectangular' # grid type (square or hexa), (rectangular or hexagonal)
argsP.redraw='true'       # whether to draw all plots, or only those required for clustering (true: draw all. false:draw only for clustering).
argsP.outgeofile=args.output_file_geospace     # som geospace results txt file
argsP.dataType='grid'       # Data type (scatter or grid)
argsP.noDataValue='-9999'    # noData value

plot.run_plotting_script(argsP)

subfolder_name = "plots"
images, labels = mts.move_figures(args.output_folder, subfolder_name)

# import matplotlib.pyplot as plt
# from IPython.display import clear_output
# import ipyplot
#
# # Clear Matplotlib cache
# plt.close('all')
#
# # Clear output
# clear_output(wait=True)
#
# tabs = [image.split('_')[-2] for image in labels]
#
# print("List of figures:")
# print(labels)
# #print(tabs)
#
# # Plot the images
# #ipyplot.plot_images(images, max_images=50, img_width=250)
# ipyplot.plot_class_representations(images,  labels, img_width=200, show_url=False)
# ipyplot.plot_class_tabs(images, tabs, max_imgs_per_tab=50, img_width=400)
pass