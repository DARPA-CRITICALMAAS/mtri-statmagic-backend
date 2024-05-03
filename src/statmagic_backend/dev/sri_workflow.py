from pathlib import Path
import sys
if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

import numpy as np
from omegaconf import DictConfig

from sri_maper.src.utils import build_hydra_config_notebook, print_config_tree
from sri_maper.src.train import train
from sri_maper.src.test import test
from sri_maper.src.map import build_map
from torch import set_float32_matmul_precision

set_float32_matmul_precision('medium') # reduces floating point precision for computational efficiency
sri_ta3_path = files('sri_maper').parents[0]


def get_experiment_list():
    experiment_paths = Path.glob(sri_ta3_path / "sri_maper/configs/experiment/", "*_classifier_*.yaml")
    experiment_names = [path.stem for path in experiment_paths]
    return experiment_names

def get_preprocess_list():
    preprocess_paths = Path.glob(sri_ta3_path / "sri_maper/configs/preprocess/", "*.yaml")
    preprocess_names = [path.stem for path in preprocess_paths]
    return preprocess_names

def get_trainer_list():
    trainer_paths = Path.glob(sri_ta3_path / "sri_maper/configs/trainer/", "*.yaml")
    trainer_names = [path.stem for path in trainer_paths]
    return trainer_names

def run_experiment(experiment, trainer, preprocess, tif_dir, ckpt_path):
    train_cfg = build_hydra_config_notebook(
        root_dir=sri_ta3_path,
        overrides=[
            f"experiment={experiment}",
            f"logger=csv",
            f"trainer={trainer}",
            f"preprocess={preprocess}",
            f"data.tif_dir={tif_dir}",
            f"ckpt_path={ckpt_path}"
        ]
    )
    # train_metrics, train_objs = train(train_cfg)
    # train_cfg.ckpt_path = train_objs["trainer"].checkpoint_callback.best_model_path # required for test
    # test_metrics, test_objs = test(train_cfg)
    train_cfg.data.batch_size=128
    maniac_maps, _ = build_map(train_cfg)

    return maniac_maps

def plot_likelihood_raster(maniac_maps):
    import rasterio
    import matplotlib.pyplot as plt # TODO: use fancy import

    with rasterio.open(maniac_maps[0], "r") as likelihood_raster:
        likelihood_data = likelihood_raster.read(1)
    plt.imshow(likelihood_data, cmap="turbo")
    plt.colorbar()
    plt.show()