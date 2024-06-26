import numpy as np

from statmagic_backend.maths.utils import hardenedLDivide, is_numeric
import logging
logger = logging.getLogger("statmagic_backend")


def normalKLDiv(mu1=None, sigma1=None, mu2=None, sigma2=None, theta1=None, theta2=None):
    r"""
    Computes the Kullback-Leibler divergence of the normal distribution
    described by parameter vector ``theta1`` from the normal distribution
    described by parameter vector ``theta2``. In common notation one would
    write :maths:`D_{KL}(P(\theta_1) || Q(\theta_2))`, where

    .. maths::

        D_{KL}(P||Q) = \int{p(x)\cdot \log\left({\dfrac{p(x)}{q(x)}}\right)}dx

    The ``theta1`` and ``theta2`` arguments could also be split up into
    explicit ``mu1``, ``Sigma1``, ``mu2``, ``Sigma2`` calling syntax.
    In the event that both ``theta`` and ``mu``, ``Sigma`` are passed
    for a single parameter, the ``theta`` takes precedence.

    Parameters
    ----------
    mu1 : ndarray, optional
        Mean :maths:`\mu_1` of normal distribution :maths:`P`.
    sigma1 : ndarray, optional
        Covariance :maths:`\Sigma_1` of normal distribution :maths:`P`.
    mu2 : ndarray, optional
        Mean :maths:`\mu_2` of normal distribution :maths:`Q`.
    sigma2 : ndarray, optional
        Covariance :maths:`\Sigma_2` of normal distribution :maths:`Q`.
    theta1 : ndarray, optional
        Lexicographic concatenation of ``mu1`` and ``Sigma1``, i.e.
        :maths:`\theta_1=\begin{bmatrix}\mu_1^T \\ \Sigma_1 \end{bmatrix}`
    theta2 : ndarray, optional
        Lexicographic concatenation of ``mu2`` and ``Sigma2``, i.e.
        :maths:`\theta_2=\begin{bmatrix}\mu_2^T \\ \Sigma_2 \end{bmatrix}`

    Returns
    -------
    ndarray
        Array containing the Kullback-Leibler divergence.
    """
    # Parse Inputs
    if theta1 is not None:
        mu1, sigma1 = parse_theta(theta1)
    else:
        mu1 = np.atleast_2d(mu1)
        sigma1 = np.atleast_2d(sigma1)

    if theta2 is not None:
        mu2, sigma2 = parse_theta(theta2)
    else:
        mu2 = np.atleast_2d(mu2)
        sigma2 = np.atleast_2d(sigma2)

    if mu1.shape[0] == 1:
        mu1 = mu1.T
    if mu2.shape[0] == 1:
        mu2 = mu2.T

    # Compute the KL divergence

    # t1 = Sigma1 \ Sigma0
    t1 = hardenedLDivide(sigma2, sigma1)

    t2 = mu2 - mu1

    # temp = (Sigma1 \ t2)
    temp = hardenedLDivide(sigma2, t2)

    return np.array(
        (np.trace(t1) - np.log(np.linalg.det(t1)) + t2.T @ temp - len(mu2)) / 2) \
        .squeeze()


def parse_theta(theta):
    """ Helper function for parsing ``theta`` into ``mu``, ``Sigma``. """

    if type(theta) == list:
        mu, sigma = theta

    elif is_numeric(theta):
        mu = theta[0]
        sigma = theta[1:]

    else:
        raise TypeError('unexpectedInputType: Params was expected to be '
                        'a cell array or a numeric type')

    return np.atleast_2d(mu), np.atleast_2d(sigma)
