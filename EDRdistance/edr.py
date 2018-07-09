# -*- coding: UTF-8 -*-
"""
dtaidistance.edr
~~~~~~~~~~~~~~~~

Dynamic Time Warping (edr)

:author: Wannes Meert
:copyright: Copyright 2017-2018 KU Leuven, DTAI Research Group.
:license: Apache License, Version 2.0, see LICENSE for details.

"""
import logging
import math
import numpy as np

from .util import SeriesContainer, dtaidistance_dir


logger = logging.getLogger("be.kuleuven.dtai.distance")

try:
    from . import edr_c
except ImportError:
    # logger.info('C library not available')
    edr_c = None

try:
    from tqdm import tqdm
except ImportError:
    logger.info('tqdm library not available')
    tqdm = None


def lb_keogh(s1, s2, window=None, max_dist=None,
             max_step=None, max_length_diff=None):
    """Lowerbound LB_KEOGH"""
    # TODO: This implementation slower than distance() in C
    if window is None:
        window = max(len(s1), len(s2))

    t = 0
    for i in range(len(s1)):
        imin = max(0, i - max(0, len(s1) - len(s2)) - window + 1)
        imax = min(len(s2), i + max(0, len(s2) - len(s1)) + window)
        ui = np.max(s2[imin:imax])
        li = np.min(s2[imin:imax])
        ci = s1[i]
        if ci > ui:
            t += abs(ci - ui)
        else:
            t += abs(ci - li)
    return t


def distance(s1, s2, epsilon=None, window=None, max_dist=None,
             max_step=None, max_length_diff=None, penalty=None, psi=None,
             use_c=False):
    """
    Dynamic Time Warping.

    This function keeps a compact matrix, not the full warping paths matrix.

    :param s1: First sequence
    :param s2: Second sequence
    :param window: Only allow for maximal shifts from the two diagonals smaller than this number.
        It includes the diagonal, meaning that an Euclidean distance is obtained by setting weight=1.
    :param max_dist: Stop if the returned values will be larger than this value
    :param max_step: Do not allow steps larger than this value
    :param max_length_diff: Return infinity if length of two series is larger
    :param penalty: Penalty to add if compression or expansion is applied
    :param psi: Psi relaxation parameter (ignore start and end of matching).
        Useful for cyclical series.
    :param use_c: Use fast pure c compiled functions

    Returns: edr distance
    """
    if use_c:
        return distance_fast(s1, s2,
                             epsilon=epsilon,
                             window=window,
                             max_dist=max_dist,
                             max_step=max_step,
                             max_length_diff=max_length_diff,
                             penalty=penalty,
                             psi=psi)
    r, c = len(s1), len(s2)
    # my追記
    if epsilon is None:
        epsilon = 0.0
    ####
    if max_length_diff is not None and abs(r - c) > max_length_diff:
        return np.inf
    if window is None:
        window = max(r, c)
    if not max_step:
        max_step = np.inf
    else:
        max_step *= max_step
    if not max_dist:
        max_dist = np.inf
    else:
        max_dist *= max_dist
    if not penalty:
        penalty = 0
    else:
        penalty *= penalty
    if psi is None:
        psi = 0
    length = min(c + 1, abs(r - c) + 2 * (window - 1) + 1 + 1 + 1)
    # print("length (py) = {}".format(length))
    edr = np.full((2, length), np.inf)
    for i in range(psi + 1):
        edr[0, i] = 0
    last_under_max_dist = 0
    skip = 0
    i0 = 1
    i1 = 0
    psi_shortest = np.inf
    for i in range(r):
        # print("i={}".format(i))
        # print(edr)
        if last_under_max_dist == -1:
            prev_last_under_max_dist = np.inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        skipp = skip
        skip = max(0, i - max(0, r - c) - window + 1)
        i0 = 1 - i0
        i1 = 1 - i1
        # my変更
        edr[i1, :] = np.inf  # from
        ####
        j_start = max(0, i - max(0, r - c) - window + 1)
        j_end = min(c, i + max(0, c - r) + window)
        if edr.shape[1] == c + 1:
            skip = 0
        if psi != 0 and j_start == 0 and i < psi:
            edr[i1, 0] = 0
        for j in range(j_start, j_end):
            # my change
            # d = (s1[i] - s2[j])**2 #from
            d = np.fabs(s1[i] - s2[j])  # to
            ####
            if d > max_step:
                continue
            assert j + 1 - skip >= 0
            assert j - skipp >= 0
            assert j + 1 - skipp >= 0
            assert j - skip >= 0
            # my addition
            if d <= epsilon:
                cand_values = np.array(
                    [edr[i0, j - skipp], edr[i0, j + 1 - skipp] + 1, edr[i1, j - skip] + 1])
            else:
                cand_values = np.array(
                    [edr[i0, j - skipp] + 1, edr[i0, j + 1 - skipp] + 1, edr[i1, j - skip] + 1])
            ####
            # my change
            edr[i1, j + 1 -
                skip] = np.nanmin(cand_values[cand_values != np.inf])
            ####

            # print('({},{}), ({},{}), ({},{})'.format(
            #    i0, j - skipp, i0, j + 1 - skipp, i1, j - skip))
            # print('{}, {}, {}'.format(
            #    edr[i0, j - skipp], edr[i0, j + 1 - skipp], edr[i1, j - skip]))
            # print('i={}, j={}, d={}, skip={}, skipp={}'.format(
            #    i, j, d, skip, skipp))
            # print(edr)
            if edr[i1, j + 1 - skip] <= max_dist:
                last_under_max_dist = j
            else:
                # print('above max_dist', edr[i1, j + 1 - skip], i1, j + 1 - skip)
                edr[i1, j + 1 - skip] = np.inf
                if prev_last_under_max_dist + 1 - skipp < j + 1 - skip:
                    # print("break")
                    break
        if last_under_max_dist == -1:
            # print('early stop')
            # print(edr)
            return np.inf
        if psi != 0 and j_end == len(s2) and len(s1) - 1 - i <= psi:
            psi_shortest = min(psi_shortest, edr[i1, length - 1])
    if psi == 0:
        d = edr[i1, min(c, c + window - 1) - skip]
        # d = math.sqrt(edr[i1, min(c, c + window - 1) - skip])
    else:
        ic = min(c, c + window - 1) - skip
        vc = edr[i1, ic - psi:ic + 1]
        d = min(np.min(vc), psi_shortest)
        d = math.sqrt(d)
    return d


def distance_fast(s1, s2, epsilon=None, window=None, max_dist=None,
                  max_step=None, max_length_diff=None, penalty=None, psi=None):
    """Fast C version of :meth:`distance`."""
    if edr_c is None:
        _print_library_missing()
        return None
    if epsilon is None:
        epsilon = 0.0
    if window is None:
        window = 0
    if max_dist is None:
        max_dist = 0
    if max_step is None:
        max_step = 0
    if max_length_diff is None:
        max_length_diff = 0
    if penalty is None:
        penalty = 0
    if psi is None:
        psi = 0

    d = edr_c.distance_nogil(s1, s2,
                             epsilon=epsilon,
                             window=window,
                             max_dist=max_dist,
                             max_step=max_step,
                             max_length_diff=max_length_diff,
                             penalty=penalty,
                             psi=psi)
    return d


def _distance_with_params(t):
    return distance(t[0], t[1], **t[2])


def _distance_c_with_params(t):
    return edr_c.distance(t[0], t[1], **t[2])


def warping_paths(s1, s2, window=None, max_dist=None,
                  max_step=None, max_length_diff=None, penalty=None, psi=None):
    """
    Dynamic Time Warping.

    The full matrix of all warping paths is build.

    :param s1: First sequence
    :param s2: Second sequence
    :param window: see :meth:`distance`
    :param max_dist: see :meth:`distance`
    :param max_step: see :meth:`distance`
    :param max_length_diff: see :meth:`distance`
    :param penalty: see :meth:`distance`
    :param psi: see :meth:`distance`
    :returns: (edr distance, edr matrix)
    """
    r, c = len(s1), len(s2)
    if max_length_diff is not None and abs(r - c) > max_length_diff:
        return np.inf
    if window is None:
        window = max(r, c)
    if not max_step:
        max_step = np.inf
    else:
        max_step *= max_step
    if not max_dist:
        max_dist = np.inf
    else:
        max_dist *= max_dist
    if not penalty:
        penalty = 0
    else:
        penalty *= penalty
    if psi is None:
        psi = 0
    edr = np.full((r + 1, c + 1), np.inf)
    # edr[0, 0] = 0
    for i in range(psi + 1):
        edr[0, i] = 0
        edr[i, 0] = 0
    last_under_max_dist = 0
    i0 = 1
    i1 = 0
    for i in range(r):
        if last_under_max_dist == -1:
            prev_last_under_max_dist = np.inf
        else:
            prev_last_under_max_dist = last_under_max_dist
        last_under_max_dist = -1
        i0 = i
        i1 = i + 1
        # print('i =', i, 'skip =',skip, 'skipp =', skipp)
        # jmin = max(0, i - max(0, r - c) - window + 1)
        # jmax = min(c, i + max(0, c - r) + window)
        # print(i,jmin,jmax)
        # x = edr[i, jmin-skipp:jmax-skipp]
        # y = edr[i, jmin+1-skipp:jmax+1-skipp]
        # print(x,y,edr[i+1, jmin+1-skip:jmax+1-skip])
        # edr[i+1, jmin+1-skip:jmax+1-skip] = np.minimum(x,
        #                                                y)
        for j in range(max(0, i - max(0, r - c) - window + 1), min(c, i + max(0, c - r) + window)):
            # print('j =', j, 'max=',min(c, c - r + i + window))
            d = (s1[i] - s2[j])**2
            if max_step is not None and d > max_step:
                continue
            # print(i, j + 1 - skip, j - skipp, j + 1 - skipp, j - skip)
            edr[i1, j + 1] = d + min(edr[i0, j],
                                     edr[i0, j + 1] + penalty,
                                     edr[i1, j] + penalty)
            # edr[i + 1, j + 1 - skip] = d + min(edr[i + 1, j + 1 - skip], edr[i + 1, j - skip])
            if max_dist is not None:
                if edr[i1, j + 1] <= max_dist:
                    last_under_max_dist = j
                else:
                    edr[i1, j + 1] = np.inf
                    if prev_last_under_max_dist < j + 1:
                        break
        if max_dist is not None and last_under_max_dist == -1:
            # print('early stop')
            # print(edr)
            return np.inf, edr
    edr = np.sqrt(edr)
    if psi == 0:
        d = edr[i1, min(c, c + window - 1)]
    else:
        ir = i1
        ic = min(c, c + window - 1)
        vr = edr[ir-psi:ir+1, ic]
        vc = edr[ir, ic-psi:ic+1]
        mir = np.argmin(vr)
        mic = np.argmin(vc)
        if vr[mir] < vc[mic]:
            edr[ir-psi+mir+1:ir+1, ic] = -1
            d = vr[mir]
        else:
            edr[ir, ic - psi + mic + 1:ic+1] = -1
            d = vc[mic]
    return d, edr


def distance_matrix_func(use_c=False, use_nogil=False, parallel=False, show_progress=False):
    def distance_matrix_wrapper(seqs, **kwargs):
        return distance_matrix(seqs, parallel=parallel, use_c=use_c,
                               use_nogil=use_nogil,
                               show_progress=show_progress, **kwargs)
    return distance_matrix_wrapper


def distance_matrix(s, epsilon=None, max_dist=None, max_length_diff=None,
                    window=None, max_step=None, penalty=None, psi=None,
                    block=None, parallel=False,
                    use_c=False, use_nogil=False, show_progress=False):
    """Distance matrix for all sequences in s.

    :param s: Iterable of series
    :param window: see :meth:`distance`
    :param max_dist: see :meth:`distance`
    :param max_step: see :meth:`distance`
    :param max_length_diff: see :meth:`distance`
    :param penalty: see :meth:`distance`
    :param psi: see :meth:`distance`
    :param block: Only compute block in matrix. Expects tuple with begin and end, e.g. ((0,10),(20,25)) will
        only compare rows 0:10 with rows 20:25.
    :param parallel: Use parallel operations
    :param use_c: Use c compiled Python functions (it is recommended to use use_nogil)
    :param use_nogil: Use pure c functions
    :param show_progress: Show progress using the tqdm library
    """
    if parallel and (not use_c or not use_nogil):
        try:
            import multiprocessing as mp
            logger.info('Using multiprocessing')
        except ImportError:
            parallel = False
            mp = None
    else:
        mp = None
    dist_opts = {
        'epsilon': epsilon,
        'max_dist': max_dist,
        'max_step': max_step,
        'window': window,
        'max_length_diff': max_length_diff,
        'penalty': penalty,
        'psi': psi
    }
    s = SeriesContainer.wrap(s)
    dists = None
    if max_length_diff is None:
        max_length_diff = np.inf
    large_value = np.inf
    logger.info('Computing distances')
    if use_c:
        for k, v in dist_opts.items():
            if v is None:
                dist_opts[k] = 0.0
    if use_c and use_nogil:
        logger.info("Compute distances in pure C")
        dist_opts['block'] = block
        if parallel:
            logger.info("Use parallel computation")
            dists = edr_c.distance_matrix_nogil_p(s, **dist_opts)
        else:
            logger.info("Use serial computation")
            dists = edr_c.distance_matrix_nogil(s, **dist_opts)
    if use_c and not use_nogil:
        logger.info("Compute distances in Python compiled C")
        if parallel:
            logger.info("Use parallel computation")
            dists = np.zeros((len(s), len(s))) + large_value
            if block is None:
                idxs = np.triu_indices(len(s), k=1)
            else:
                idxsl_r = []
                idxsl_c = []
                for r in range(block[0][0], block[0][1]):
                    for c in range(max(r + 1, block[1][0]), min(len(s), block[1][1])):
                        idxsl_r.append(r)
                        idxsl_c.append(c)
                idxs = (np.array(idxsl_r), np.array(idxsl_c))
            with mp.Pool() as p:
                dists[idxs] = p.map(_distance_c_with_params, [
                                    (s[r], s[c], dist_opts) for c, r in zip(*idxs)])
                # pbar = tqdm(total=int((len(s)*(len(s)-1)/2)))
                # for r in range(len(s)):
                #     dists[r,r+1:len(s)] = p.map(distance, [(s[r],s[c], dist_opts) for c in range(r+1,len(cur))])
                #     pbar.update(len(s) - r - 1)
                # pbar.close()
        else:
            logger.info("Use serial computation")
            dist_opts['block'] = block
            dists = edr_c.distance_matrix(s, **dist_opts)
    if not use_c:
        logger.info("Compute distances in Python")
        if parallel:
            logger.info("Use parallel computation")
            dists = np.zeros((len(s), len(s))) + large_value
            if block is None:
                idxs = np.triu_indices(len(s), k=1)
            else:
                idxsl_r = []
                idxsl_c = []
                for r in range(block[0][0], block[0][1]):
                    for c in range(max(r + 1, block[1][0]), min(len(s), block[1][1])):
                        idxsl_r.append(r)
                        idxsl_c.append(c)
                idxs = (np.array(idxsl_r), np.array(idxsl_c))
            with mp.Pool() as p:
                dists[idxs] = p.map(_distance_with_params, [
                                    (s[r], s[c], dist_opts) for c, r in zip(*idxs)])
                # pbar = tqdm(total=int((len(s)*(len(s)-1)/2)))
                # for r in range(len(s)):
                #     dists[r,r+1:len(s)] = p.map(distance, [(s[r],s[c], dist_opts) for c in range(r+1,len(cur))])
                #     pbar.update(len(s) - r - 1)
                # pbar.close()
        else:
            logger.info("Use serial computation")
            dists = np.zeros((len(s), len(s))) + large_value
            if block is None:
                it_r = range(len(s))
            else:
                it_r = range(block[0][0], block[0][1])
            if show_progress:
                it_r = tqdm(it_r)
            for r in it_r:
                if block is None:
                    it_c = range(r + 1, len(s))
                else:
                    it_c = range(
                        max(r + 1, block[1][0]), min(len(s), block[1][1]))
                for c in it_c:
                    if abs(len(s[r]) - len(s[c])) <= max_length_diff:
                        dists[r, c] = distance(s[r], s[c], **dist_opts)
    return dists


def distance_matrix_fast(s, epsilon=None, max_dist=None, max_length_diff=None,
                         window=None, max_step=None, penalty=None, psi=None,
                         block=None, parallel=True, show_progress=False):
    """Fast C version of :meth:`distance_matrix`."""
    if edr_c is None:
        _print_library_missing()
        return None
    return distance_matrix(s, epsilon=epsilon, max_dist=max_dist, max_length_diff=max_length_diff,
                           window=window, max_step=max_step, penalty=penalty, psi=psi,
                           block=block, parallel=parallel,
                           use_c=True, use_nogil=True, show_progress=show_progress)


def warping_path(from_s, to_s, **kwargs):
    """Compute warping path between two sequences."""
    dist, paths = warping_paths(from_s, to_s, **kwargs)
    path = best_path(paths)
    return path


def warp(from_s, to_s, **kwargs):
    """Warp a function to optimally match a second function.

    Same options as :meth:`warping_paths`.
    """
    path = warping_path(from_s, to_s, **kwargs)
    from_s2 = np.zeros(len(to_s))
    from_s2_cnt = np.zeros(len(to_s))
    for r_c, c_c in path:
        from_s2[c_c] += from_s[r_c]
        from_s2_cnt[c_c] += 1
    from_s2 /= from_s2_cnt
    return from_s2, path


def _print_library_missing():
    logger.error("The compiled dtaidistance C library is not available.\n" +
                 "See the documentation for alternative installation options.")


def best_path(paths):
    """Compute the optimal path from the nxm warping paths matrix."""
    i, j = int(paths.shape[0] - 1), int(paths.shape[1] - 1)
    p = []
    if paths[i, j] != -1:
        p.append((i - 1, j - 1))
    while i > 0 and j > 0:
        c = np.argmin([paths[i - 1, j - 1], paths[i - 1, j], paths[i, j - 1]])
        if c == 0:
            i, j = i - 1, j - 1
        elif c == 1:
            i = i - 1
        elif c == 2:
            j = j - 1
        if paths[i, j] != -1:
            p.append((i - 1, j - 1))
    p.pop()
    p.reverse()
    return p


def best_path2(paths):
    """Compute the optimal path from the nxm warping paths matrix."""
    m = paths
    path = []
    r, c = m.shape
    r -= 1
    c -= 1
    v = m[r, c]
    path.append((r - 1, c - 1))
    while r > 1 or c > 1:
        r_c, c_c = r, c
        if r >= 1 and c >= 1 and m[r - 1, c - 1] <= v:
            r_c, c_c, v = r - 1, c - 1, m[r - 1, c - 1]
        if r >= 1 and m[r - 1, c] <= v:
            r_c, c_c, v = r - 1, c, m[r - 1, c]
        if c >= 1 and m[r, c - 1] <= v:
            r_c, c_c, v = r, c - 1, m[r, c - 1]
        path.append((r_c - 1, c_c - 1))
        r, c = r_c, c_c
    path.reverse()
    return path