import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def base_load(power):
    avg = np.mean(power)
    stored = 0
    released = np.zeros(shape=(len(power)))
    stored_ts = np.zeros(shape=(len(power)))
    for i in range(len(power)):
        stored_ts[i] = stored
        g = power[i]
        if g == avg:
            released[i] = avg
        elif g > avg:
            stored += g - avg
            released[i] = avg
        else:
            margin = min(avg - g, stored)
            stored -= margin
            released[i] = margin + g
    return released, stored_ts

def base_load_modified(power, price):
    g_avg = np.mean(power)
    print(g_avg)
    p_avg = np.mean(price)
    stored = 0
    released = np.zeros(shape=(len(power)))
    for i in range(len(power)):
        g = power[i]
        p = price[i]
        ## Standard base load
        if g == g_avg:
            released[i] = g_avg
        elif g > g_avg:
            stored += g - g_avg
            released[i] = g_avg
        else:
            margin = min(g_avg - g, stored)
            stored -= margin
            released[i] = margin + g
        ## Custom price-based method
        if p > p_avg:
            factor = p / p_avg
            goal = g_avg * (factor - 1)
            available = min(goal, stored)
            released[i] += available
            stored -= available
    return released
    