""" This file holds vaguely AI-related stuff (could use a better name). """
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, balanced_accuracy_score, f1_score, accuracy_score

from statmagic_backend.utils import logger


def make_fullConfMat(actual, prediction, target_names):
    """
    Creates a dataframe containing a confusion matrix as well as summary
    accuracy and F1 statistics.

    Parameters
    ----------
    actual : array-like
        True sample labels
    prediction : array-like
        Predicted sample labels
    target_names : array-like
        Collection of names corresponding to each numerical label

    Returns
    -------
    df : pd.DataFrame
        Dataframe containing result

    """
    cnf_mat = confusion_matrix(actual, prediction)
    ovacc = accuracy_score(actual, prediction)
    balacc = balanced_accuracy_score(actual, prediction)
    weight_f1 = f1_score(actual, prediction, average='weighted')

    tp_and_fn = cnf_mat.sum(1)
    tp_and_fp = cnf_mat.sum(0)
    tp = cnf_mat.diagonal()
    precision = [str(round(num, 2) * 100) + '%' for num in list(tp / tp_and_fp)]
    recall = [str(round(num, 2) * 100) + '%' for num in list(tp / tp_and_fn)]

    # creating dataframe for exporting to excel
    cnf_matrix_df = pd.DataFrame(cnf_mat, columns=target_names)
    cnf_matrix_df = cnf_matrix_df.add_prefix('Predicted - ')
    actual_list = ['Actual - ' + str(x) for x in target_names]
    cnf_matrix_df['Confusion matrix'] = actual_list
    cnf_matrix_df = cnf_matrix_df.set_index('Confusion matrix')
    cnf_matrix_df['User Acc'] = recall

    # adding a row in the dataframe for precision scores
    precision_row = ['Prod Acc']
    precision_row.extend(precision)
    precision_row.append('')

    cnf_matrix_df.loc['Prod Acc'] = precision_row[1:]

    df = cnf_matrix_df.copy()
    df.reset_index(inplace=True)
    rows, cols = df.shape
    blank_row = [" " for x in range(cols)]
    for i in range(rows, rows + 4):
        df.loc[i] = blank_row

    df.at[rows + 1, df.columns[2]] = 'Overall Accuracy'
    df.at[rows + 2, df.columns[2]] = 'Balanced Accuracy'
    df.at[rows + 3, df.columns[2]] = 'Weighted F1 Score'

    df.at[rows + 1, df.columns[3]] = str(round(ovacc, 4) * 100) + '%'
    df.at[rows + 2, df.columns[3]] = str(round(balacc, 4) * 100) + '%'
    df.at[rows + 3, df.columns[3]] = str(round(weight_f1, 4))

    return df
