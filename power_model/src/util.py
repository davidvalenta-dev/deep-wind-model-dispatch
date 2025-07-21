import numpy as np
import yaml
import matplotlib.pyplot as plt
import torch
import os
from model import NQF_RNN, NQF_RNN_AR
import pandas as pd
from dataset import WindDataset
from torch.utils.data import DataLoader

def random_quantiles(size, low, high):
    return np.random.uniform(low=low, high=high, size=size)

## MISC. UTILS 
def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_model(model_path, config_path, use_autoregressive=False):
    config = load_config(config_path)
    if use_autoregressive:
        model = NQF_RNN_AR(config['hidden_size'], config['num_hidden'], config['nqf_hidden_sizes'])
    else:
        model = NQF_RNN(config['hidden_size'], config['num_hidden'], config['nqf_hidden_sizes'])
    model.load_state_dict(torch.load(model_path))
    return model

def load_dataset_no_split(csv_path):
    df = pd.read_csv(csv_path)
    speed = torch.tensor(df['speed_HRRR'], dtype=torch.float)
    power = torch.tensor(df['ercot_power'], dtype=torch.float)

    # Normalize power
    power /= torch.max(power)

    # # Shift to account for time zone difference
    # speed = speed[6:]
    # power = power[:-6]

    return speed, power

def load_dataset(csv_path, config):
    df = pd.read_csv(csv_path)
    speed = df['speed_HRRR']
    power = df['ercot_power']

    # Normalize power
    power /= np.max(power)

    # # Shift to account for time zone difference
    # speed = speed[6:]
    # power = power[:-6]

    # Chunk data into sequences of length config['seq_length']
    seq_length = config['seq_length']
    split_idxs = np.arange(0, len(power), seq_length)
    # Drop edges to avoid inhomogeneity in subarray length after split
    split_power = np.array(np.split(power, split_idxs)[1:-1])
    split_speed = np.array(np.split(speed, split_idxs)[1:-1])

    # Format as torch tensor
    power_tensor = torch.tensor(split_power, dtype=torch.float)
    speed_tensor = torch.tensor(split_speed, dtype=torch.float)
    assert power_tensor.shape[0] == speed_tensor.shape[0]

    len_data = speed_tensor.shape[0]
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
    X_train, y_train = speed_tensor[train_indices], power_tensor[train_indices]
    X_val, y_val = speed_tensor[val_indices], power_tensor[val_indices]
    X_test, y_test = speed_tensor[test_indices], power_tensor[test_indices]

    batch_size = config['batch_size']

    train_dataset = WindDataset(X_train, y_train)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_dataset = WindDataset(X_val, y_val)
    val_dataloader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    test_dataset = WindDataset(X_test, y_test)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_dataloader, val_dataloader, test_dataloader

# Returns config, model, and dataset (without split) for use with model evaluation
def load_experiment(folder_name, dataset_path, use_autoregressive=False):
    dir = f'../test/{folder_name}'
    config_path = f'{dir}/config_{folder_name}.yaml'
    model_path = f'{dir}/model_{folder_name}.pth'
    config = load_config(config_path)
    model = load_model(model_path, config_path, use_autoregressive)
    dataset = load_dataset_no_split(dataset_path)
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