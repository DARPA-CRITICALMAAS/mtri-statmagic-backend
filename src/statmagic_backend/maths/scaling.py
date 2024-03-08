from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

def standardScale_and_PCA(data_array, var):
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data_array)
    pca = PCA(n_components=var, svd_solver='full')
    pca_data = pca.fit_transform(scaled_data)
    return pca_data, pca

