import torch
import util
from model import NQF_RNN, NQF_RNN_AR
from util import load_dataset
from train import train, validate

def main():
    config = util.load_config('./configs/config.yaml')
    train_loader, val_loader, test_loader = load_dataset(config['dataset_path'], config)
    # train_loader, val_loader, test_loader = load_dataset('../probabilistic/wevalidate_data/EIA_930.csv', config)

    # Test entry in data loader as sanity check
    (features, power) = train_loader.dataset[0]
    print(f'Feature shape: {features.shape}')
    print(f'Power shape: {power.shape}')
    print(f"Features: {', '.join(config['feature_names'])}")
    assert power.shape[0] == features.shape[0] and power.shape[0] == config['seq_length']

    # model = NQF_RNN(config['hidden_size'], config['num_hidden'], config['nqf_hidden_sizes'])
    model = NQF_RNN_AR(config['hidden_size'], config['num_hidden'], config['nqf_hidden_sizes'], input_size=config['input_size'])
    train(model, train_loader, val_loader, config)

    test_loss = validate(model, test_loader, config)
    print(f'Test Loss = {test_loss}')

if __name__ == '__main__':
    main()
