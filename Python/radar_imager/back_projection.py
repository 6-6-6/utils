#!/usr/bin/python
# -*- coding:utf-8 -*-

import numba
import numpy as np
import h5py


class Projecter():
    def __init__(self,
                 data,
                 position_tx,
                 position_rx,
                 time_axis,
                 projection_map,
                 projection_cache,
                 wavelet_dots=1,
                 beam=[-np.pi,
                       2 * np.pi]):
        # data: a trace of data
        # position: the position of the data
        # time_axis: range time axis, UNIT: ns!!
        # projection map: tuple of: X, Y, Z, while X.size == Y.size ( and X, Y represents pairs of dosts )
        # projection_cache: time_delay_profile.SimpleTimeDelayProfile()
        self.projection_cache = projection_cache
        self.wavelet_dots = wavelet_dots
        self.map_hint = self.parse_projection_map(
            projection_map, position_tx, position_rx, beam)
        self.map = self.spread_data_to_map(data, time_axis)

    def tofile(self, fname):
        with h5py.File(fname, 'w') as f:
            f.create_dataset("data", data=self.map, compression="gzip")

    def parse_projection_map(
            self,
            projection_area,
            antenna_position_tx,
            antenna_position_rx,
            antenna_beam):
        # using the square of cos instead of cos itself to avoid further
        # sqrt()s, see main loop
        beam_left_bound = np.cos(antenna_beam[0] - 1.5 * np.pi)**2
        beam_right_bound = np.cos(antenna_beam[1] - 1.5 * np.pi)**2
        # dx * n + x_0 - antenna_x: the position relative to the antenna of a
        # pixel
        Xt = projection_area[0] - antenna_position_tx[0]
        Yt = projection_area[1] - antenna_position_tx[1]
        Zt = projection_area[2] - antenna_position_tx[2]
        #
        Xr = projection_area[0] - antenna_position_rx[0]
        Yr = projection_area[1] - antenna_position_rx[1]
        Zr = projection_area[2] - antenna_position_rx[2]
        Z = projection_area[2]
        # size of X or Y: the trail; size of Z: the depth
        map_hint = np.zeros(
            [projection_area[0].size, projection_area[2].size],
            dtype='float64')
        # debug
        #from matplotlib import pyplot as plt
        # print(Y)
        # print(beam_left_bound)
        # print(beam_right_bound)
        # plt.plot(Z)
        # plt.show()
        # TODO: rust!!
        for idx_xy in range(Xt.size):
            for idx_z in range(Zt.size):
                # determine bound: TX
                if Xt[idx_xy] < 0:
                    boundt = beam_left_bound
                else:
                    boundt = beam_right_bound
                # determine bound: RX
                if Xr[idx_xy] < 0:
                    boundr = beam_left_bound
                else:
                    boundr = beam_right_bound
                Rt = [Xt[idx_xy], Yt[idx_xy], Zt[idx_z]]
                Rr = [Xr[idx_xy], Yr[idx_xy], Zr[idx_z]]
                #
                if Zt[idx_z] < 0 and \
                        Zt[idx_z]**2 >= boundt * np.dot(Rt, Rt) and \
                        Zr[idx_z]**2 >= boundr * np.dot(Rr, Rr):
                    time_delay_tx = self.projection_cache.get_time_delay(
                        (Xt[idx_xy], Yt[idx_xy], Z[idx_z]), (0, 0, antenna_position_tx[2]))
                    time_delay_rx = self.projection_cache.get_time_delay(
                        (Xr[idx_xy], Yr[idx_xy], Z[idx_z]), (0, 0, antenna_position_rx[2]))
                    map_hint[idx_xy, idx_z] = time_delay_tx + time_delay_rx
                else:
                    map_hint[idx_xy, idx_z] = 0
        # end of TODO
        return map_hint

    def spread_data_to_map(self, data, time_axis):
        print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        sample_interval = time_axis[1] - time_axis[0]
        map_hint = (self.map_hint + time_axis[0]) // sample_interval
        map_hint = map_hint.astype('uint').flatten()
        map_hint_right = map_hint.copy() + self.wavelet_dots
        output_data = np.zeros(
            [map_hint.size, self.wavelet_dots], dtype=data.dtype)
        # spread data to output_data, numba accelerated
        main_loop_spread_data_to_map(
            output_data,
            data,
            map_hint,
            map_hint_right,
            self.wavelet_dots)
        #
        output_data = output_data.reshape(
            (*self.map_hint.shape, self.wavelet_dots))
        output_data[self.map_hint == 0, :] = 0
        return output_data

    def tofile(self, fname):
        with h5py.File(fname, 'w') as output_file:
            output_file.create_dataset("image", data=self.map, compress="gzip")


# TODO: gain
@numba.jit(nopython=True, cache=True)
def main_loop_spread_data_to_map(
        output_data,
        data,
        map_hint,
        map_hint_right,
        wavelet_dots):
    for i in range(map_hint.size):
        if map_hint[i] < data.size - 1 - wavelet_dots:
            tmp = data[map_hint[i]:map_hint_right[i]]
            output_data[i, :] = tmp
