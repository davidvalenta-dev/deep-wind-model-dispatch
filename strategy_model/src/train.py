import torch
import numpy as np
import uuid
import csv
import os
from loss import VFLoss
from util import plot_losses
from hp_search import validate_performance
import shutil

def train(model, train_dataloader, val_dataloader, config, verbose, hp_searching=False, save_dir=None):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    criterion = VFLoss(config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config['learning_rate'])
    early_stopper = EarlyStopper(config['patience'], config['early_stop_epoch'])
    
    unique_code_str = uuid.uuid4()
    
    if save_dir == None:
        models_folder = '../test/'
        model_folder = models_folder+f"{unique_code_str}/"
        try:
            os.mkdir(model_folder)
            if(verbose):
                print(f"Folder '{model_folder}' created successfully.")
        except FileExistsError:
            if(verbose):
                print(f"Folder '{model_folder}' already exists.")
        except Exception as e:
            print(f"An error occurred: {e}")

        shutil.copyfile('./configs/config.yaml', model_folder+f"config_{unique_code_str}.yaml")
    
    else:
        model_folder = save_dir + '/'
    min_val_loss = float("inf")
    train_loss = []
    val_loss = []

    hp_search_cutoff_epoch = -1
    if hp_searching:
        hp_search_cutoff_epoch = config['hp_search_cutoff_epoch']

    for t in range(config['epochs']):
        epoch_train_loss = []
        for i, (input, power, price) in enumerate(train_dataloader):
            optimizer.zero_grad()

            input = input.to(device)
            power = power.to(device)
            price = price.to(device)

            pred = model(input)
            released = pred[:,:,0]
            stored = pred[:,:,1]

            loss = criterion(released, stored, power, price)

            epoch_train_loss.append(loss.detach().cpu().numpy())
            if verbose and i % 10 == 0:
                print(f'Batch {i} loss: {loss.detach().cpu().numpy()}')
            
            loss.backward()
            optimizer.step()
        # Steps forward adaptive loss term
        criterion.step()
        avg_train_loss = np.mean(epoch_train_loss)
        avg_val_loss, avg_release = validate(model, val_dataloader, config)

        # Save best model checkpoint
        if(avg_val_loss < min_val_loss):
            min_val_loss = avg_val_loss
            torch.save(model.state_dict(), model_folder+f"model_{unique_code_str}.pth")
        
        # Early stopping logic
        if(early_stopper.early_stop(avg_val_loss, t)):
            save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str, verbose)
            return
        
        if verbose:
            print(f"Epoch {t}:")
            print(f"Avg Training Loss: {avg_train_loss}")
            print(f"Validation Loss: {avg_val_loss}")
            print(f"Average Release: {avg_release}")

        train_loss.append(avg_train_loss)
        val_loss.append(avg_val_loss)

        if t == hp_search_cutoff_epoch:
            continue_run = validate_performance(model, val_dataloader, config, device, save_dir)
            if not continue_run:
                save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str, verbose)
                return
            
    # Training finished, save metrics
    save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str, verbose)

def validate(model, dataloader, config):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    criterion = VFLoss(config)
    val_loss = []
    releases = []

    for i, (input, power, price) in enumerate(dataloader):
        input = input.to(device)
        power = power.to(device)
        price = price.to(device)

        pred = model(input)
        released = pred[:,:,0]
        stored = pred[:,:,1]
        loss = criterion(released, stored, power, price)

        val_loss.append(loss.detach().cpu().numpy())
        releases.append(torch.mean(released).detach().cpu().numpy())
    return np.mean(val_loss), np.mean(releases)

def save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str, verbose):
    plot_losses(train_loss, val_loss, model_folder+f"hidden{config['hidden_size']}_seqlen{config['seq_length']}_{unique_code_str}")
    csv_filename = model_folder + f"hidden{config['hidden_size']}_seqlen{config['seq_length']}_{unique_code_str}.csv"
    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "val_loss"])
        for epoch_idx in range(len(train_loss)):
            writer.writerow([epoch_idx, train_loss[epoch_idx], val_loss[epoch_idx]])
    if verbose:
        print("CSV file saved")
  
class EarlyStopper():
    def __init__(self, patience, early_stop_epoch):
        self.min_val_loss = float("inf")
        self.patience = patience
        self.early_stop_epoch = early_stop_epoch
        self.increasing_loss_count = 0
    def early_stop(self, val_loss, epoch):
        if(val_loss < self.min_val_loss):
            self.min_val_loss = val_loss
            self.increasing_loss_count = 0
        elif(epoch >= self.early_stop_epoch):
            self.increasing_loss_count += 1
            if(self.increasing_loss_count > self.patience):
                return True
        return False