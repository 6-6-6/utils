#!/usr/bin/python
# -*- coding:utf-8 -*-

import numpy as np
from functools import reduce

class Sinc():

    def __init__(self, data, sample_interval):
        self.base_data = data
        self.sample_interval = sample_interval

    def __call__(self, t):
        tmp = np.zeros(t.size)
        for i in range(self.base_data.size):
            v = self.base_data[i] * np.sinc(t/self.sample_interval - i)
            tmp += v
        return tmp
