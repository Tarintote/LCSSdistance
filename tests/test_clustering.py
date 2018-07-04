import os
import sys
import math
import tempfile
import pytest
import logging
import numpy as np
from dtaidistance import dtw, clustering


logger = logging.getLogger("be.kuleuven.dtai.distance")


def test_clustering():
    s = np.array([
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1],
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1]])

    def test_hook(from_idx, to_idx, distance):
        assert (from_idx, to_idx) in [(3, 0), (4, 1), (5, 2), (1, 0)]
    model = clustering.Hierarchical(dtw.distance_matrix_fast, {}, 2, merge_hook=test_hook,
                                    show_progress=False)
    cluster_idx = model.fit(s)
    assert cluster_idx[0] == {0, 1, 3, 4}
    assert cluster_idx[2] == {2, 5}


def test_clustering_tree(directory=None):
    s = np.array([
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1],
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1],
         [1., 2, 0, 0, 0, 0, 0, 1, 1]])

    def test_hook(from_idx, to_idx, distance):
        assert (from_idx, to_idx) in [(3, 0), (4, 1), (5, 2), (6, 2), (1, 0), (2, 0)]
    model = clustering.Hierarchical(dtw.distance_matrix_fast, {}, merge_hook=test_hook,
                                    show_progress=False)
    modelw = clustering.HierarchicalTree(model)
    cluster_idx = modelw.fit(s)
    assert cluster_idx[0] == {0, 1, 2, 3, 4, 5, 6}

    if directory:
        hierarchy_fn = os.path.join(directory, "hierarchy.png")
        graphviz_fn = os.path.join(directory, "hierarchy.dot")
    else:
        file = tempfile.NamedTemporaryFile()
        hierarchy_fn = file.name + "_hierarchy.png"
        graphviz_fn = file.name + "_hierarchy.dot"
    modelw.plot(hierarchy_fn)
    print("Figure saved to", hierarchy_fn)
    with open(graphviz_fn, "w") as ofile:
        print(modelw.to_dot(), file=ofile)
    print("Dot saved to", graphviz_fn)


def test_linkage_tree(directory=None):
    s = np.array([
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1],
         [0., 0, 1, 2, 1, 0, 1, 0, 0],
         [0., 1, 2, 0, 0, 0, 0, 0, 0],
         [1., 2, 0, 0, 0, 0, 0, 1, 1],
         [1., 2, 0, 0, 0, 0, 0, 1, 1]])

    model = clustering.LinkageTree(dtw.distance_matrix_fast, {})
    cluster_idx = model.fit(s)

    if directory:
        hierarchy_fn = os.path.join(directory, "hierarchy.png")
        graphviz_fn = os.path.join(directory, "hierarchy.dot")
    else:
        file = tempfile.NamedTemporaryFile()
        hierarchy_fn = file.name + "_hierarchy.png"
        graphviz_fn = file.name + "_hierarchy.dot"
    model.plot(hierarchy_fn)
    print("Figure saved to", hierarchy_fn)
    with open(graphviz_fn, "w") as ofile:
        print(model.to_dot(), file=ofile)
    print("Dot saved to", graphviz_fn)


def test_controlchart(directory=None):
    series = np.zeros((600, 60))
    rsrc_fn = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rsrc', 'synthetic_control.data')
    with open(rsrc_fn, 'r') as ifile:
        for idx, line in enumerate(ifile.readlines()):
            series[idx, :] = line.split()
    s = []
    for idx in range(0, 600, 20):
        s.append(series[idx, :])

    model = clustering.LinkageTree(dtw.distance_matrix_fast, {})
    cluster_idx = model.fit(s)

    if directory:
        hierarchy_fn = os.path.join(directory, "hierarchy.png")
    else:
        file = tempfile.NamedTemporaryFile()
        hierarchy_fn = file.name + "_hierarchy.png"
    model.plot(hierarchy_fn)
    print("Figure saved to", hierarchy_fn)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.propagate = 0
    # test_clustering_tree(directory="/Users/wannes/Desktop/")
    # test_linkage_tree(directory="/Users/wannes/Desktop/")
    test_controlchart(directory="/Users/wannes/Desktop/")
