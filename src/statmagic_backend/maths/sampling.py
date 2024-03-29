import numpy as np
import pandas as pd

import logging
logger = logging.getLogger("statmagic_backend")


def randomSample(data_arr, keep_pct):
    """
    Randomly subsets ``data_arr`` according to the probability distribution
    determined by ``keep_pct``.

    Parameters
    ----------
    data_arr : ndarray
        Array to subset
    keep_pct : float
        Percentage of data to keep [0-100].

    Returns
    -------
    ndarray
        Data kept
    ndarray
        Data removed

    """
    keepflt = float(keep_pct/100)
    rand_mask = np.random.choice([True, False], len(data_arr), p=[keepflt, (1-keepflt)])
    return data_arr[rand_mask], data_arr[~rand_mask]


def balancedSamples(dataframe, take_min=False, n=2000):
    dataframe = pd.DataFrame(dataframe)
    if take_min:
        n = min(dataframe[0].value_counts())
        sampled = dataframe.groupby([0]).apply(lambda x: x.sample(n)).reset_index(drop=True)
    else:
        sampled = dataframe.groupby([0]).apply(lambda x: x.sample(min(n, len(x)))).reset_index(drop=True)
    logger.debug("Samples Taken per class")
    logger.debug(sampled[0].value_counts())
    return sampled.to_numpy()


def dropSelectedBandsforSupClass(labeled_data, selectedBands, bandDescList):
    """
    Drops selected bands for sup class.

    Parameters
    ----------
    labeled_data : ndarray
        output from getTrainingDataFrom Features
    selectedBands : list
        the return of bandSelToList
    bandDescList : list
        the return of rasterBandDescAslist

    Returns
    -------
    cds
    bands

    """
    # bandList = bandSelToList(self.dockwidget.stats_table)
    selectedBands.insert(0, 0)
    cds = np.take(labeled_data, selectedBands, axis=1)
    sublist = [x - 1 for x in selectedBands]
    bands = [b for i, b in enumerate(bandDescList) if i in sublist]
    return cds, bands


def label_count(arr):
    """
    Computes the relative frequency of each label in ``arr``.

    Parameters
    ----------
    arr : ndarray
        Input array containing labels

    Returns
    -------
    df : pd.DataFrame
        Dataframe containing, for each record, the Class, number of pixels,
        and percent of labels.

    """
    unis = np.unique(arr, return_counts=True)
    classes = unis[0].astype('uint8')
    counts = unis[1].astype('uint16')
    pcts = (np.divide(unis[1], np.sum(unis[1])) * 100).round(decimals=2)
    df = pd.DataFrame({"Class": classes, "Num_Pixels": counts, "% of Labels": pcts})
    return df
