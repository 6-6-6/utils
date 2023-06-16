#!/usr/bin/python
#-*- coding:utf-8 -*-

import pickle
import numpy as np
from pathlib import Path
from filelock import FileLock
from deprecated import deprecated
from scipy.optimize import minimize

# m / ns
SPEED_OF_LIGHT = 0.3

class SimpleTimeDelayProfile():
    def __init__(self, cache_path, lock_path, layers=tuple()):
        ## layers: contains the (epsilon above the depth, depth) of layers
        self.cache_path = Path(cache_path)
        self.lock = lock_path
        self.layers = layers
        if False:#self.cache_path.exists():
            #with FileLock(self.lock):
            with open(self.cache_path, 'rb') as cache_file:
                self.cache = pickle.load(cache_file)
            # TODO: error messages
            print(layers)
            compared = (self.cache["layers"] != layers)
            if compared.all():
                raise ValueError
        else:
            self.cache = dict()
            self.cache["layers"] = layers
    
    # this function is like a piece of s**t
    # TODO: rewrite!!!
    #
    def get_time_delay(self, pos_pixel: tuple, pos_antenna: tuple):
        ## relative position: contains the image point relative to antenna position (x,y,z)
        ## returns time delay of a specific relative position, UNIT: ns
        pos_pixel2 = (pos_pixel[0] - pos_antenna[0], pos_pixel[1] - pos_antenna[1], pos_pixel[2])
        # if cache exists, use it
        '''
        if pos_pixel2[0] in self.cache:
            if pos_pixel2[1] in self.cache.get(pos_pixel2[0]):
                if pos_pixel2[2] in self.cache.get(pos_pixel2[0]).get(pos_pixel2[1]):
                    if pos_antenna[2] in self.cache.get(pos_pixel2[0]).get(pos_pixel2[1]).get(pos_pixel2[2]):
                        time_delay = self.cache.get(pos_pixel2[0]).get(pos_pixel2[1]).get(pos_pixel2[2]).get(pos_antenna[2])
                        return time_delay
        '''
        # else: if there is no value in cache, we will calculate it and update the cache
        my_time_delay = self.calculate_time_delay(pos_pixel2, pos_antenna[2])
        time_delay = my_time_delay
        '''
        if pos_pixel2[0] in self.cache:
            if pos_pixel2[1] in self.cache.get(pos_pixel2[0]):
                if pos_pixel2[2] in self.cache.get(pos_pixel2[0]).get(pos_pixel2[1]):
                    self.cache[pos_pixel2[0]][pos_pixel2[1]][pos_pixel2[2]][pos_antenna[2]] = my_time_delay
                else:
                    self.cache[pos_pixel2[0]][pos_pixel2[1]][pos_pixel2[2]] = {pos_antenna[2]: my_time_delay}
            else:
                self.cache[pos_pixel2[0]][pos_pixel2[1]] = { pos_pixel2[2]: {pos_antenna[2]: my_time_delay} }
        else:
            self.cache[pos_pixel2[0]] = { pos_pixel2[1]: { pos_pixel2[2]: {pos_antenna[2]: my_time_delay} } }
        '''
        return time_delay


    @deprecated(version='asap', reason="use calculate_time_delay, which considers refraction")
    def calculate_time_delay_old(self, relative_position_xy: tuple, z_antenna: float):
        # tuple to ndarray
        pixel = np.array(relative_position_xy)
        relative_position = pixel.copy()
        relative_position[2] -= z_antenna
        # the slope
        if relative_position[2] == 0:
            k=0
        else:
            k = relative_position / relative_position[2]
        #print(k)
        # if there is no layers, simply calculate the two-way travel time
        if len(self.layers) == 0:
            # distance / speed
            time_delay = np.linalg.norm(relative_position) / SPEED_OF_LIGHT
        #elif len(self.layers) == 1:
        #    # distance / speed
        #    time_delay = np.linalg.norm(relative_position) / (SPEED_OF_LIGHT / np.sqrt(self.layers[0][0]))
        # calculate travel time by layers
        else:
            if pixel[2] > 0:
                time_delay = np.linalg.norm(relative_position) / SPEED_OF_LIGHT * np.sqrt(self.layers[0][0])
            else:
                time_delay = np.linalg.norm(k * z_antenna) / SPEED_OF_LIGHT * np.sqrt(self.layers[0][0])
                z0 = 0
                for layer in self.layers[1:]:
                    #print(layer)
                    #print(z0)
                    #print(layer[0])
                    if pixel[2] > layer[1]:
                        time_delay += np.linalg.norm(k * (pixel[2] - z0)) / SPEED_OF_LIGHT * np.sqrt(layer[0])
                        break
                    else:
                        time_delay += np.linalg.norm(k * (layer[1] - z0)) / SPEED_OF_LIGHT * np.sqrt(layer[0])
                        z0 = layer[1]
            return time_delay

    def calculate_time_delay(self, relative_position_xy: tuple, z_antenna: float):
        # define layers
        incident_points = [[0, z_antenna]]
        sqrt_epsilons = []
        for layer in self.layers:
            if relative_position_xy[2] < layer[1]:
                incident_points.append([0, layer[1]])
                sqrt_epsilons.append(np.sqrt(layer[0]))
            elif relative_position_xy[2] >= layer[1]:
                incident_points.append([np.linalg.norm(relative_position_xy[:2]), relative_position_xy[2]])
                sqrt_epsilons.append(np.sqrt(layer[0]))
                break
        # ndarrayize
        incident_points = np.array(incident_points)
        # initialize time_delay
        time_delay = 0
        if len(sqrt_epsilons) == 1:
            time_delay += np.linalg.norm(incident_points[1] - incident_points[0]) / SPEED_OF_LIGHT * sqrt_epsilons[0]
            return time_delay
        elif len(sqrt_epsilons) >= 2:
            ret = minimize(light_path,
                           np.zeros(len(sqrt_epsilons)-1),
                           (incident_points, sqrt_epsilons, ))
            for i in range(len(sqrt_epsilons)):
                time_delay += np.linalg.norm(incident_points[i+1] - incident_points[i]) / SPEED_OF_LIGHT * sqrt_epsilons[i]
            return time_delay
        print(incident_points)
        print(sqrt_epsilons)
        exit()



    def save(self):
        # lock since the file may be read by other processes
        with FileLock(self.lock):
            # first, update the cache, since the file may be written during this instance's life
            if self.cache_path.exists():
                with open(self.cache_path, 'rb') as cache_file:
                    new_cache = pickle.load(cache_file)
                    self.cache.update(new_cache)
            #print(self.cache)
            # update the cache by pickle
            with open(self.cache_path, 'wb') as cache_file:
                pickle.dump(self.cache, cache_file)


def light_path(x, incident_points, sqrt_epsilons):
    for i in range(1, incident_points.shape[0] - 1):
        incident_points[i, 0] = x[i-1]
    ret = 0
    for i in range(incident_points.shape[0] - 1):
        ret += sqrt_epsilons[i] * np.linalg.norm(incident_points[i+1] - incident_points[i])
    return ret