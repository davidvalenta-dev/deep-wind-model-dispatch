import torch
import util
from model import VFNN, VFNN_2
from util import load_dataset
from train import train, validate

def main():
    config = util.load_config('./configs/config.yaml')
    train_loader, val_loader, test_loader = load_dataset('../../data/processed/dataset_2018-21_withloads.csv', config, with_loads=True)

    # Test entry in data loader as sanity check
    (data, power, price) = train_loader.dataset[0]
    print(f'Power shape: {power.shape}')
    print(f'Price shape: {price.shape}')
    assert power.shape[0] == price.shape[0] and power.shape[0] == config['seq_length']

    # model = VFNN(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])

    # VFNN_2 uses load data as well, otherwise the same as VFNN
    model = VFNN_2(config['hidden_size'], 
                   config['num_hidden'], 
                   config['fc_hidden_sizes'], 
                   config['rated_capacity'],
                   config['battery_rating'], 
                   config['battery_duration'])
    
    train(model, train_loader, val_loader, config)
    
    test_loss = validate(model, test_loader, config)[0]
    print(f'Test Loss = {test_loss}')

if __name__ == '__main__':
    main()