#!/usr/bin/python
# -*- coding:utf-8 -*-

import numpy as np

def sec(t, t0=6, tw=0.2, const_gain=0.01, alpha=0.05,
        speed=0.173205, maxg=100):
    # time: ns
    # speed: m/ns
    #
    if not isinstance(t, np.ndarray):
        t = np.array([t])
    beta = alpha * speed / 8.69
    tau = np.array(t - t0, dtype='float')
    g = np.array(t - t0, dtype='float')
    #
    tau1 = tau < 0
    tau2 = tau >= 0
    g[tau1] = 1
    g[tau2] = const_gain + \
            (1 + tau[tau2]/tw)*np.exp(beta*tau[tau2])
    g[g>maxg] = maxg
    if g.size == 1:
        return g[0]
    else:
        return g
