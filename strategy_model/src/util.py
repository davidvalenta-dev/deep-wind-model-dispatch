import numpy as np
import yaml
import matplotlib.pyplot as plt
import torch
import os
from model import VFNN, VFNN_2
import pandas as pd
from dataset import VFDataset, VF2Dataset
from torch.utils.data import Dataset, DataLoader

## UTILS FOR VF CALCULATION

# These are useful for visualization purposes, the batchwise variants are useful for training
def cove(power, price, range=()):
    return 1 / revenue(power, price, range)

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

def load_model(model_path, config_path, with_loads=False):
    if with_loads:
        return load_model_with_loads(model_path, config_path)
    config = load_config(config_path)
    model = VFNN(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])
    model.load_state_dict(torch.load(model_path, weights_only=True))
    return model

def load_model_with_loads(model_path, config_path):
    config = load_config(config_path)
    model = VFNN_2(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])
    model.load_state_dict(torch.load(model_path, weights_only=True))
    return model

def load_dataset_no_split(csv_path, config, with_loads=False):
    if with_loads:
        return load_dataset_no_split_with_loads(csv_path, config)
    
    df = pd.read_csv(csv_path)
    cf = df['power_cf']
    # Keeping normalized for now, it seems like anything else causes numerical instability
    power = cf #* config['rated_capacity']
    prices = df['lmp']
    prices = normalize_price(prices, config)

    # Format as torch tensor
    power_tensor = torch.tensor(power, dtype=torch.float)
    prices_tensor = torch.tensor(prices, dtype=torch.float)
    assert power_tensor.shape[0] == prices_tensor.shape[0]
    data_tensor = torch.concat([power_tensor.unsqueeze(-1), prices_tensor.unsqueeze(-1)], dim=-1)

    return data_tensor


def load_dataset_no_split_with_loads(csv_path, config):
    df = pd.read_csv(csv_path)
    cf = df['power_cf']
    # Keeping normalized for now, it seems like anything else causes numerical instability
    power = cf #* config['rated_capacity']
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
    cf = df['power_cf']
    # Keeping normalized for now, it seems like anything else causes numerical instability
    power = cf #* config['rated_capacity']
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
    cf = df['power_cf']
    # Keeping normalized for now, it seems like anything else causes numerical instability
    power = cf #* config['rated_capacity']
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
def load_experiment(folder_name, dataset_path, with_loads=False):
    dir = f'../test/{folder_name}'
    config_path = f'{dir}/config_{folder_name}.yaml'
    model_path = f'{dir}/model_{folder_name}.pth'
    config = load_config(config_path)
    model = load_model(model_path, config_path, with_loads=with_loads)
    dataset = load_dataset_no_split(dataset_path, config, with_loads=with_loads)
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