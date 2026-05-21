import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def baseload(power, battery_rating, battery_capacity, rte, account_for_rte=True):
    avg = np.mean(power)
    stored = 0
    released = np.zeros(shape=(len(power)))
    stored_ts = np.zeros(shape=(len(power)))
    direct_gens = np.zeros(shape=(len(power)))
    regens = np.zeros(shape=(len(power)))
    # Includes curtailment during charging due to rating and capacity
    # Also includes losses to RTE during discharging
    losses = np.zeros(shape=(len(power)))
    for i in range(len(power)):
        stored_ts[i] = stored
        g = power[i]
        direct_gens[i] = 0
        regens[i] = 0
        # If g == avg, don't store anything, just directly release
        if g == avg:
            released[i] = g
            direct_gens[i] = g
        # If g > avg, store g - avg, release g
        elif g > avg:
            margin = g - avg
            released[i] = g - margin
            direct_gens[i] = g - margin
            if margin > battery_rating:
                losses[i] += margin - battery_rating
            charge = min(margin, battery_rating)
            stored += charge
        # If g < avg, try to release enough stored energy to release avg total
        else:
            diff = avg - g
            if account_for_rte:
                diff *= (1 / rte)
            margin = min(diff, stored)
            discharge = min(margin, battery_rating)
            stored -= discharge
            losses[i] += discharge * (1 - rte)
            released[i] = g + (discharge * rte)
            regens[i] = discharge * rte
        if stored > battery_capacity:
            losses[i] += stored - battery_capacity
        stored = min(stored, battery_capacity)
    return released, stored_ts, losses, direct_gens, regens

def baseload_ideal(power):
    avg = np.mean(power)
    stored = 0
    released = np.zeros(shape=(len(power)))
    stored_ts = np.zeros(shape=(len(power)))
    direct_gens = np.zeros(shape=(len(power)))
    regens = np.zeros(shape=(len(power)))
    for i in range(len(power)):
        stored_ts[i] = stored
        g = power[i]
        direct_gens[i] = 0
        regens[i] = 0
        # If g == avg, don't store anything, just directly release
        if g == avg:
            released[i] = g
            direct_gens[i] = g
        # If g > avg, store g - avg, release g
        elif g > avg:
            margin = g - avg
            released[i] = g - margin
            direct_gens[i] = g - margin
            stored += margin
        # If g < avg, try to release enough stored energy to release avg total
        else:
            diff = avg - g
            margin = min(diff, stored)
            stored -= margin
            released[i] = g + margin
            regens[i] = margin
    return released, stored_ts, direct_gens, regens