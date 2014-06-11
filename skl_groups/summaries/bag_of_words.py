from copy import copy

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.externals.six.moves import xrange

from ..features import Features

# TODO: support vlfeat's kmeans algorithms
# (to separate fit() and predict(), need to refactor vlfeat-ctypes a bit)

class BagOfWords(BaseEstimator, TransformerMixin):
    '''
    Transforms a list of bags of features (e.g. a :class:`Features` instance)
    into the bag of words representation:
     1. Run k-means on the set of all points from all bags, to get codewords.
     2. Represent each bag by the count of points assigned to each codeword.

    Parameters
    ----------
    kmeans : KMeans estimator
        Object to run k-means with; :class:`sklearn.cluster.KMeans` or
        :class:`sklearn.cluster.MinibatchKMeans` are most likely.
        Compared to a standard clustering setup, you want a much higher
        ``n_clusters`` (depending on the size and dimensionality, between maybe
        tens and thousands), lowish ``max_iter`` (maybe 100; we don't care so
        much about the exact solution, just that it has a reasonable spread),
        and lower ``n_init`` (same reason). The object should not yet be fit;
        we'll copy it, not modify it.

    Attributes
    ----------
    `kmeans_fit_` : KMeans estimator
        A fit version of the `kmeans` parameter.
    '''
    def __init__(self, kmeans):
        self.kmeans = kmeans

    def _check_fitted(self):
        if not hasattr(self, "kmeans_fit_"):
            raise AttributeError("Model has not been trained yet.")
        self.kmeans_fit_._check_fitted()

    @property
    def n_codewords(self):
        return self.kmeans.n_clusters

    @property
    def codewords(self):
        self._check_fitted()
        return self.kmeans_fit_.cluster_centers_

    def _check_inputs(self, X):
        if isinstance(X, Features):
            X.make_stacked()
        else:
            X = Features(X, stack=True)
        return X

    def _group_assignments(self, X, assignments):
        X_new = np.empty((len(X), self.n_codewords), dtype=np.int32)
        for i in xrange(len(X)):
            start = X._boundaries[i]
            end = X._boundaries[i + 1]

            X_new[i, :] = np.bincount(assignments[start:end],
                                      minlength=self.n_codewords)
        return X_new

    def fit(self, X, y=None):
        '''
        Choose the codewords based on a training set.

        Parameters
        ----------
        X : :class:`Features` or list of arrays of shape ``[n_samples[i], n_features]``
            Training set. If a Features object, it will be stacked.
        '''
        self.kmeans_fit_ = copy(self.kmeans)
        X = self._check_inputs(X)
        self.kmeans_fit_.fit(X.stacked_features) 
        self.codewords_ = self.kmeans_fit_.cluster_centers_
        return self

    def transform(self, X):
        '''
        Transform a list of bag features into its bag-of-words representation.

        Parameters
        ----------
        X : :class:`Features` or list of bag feature arrays
            New data to transform.

        Returns
        -------
        X_new : integer array, shape [len(X), kmeans.n_clusters]
            X transformed into the new space.
        '''
        self._check_fitted()
        X = self._check_inputs(X)
        assignments = self.kmeans_fit_.predict(X.stacked_features)
        return self._group_assignments(X, assignments)

    def fit_transform(self, X):
        '''
        Compute clustering and transform a list of bag features into its
        bag-of-words representation. Like calling fit(X) and then transform(X),
        but more efficient.

        Parameters
        ----------
        X : :class:`Features` or list of bag feature arrays
            New data to transform.

        Returns
        -------
        X_new : integer array, shape [len(X), kmeans.n_clusters]
            X transformed into the new space.
        '''
        X = self._check_inputs(X)
        self.kmeans_fit_ = copy(self.kmeans)
        assignments = self.kmeans_fit_.fit_predict(X.stacked_features) 
        self.codewords_ = self.kmeans_fit_.cluster_centers_
        return self._group_assignments(X, assignments)
