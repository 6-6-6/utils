#!/usr/bin/python
# -*- coding:utf-8 -*-

import numpy as np
from numpy.lib import stride_tricks
from functools import reduce
from numba import njit, prange


class Sinc():

    def __init__(self, data, sample_interval):
        self.base_data = data
        self.sample_interval = sample_interval

    def __call__(self, t):
        # not going to consider complex{192,256}
        if self.base_data[0].dtype in [np.complex64, np.complex128]:
            my_dtype = "complex128"
        else:
            my_dtype = "float64"
        normalized_t = t/self.sample_interval
        # main loop
        output = np.zeros(t.size, dtype=my_dtype)
        for i in range(self.base_data.size):
            output += self.base_data[i] * np.sinc(normalized_t - i)
        return output
    
    def shift_by_delay(self, delay):
        normalized_t_min = 0 - self.base_data.size + 1
        normalized_t_max = self.base_data.size
        normalized_t = np.arange(normalized_t_min, normalized_t_max) + delay/self.sample_interval
        #
        modulation_matrix = stride_tricks.sliding_window_view(np.sinc(normalized_t), self.base_data.size)#.T
        print(modulation_matrix.shape)
        # main loop
        output = modulation_matrix @ self.base_data
        return output
