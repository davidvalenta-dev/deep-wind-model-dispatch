import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def baseload(power, battery_rating, battery_capacity, rte):
    avg = np.mean(power)
    stored = 0
    released = np.zeros(shape=(len(power)))
    stored_ts = np.zeros(shape=(len(power)))
    # Includes curtailment during charging due to rating and capacity
    # Also includes losses to RTE during discharging
    losses = np.zeros(shape=(len(power)))
    for i in range(len(power)):
        stored_ts[i] = stored
        g = power[i]
        # If g == avg, don't store anything, just directly release
        if g == avg:
            released[i] = g
        # If g > avg, store g - avg, release g
        elif g > avg:
            margin = g - avg
            released[i] = g - margin
            if margin > battery_rating:
                losses[i] += margin - battery_rating
            charge = min(margin, battery_rating)
            stored += charge
        # If g < avg, try to release enough stored energy to release avg total
        else:
            margin = min(avg - g, stored)
            discharge = min(margin, battery_rating)
            stored -= discharge
            losses[i] += discharge * (1 - rte)
            released[i] = g + (discharge * rte)
        if stored > battery_capacity:
            losses[i] += stored - battery_capacity
        stored = min(stored, battery_capacity)
    return released, stored_ts, losses