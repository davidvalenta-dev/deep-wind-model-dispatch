import torch
import util
from model import VFNN
from util import load_dataset
from train import train, validate

def main():
    config = util.load_config('./configs/config.yaml')
    train_loader, val_loader, test_loader = load_dataset('../data/processed/dataset_2018-21_clean.csv', config)

    # Test entry in data loader as sanity check
    (data, power, price) = train_loader.dataset[0]
    print(f'Power shape: {power.shape}')
    print(f'Price shape: {price.shape}')
    assert power.shape[0] == price.shape[0] and power.shape[0] == config['seq_length']

    model = VFNN(config['hidden_size'], config['num_hidden'], config['fc_hidden_sizes'])
    train(model, train_loader, val_loader, config)
    
    test_loss = validate(model, test_loader, config)
    print(f'Test Loss = {test_loss}')

if __name__ == '__main__':
    main()