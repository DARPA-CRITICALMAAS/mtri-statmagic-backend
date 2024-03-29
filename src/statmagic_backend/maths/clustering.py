import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from statmagic_backend.utils import logger


def doPCA_kmeans(pred_data, bool_arr, nclust, varexp, pca_bool):
    """
    Computes PCA followed by kmeans clustering.

    Parameters
    ----------
    pred_data : array-like
        Data on which PCA and clustering will be performed
    bool_arr : array-like
        Indicator function for data to omit from PCA and clustering
    nclust : int
        Number of clusters
    varexp : int
        Number of components to keep
    pca_bool : bool
        If ``False``, don't run PCA

    Returns
    -------
    labels : ndarray
        Cluster member labels
    km : sklearn.cluster.MiniBatchKMeans
        Fitted model for k-means
    pca : sklearn.decomposition.PCA
        Fitted model for PCA
    fitdat : ndarray
        Fitted data according to PCA (if ``pca_bool`` is ``False``, this is just
        the input data)

    """
    km = MiniBatchKMeans(n_clusters=nclust, init='k-means++', random_state=101)
    pca = PCA(n_components=varexp, svd_solver='full')
    if np.count_nonzero(bool_arr == 1) < 1:
        if pca_bool:
            standata = StandardScaler().fit_transform(pred_data)
            fitdat = pca.fit_transform(standata)
            print(f'PCA uses {pca.n_components_} to get to {varexp} variance explained')
            km.fit_predict(fitdat)
            labels = km.labels_ + 1
        else:
            fitdat = pred_data
            km.fit_predict(fitdat)
            labels = km.labels_ + 1
    else:
        if pca_bool:
            idxr = bool_arr.reshape(pred_data.shape[0])
            pstack = pred_data[idxr == 0, :]
            standata = StandardScaler().fit_transform(pstack)
            fitdat = pca.fit_transform(standata)
            print(f'PCA uses {pca.n_components_} to get to {varexp} variance explained')
            km.fit_predict(fitdat)
            labels = km.labels_ + 1
        else:
            idxr = bool_arr.reshape(pred_data.shape[0])
            fitdat = pred_data[idxr == 0, :]
            km.fit_predict(fitdat)
            labels = km.labels_ + 1
    return labels, km, pca, fitdat


def unpack_fullK(Kdict):
    """Unpacks a dictionary according to a set of fixed expected keys."""
    labels = Kdict['labels']
    km = Kdict['km']
    pca = Kdict['pca']
    ras_dict = Kdict['ras_dict']
    bool_arr = Kdict['bool_arr']
    fitdat = Kdict['fitdat']
    rasBands = Kdict['rasBands']
    nclust = Kdict['nclust']
    # Maybe look into making an unpack full, masked, and training for different needs
    if 'class_arr' in Kdict.keys():
        class_arr = Kdict['class_arr']
        return labels, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust, class_arr
    else:
        return labels, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust


def clusterDataInMask(pred_data, class_data, nodata_mask, nclust, varexp, pca_bool, clusclass):
    noncluster_mask = np.isin(class_data, clusclass, invert=True)
    bool_arr = np.logical_or(noncluster_mask, nodata_mask)
    labels, km, pca, fitdat = doPCA_kmeans(pred_data, bool_arr, nclust, varexp, pca_bool)
    return labels, km, pca, fitdat, bool_arr

def soft_clustering_weights(data, cluster_centres, m):
    Nclusters = cluster_centres.shape[0]
    Ndp = data.shape[0]
    # Get distances from the cluster centres for each data point and each cluster
    EuclidDist = np.zeros((Ndp, Nclusters))
    for i in range(Nclusters):
        EuclidDist[:, i] = np.sum((data - np.matlib.repmat(cluster_centres[i], Ndp, 1)) ** 2, axis=1)
    # Denominator of the weight from wikipedia:
    invWeight = EuclidDist ** (2 / (m - 1)) * np.matlib.repmat(
        np.sum((1. / EuclidDist) ** (2 / (m - 1)), axis=1).reshape(-1, 1), 1, Nclusters)
    Weight = 1. / invWeight
    return Weight


def kmeans_fit_predict(data_array, num_clusters):
    km = MiniBatchKMeans(n_clusters=num_clusters, init='k-means++', n_init='auto', random_state=101)
    km.fit_predict(data_array)
    return km
