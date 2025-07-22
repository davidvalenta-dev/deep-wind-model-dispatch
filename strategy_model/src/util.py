import numpy as np
import yaml
import matplotlib.pyplot as plt
import torch
import os
from model import VFNN, VFNN_2
import pandas as pd
from dataset import VFDataset, VF2Dataset
from torch.utils.data import Dataset, DataLoader

## CONSTANTS FOR CAPEX AND OPEX
STORAGE_TYPES = np.array(['battery-li', 'caes', 'hydro'])
# These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/lithium-ion-battery
BATTERY_LI_RATINGS = np.array([1, 10, 100, 1000])
BATTERY_LI_DURATIONS = np.array([2, 4, 6, 8, 10, 24, 100])
# CAPEX is indexed by [rating, duration]
BATTERY_LI_CAPEX = np.array([[1040.88, 1841.72, 2648.46, 3453.84, 4256.60, 9840.96, 39754.00],
                  [904.44, 1618.62, 2350.83, 3070.57, 3793.15, 8815.37, 35696.05],
                  [846.01, 1490.89, 2158.16, 2823.31, 3490.67, 8120.59, 32913.67],
                  [787.51, 1406.11, 2036.53, 2672.06, 3311.12, 7727.58, 29945.62]])
# OPEX is indexed by [rating, duration]
BATTERY_LI_OPEX = np.array([[3.17, 5.47, 6.98, 8.76, 10.59, 23.30, 90.47],
                 [2.79, 4.59, 6.37, 8.12, 9.87, 21.98, 85.98],
                 [2.56, 4.27, 5.96, 7.63, 9.33, 20.84, 81.82],
                 [2.37, 3.99, 5.63, 7.21, 8.79, 19.78, 77.88]])

# These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/compressed-air-energy-storage
CAES_RATINGS = np.array([100, 1000])
CAES_DURATIONS = np.array([4, 10, 24, 100])
CAES_CAPEX = np.array([[1090.24, 1125.33, 1207.53, 1637.13],
                       [992.93, 1025.37, 1101.30, 1497.66]])
CAES_OPEX = np.array([[17.02, 15.43, 14.88, 16.50],
                       [9.35, 9.18, 9.13, 9.28]])

# These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/pumped-storage-hydropower
HYDRO_RATINGS = np.array([100, 1000])
HYDRO_DURATIONS = np.array([4, 10, 24, 100])
HYDRO_CAPEX = np.array([[2703.26, 2786.84, 2950.29, 3415.97],
                        [2011.66, 2019.89, 2154.67, 3179.96]])
HYDRO_OPEX = np.array([[27.21, 27.21, 27.21, 27.21],
                        [14.62, 14.62, 14.62, 14.62]])

# indexed by storage type
RTE = np.array([0.83, 0.55, 0.80])
RATINGS = [BATTERY_LI_RATINGS, CAES_RATINGS, HYDRO_RATINGS]
DURATIONS = [BATTERY_LI_DURATIONS, CAES_DURATIONS, HYDRO_DURATIONS]
CAPEX = [BATTERY_LI_CAPEX, CAES_CAPEX, HYDRO_CAPEX]
OPEX = [BATTERY_LI_OPEX, CAES_OPEX, HYDRO_OPEX]

def get_rte(type):
    type_idx = np.where(STORAGE_TYPES == type)[0]
    return RTE[type_idx][0]

def get_storage_specs(type, rating, duration):
    type_idx = np.where(STORAGE_TYPES == type)[0][0]
    rating_idx = np.where(RATINGS[type_idx] == rating)[0]
    duration_idx = np.where(DURATIONS[type_idx] == duration)[0]
    capex = CAPEX[type_idx][rating_idx, duration_idx]
    opex = OPEX[type_idx][rating_idx, duration_idx]
    rte = get_rte(type)
    return capex, opex, rte

## UTILS FOR VF CALCULATION

# These are useful for visualization purposes, the batchwise variants are useful for training
def cove(power, price, storage_type=None, storage_rating=None, storage_duration=None):
    cost = 1
    if storage_rating != None and storage_duration != None:
        capex, opex, rte = get_storage_specs(storage_type, storage_rating, storage_duration)
        cost = capex + opex
    return cost / revenue(power, price)

def revenue(power, price, range=()):
    if(len(power) != len(price)):
        print('Warning: price and power have different lengths')
    if(len(range) != 2):
        # default range to entire range of power/price
        range = (0, len(power)-1)
    return np.sum(power[range[0]:range[1]] * price[range[0]:range[1]], axis=0)

def value_factor(power, price, range=()):
    if(len(power) != len(price)):
        print('Warning: price and power have different lengths')
    if(len(range) != 2):
        # default range to entire range of power/price
        range = (0, len(power)-1)
    P_wind = revenue(power, price, range) / np.sum(power[range[0]:range[1]], axis=0)
    P_avg = np.mean(price[range[0]:range[1]], axis=0)
    return P_wind / P_avg

def batchwise_revenue(batch_power, batch_price):
    prod = batch_power * batch_price
    return torch.sum(prod, dim=1) # axis 0 is batch, axis 1 is time

def batchwise_value_factor(batch_power, batch_price):
    rev =  batchwise_revenue(batch_power, batch_price)
    P_wind = rev / torch.sum(batch_power, dim=1)
    P_avg = torch.mean(batch_price, dim=1)
    return P_wind / P_avg

def batchwise_cove(batch_power, batch_price, epsilon, storage_type=None, storage_rating=None, storage_duration=None):
    #if rating and duration not give, use idealized COVE with no cost in the numerator
    cost = 1
    #otherwise, compute costs
    if storage_rating != None and storage_duration != None:
        capex, opex, rte = get_storage_specs(storage_type, storage_rating, storage_duration)
        cost = capex.squeeze() + opex.squeeze()
        
    brev = batchwise_revenue(batch_power, batch_price)
    epsilon_tensor = torch.full_like(brev, epsilon)
    cost_tensor = torch.full_like(brev, cost)
    bcove = cost_tensor / (brev + epsilon_tensor)
    return bcove

## MISC. UTILS 
def normalize_price(prices, config):
    threshold = config['price_threshold']
    #Cap prices
    cap_idxs = prices > threshold
    prices[cap_idxs] = threshold
    #Normalize
    prices /= np.max(prices)
    return prices

def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def save_config(config, file_path):
    with open(file_path, 'w') as file:
        yaml.dump(config, file, default_flow_style=False, sort_keys=False)

def load_model(model_path, config_path, with_loads=False):
    if with_loads:
        return load_model_with_loads(model_path, config_path)
    config = load_config(config_path)
    model = VFNN(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])
    model.load_state_dict(torch.load(model_path, weights_only=True))
    return model

def load_model_with_loads(model_path, config_path):
    config = load_config(config_path)
    model = VFNN_2(config['hidden_size'], 
                   config['num_hidden'], 
                   config['fc_hidden_sizes'], 
                   config['rated_capacity'],
                   config['storage_rating'],
                   config['storage_duration'])
    model.load_state_dict(torch.load(model_path, weights_only=True))
    return model

def load_dataset_no_split(csv_path, config, with_loads=False, cf=True):
    if with_loads:
        return load_dataset_no_split_with_loads(csv_path, config, cf=cf)
    
    df = pd.read_csv(csv_path)
    power = df['power_generated']
    if(cf):
        power = power * config['rated_capacity']
    prices = df['lmp']
    prices = normalize_price(prices, config)

    # Format as torch tensor
    power_tensor = torch.tensor(power, dtype=torch.float)
    prices_tensor = torch.tensor(prices, dtype=torch.float)
    assert power_tensor.shape[0] == prices_tensor.shape[0]
    data_tensor = torch.concat([power_tensor.unsqueeze(-1), prices_tensor.unsqueeze(-1)], dim=-1)

    return data_tensor


def load_dataset_no_split_with_loads(csv_path, config, cf=True):
    df = pd.read_csv(csv_path)
    power = df['power_generated']
    if(cf):
        power = power * config['rated_capacity']
    prices = df['lmp']
    prices = normalize_price(prices, config)
    loads = df['user_load_zonal']
    loads /= np.max(loads)

    # Format as torch tensor
    power_tensor = torch.tensor(power, dtype=torch.float)
    prices_tensor = torch.tensor(prices, dtype=torch.float)
    loads_tensor = torch.tensor(loads, dtype=torch.float)

    assert power_tensor.shape[0] == prices_tensor.shape[0] and power_tensor.shape[0] == loads_tensor.shape[0]
    data_tensor = torch.concat([power_tensor.unsqueeze(-1), prices_tensor.unsqueeze(-1), loads_tensor.unsqueeze(-1)], dim=-1)

    return data_tensor

def load_dataset(csv_path, config, with_loads=False):
    if with_loads:
        return load_dataset_with_loads(csv_path, config)
    
    df = pd.read_csv(csv_path)
    power = df['power_generated']
    prices = df['lmp']
    prices = normalize_price(prices, config)

    # Chunk data into sequences of length config['seq_length']
    seq_length = config['seq_length']
    split_idxs = np.arange(0, len(power), seq_length)
    # Drop edges to avoid inhomogeneity in subarray length after split
    split_power = np.array(np.split(power, split_idxs)[1:-1])
    split_prices = np.array(np.split(prices, split_idxs)[1:-1])

    # Format as torch tensor
    power_tensor = torch.tensor(split_power, dtype=torch.float)
    prices_tensor = torch.tensor(split_prices, dtype=torch.float)
    assert power_tensor.shape[0] == prices_tensor.shape[0]
    data_tensor = torch.concat([power_tensor.unsqueeze(-1), prices_tensor.unsqueeze(-1)], dim=-1)

    len_data = data_tensor.shape[0]
    train_frac, val_frac = config['train_percent'], config['val_percent']
    train_size = int(train_frac * len_data)
    val_size = int(val_frac * len_data)

    torch.manual_seed(0)
    indices = torch.randperm(len_data)

    train_indices = indices[:train_size]
    val_indices = indices[train_size:train_size + val_size]
    test_indices = indices[train_size + val_size:]

    assert set(train_indices).isdisjoint(set(val_indices)) and set(train_indices).isdisjoint(set(test_indices)) and set(val_indices).isdisjoint(set(test_indices))

    # Index tensors to get non-overlapping splits
    train = data_tensor[train_indices]
    val = data_tensor[val_indices]
    test = data_tensor[test_indices]

    batch_size = config['batch_size']

    train_dataset = VFDataset(train)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_dataset = VFDataset(val)
    val_dataloader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    test_dataset = VFDataset(test)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_dataloader, val_dataloader, test_dataloader

def load_dataset_with_loads(csv_path, config):    
    df = pd.read_csv(csv_path)
    power = df['power_generated']
    prices = df['lmp']
    prices = normalize_price(prices, config)

    loads = df['user_load_zonal']
    # Normalize loads
    loads /= np.max(loads)

    # Chunk data into sequences of length config['seq_length']
    seq_length = config['seq_length']
    split_idxs = np.arange(0, len(power), seq_length)
    # Drop edges to avoid inhomogeneity in subarray length after split
    split_power = np.array(np.split(power, split_idxs)[1:-1])
    split_prices = np.array(np.split(prices, split_idxs)[1:-1])
    split_loads = np.array(np.split(loads, split_idxs)[1:-1])

    # Format as torch tensor
    power_tensor = torch.tensor(split_power, dtype=torch.float)
    prices_tensor = torch.tensor(split_prices, dtype=torch.float)
    loads_tensor = torch.tensor(split_loads, dtype=torch.float)
    assert power_tensor.shape[0] == prices_tensor.shape[0] and power_tensor.shape[0] == loads_tensor.shape[0]
    data_tensor = torch.concat([power_tensor.unsqueeze(-1), prices_tensor.unsqueeze(-1), loads_tensor.unsqueeze(-1)], dim=-1)
    len_data = data_tensor.shape[0]
    train_frac, val_frac = config['train_percent'], config['val_percent']
    train_size = int(train_frac * len_data)
    val_size = int(val_frac * len_data)

    torch.manual_seed(0)
    indices = torch.randperm(len_data)

    train_indices = indices[:train_size]
    val_indices = indices[train_size:train_size + val_size]
    test_indices = indices[train_size + val_size:]

    assert set(train_indices).isdisjoint(set(val_indices)) and set(train_indices).isdisjoint(set(test_indices)) and set(val_indices).isdisjoint(set(test_indices))

    # Index tensors to get non-overlapping splits
    train = data_tensor[train_indices]
    val = data_tensor[val_indices]
    test = data_tensor[test_indices]

    batch_size = config['batch_size']

    train_dataset = VF2Dataset(train)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_dataset = VF2Dataset(val)
    val_dataloader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    test_dataset = VF2Dataset(test)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_dataloader, val_dataloader, test_dataloader

# Returns config, model, and dataset (without split) for use with model evaluation
def load_experiment(folder_name, dataset_path, with_loads=False, cf=True):
    dir = f'../test/{folder_name}'
    config_path = f'{dir}/config_{folder_name}.yaml'
    model_path = f'{dir}/model_{folder_name}.pth'
    config = load_config(config_path)
    model = load_model(model_path, config_path, with_loads=with_loads)
    dataset = load_dataset_no_split(dataset_path, config, with_loads=with_loads, cf=cf)
    return model, dataset, config

def plot_losses(train_losses, val_losses, fname):
    # Drop first train epoch, usually ~100x greater than others
    train_losses = train_losses[1:]
    val_losses = val_losses[1:]

    epochs = np.arange(1, len(train_losses) + 1)
    plt.close('all')

    # Plotting training and validation losses
    plt.plot(epochs, train_losses, label='Training Loss')
    plt.plot(epochs, val_losses, label='Validation Loss')
    plt.legend()
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Loss per Epoch')

    # Saving the plot as an image file in 'plots' directory
    plt.savefig(fname + ".png")

def format_num(num):
    if num < 10:
        return f'00{num}'
    elif num < 100:
        return f'0{num}'
    else:
        return f'{num}'