import numpy as np
import os
import yaml
from util import batchwise_cove, load_config, save_config
import torch

def validate_performance(model, dataloader, config, device, run_dir):
    print('Validating model performance for hyperparameter search')
    #Assumes that hp_dir contains a .yaml file containing the minimum COVE and associated run index
    hp_dir = os.path.join(run_dir, '..')
    run_num = run_dir[-3:]
    results_path = os.path.join(hp_dir, 'results.yaml')
    results = load_config(results_path)
    min_cove = results['min_cove']
    target_length = config['hp_comparison_length']
    (input, power, price) = get_validation_inputs(target_length, dataloader, device)

    pred = model(input)
    released = pred[:,:,0]
    
    bcove = batchwise_cove(released, price, config['epsilon'], config['storage_type'], config['storage_rating'], config['storage_duration'], config['rated_capacity'])
    cove = float(torch.mean(bcove).detach().cpu().numpy())
    run_results = {'cove': cove, 'run': run_num}
    run_results_path = os.path.join(run_dir, 'results.yaml')
    save_config(run_results, run_results_path)
    if cove < min_cove or min_cove == -1:
        # Save new best run
        results['min_cove'] = cove
        results['best_run'] = run_num
        print('New best run, updating results')
        save_config(results, results_path)
        return True
    # Did not beat best model
    print('Run did not beat best model')
    return False

def get_validation_inputs(target_length, dataloader, device, max_coverage=True):
    # Gather samples from dataloader until target_length reached
    # util is configured s.t. val and test dataloaders are not shuffled, so we can simply enumerate until
    # we reach the desired length
    num_iter = 1
    if max_coverage:
        N = len(dataloader.dataset)
        T = 168 # dataloader.dataset[0][0][1].shape[1]
        print(f"N: {N}")
        print(f"T: {T}")
        num_iter = int(np.floor((N * T) / target_length))
        print(f'Num iterations for stacking: {num_iter}')
        print(f'Dataloader: {len(dataloader.dataset)}')
    stacked_input = None
    stacked_power = None
    stacked_price = None
    for j in range(num_iter):
        val_input = None
        val_power = None
        val_price = None
        for i, (input, power, price) in enumerate(dataloader):
            if val_input == None:
                val_input = input
                val_power = power
                val_price = price
            else:
                try:
                    val_input = torch.cat([val_input, input], dim=1)
                    val_power = torch.cat([val_power, power], dim=1)
                    val_price = torch.cat([val_price, price], dim=1)
                except:
                    # Concat fails if shape mismatch, at this point end
                    break
                if val_input.shape[1] >= target_length:
                    break
        if stacked_input == None:
            stacked_input = val_input
            stacked_power = val_power
            stacked_price = val_price
        else:
            stacked_input = torch.cat([stacked_input, val_input], dim=0)
            stacked_power = torch.cat([stacked_power, val_power], dim=0)
            stacked_price = torch.cat([stacked_price, val_price], dim=0)
    input = stacked_input.to(device)
    power = stacked_power.to(device)
    price = stacked_price.to(device)
    return (input, power, price)
    
def create_config(hp_config, base_config, save_dir):
    config = base_config
    for key in hp_config:
        val = hp_config[key]
        # Sample from rand(lower, upper)
        if len(val) == 1 and 'rand' in val[0]:
            lower = float(val[0].split(',')[0].strip()[5:])
            upper = float(val[0].split(',')[1].strip()[:-1])
            sample = np.random.uniform(lower, upper)
        # Sample one element uniformly randomly
        else:
            idx = int(np.round(np.random.uniform(0, len(val) - 1)))
            sample = val[idx]
        # Replace value in config with sample
        config[key] = sample
    config_path = os.path.join(save_dir, 'config.yaml')
    save_config(config, config_path)
    return config