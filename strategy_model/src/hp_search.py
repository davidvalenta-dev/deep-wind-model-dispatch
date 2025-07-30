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
    
    bcove = batchwise_cove(released, price, config['epsilon'], config['storage_type'], config['storage_rating'], config['storage_duration'])
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

def get_validation_inputs(target_length, dataloader, device):
    # Gather samples from dataloader until target_length reached
    # util is configured s.t. val and test dataloaders are not shuffled, so we can simply enumerate until
    # we reach the desired length
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
    input = val_input.to(device)
    power = val_power.to(device)
    price = val_price.to(device)
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