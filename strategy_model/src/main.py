import torch
import util
from model import VFNN, VFNN_2
from util import load_dataset, format_num, save_config
from train import train, validate
from hp_search import create_config
import argparse
import os
import uuid
import yaml

def main():
    parser = argparse.ArgumentParser(description="Trainer for COVE-NN")
    parser.add_argument("--hp_search", help="Search hyperparameter space", action="store_true")
    parser.add_argument('--verbose', help="Print losses during training", action="store_true")
    args = parser.parse_args()
    
    if args.hp_search:
        base_config = util.load_config('./configs/config.yaml')
        hp_search_config = util.load_config('./configs/hp_search_config.yaml')
        hp_dir = os.path.join('../hp_search_results', f"{uuid.uuid4()}/")
        os.mkdir(hp_dir)
        # Initialize results yaml
        results = {'min_cove': -1, 'best_run': -1}
        results_path = os.path.join(hp_dir, 'results.yaml')
        save_config(results, results_path)
        # Run hp search
        num_runs = base_config['hp_runs']
        for i in range(num_runs):
            run_dir = os.path.join(hp_dir, f'run_{format_num(i)}')
            os.mkdir(run_dir)
            print(f'Hyperparameter search: running model {i}')
            print(f'Saving run to {run_dir}')
            config = create_config(hp_search_config, base_config, run_dir)
            run_train(config, args.verbose, hp_search=True, save_dir=run_dir)
        return
    
    config = util.load_config('./configs/config.yaml')
    run_train(config, args.verbose)

def run_train(config, verbose, hp_search=False, save_dir=None):
    train_loader, val_loader, test_loader = load_dataset('../../data/processed/dataset_1980-2023_withloads.csv', config, with_loads=True)
    # Test entry in data loader as sanity check
    (data, power, price) = train_loader.dataset[0]
    if(verbose):
        print(f'Training examples: {len(train_loader.dataset)}')
        print(f'Power shape: {power.shape}')
        print(f'Price shape: {price.shape}')
    assert power.shape[0] == price.shape[0] and power.shape[0] == config['seq_length']

    # model = VFNN(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])

    # VFNN_2 uses load data as well, otherwise the same as VFNN
    model = VFNN_2(config['hidden_size'], 
                   config['num_hidden'], 
                   config['fc_hidden_sizes'], 
                   config['rated_capacity'],
                   config['storage_type'],
                   config['storage_rating'], 
                   config['storage_duration'],
                   config['num_modules'])
    
    train(model, train_loader, val_loader, config, verbose, hp_search, save_dir)
    
    test_loss = validate(model, test_loader, config)[0]
    if(verbose):
        print(f'Test Loss = {test_loss}')

if __name__ == '__main__':
    main()