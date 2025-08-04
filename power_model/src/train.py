import torch
import numpy as np
import uuid
import csv
import os
from loss import CRPSLoss
from util import plot_losses
import shutil

def train(model, train_dataloader, val_dataloader, config):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    criterion = CRPSLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config['learning_rate'])
    early_stopper = EarlyStopper(config['patience'], config['early_stop_epoch'])

    # Training hyperparameters
    B = config['batch_size']
    T = config['seq_length']
    quantile_levels = torch.tensor(config['quantile_levels'])

    unique_code_str = uuid.uuid4()

    models_folder = '../test/'
    model_folder = models_folder+f"{unique_code_str}/"
    try:
        os.mkdir(model_folder)
        print(f"Folder '{model_folder}' created successfully.")
    except FileExistsError:
        print(f"Folder '{model_folder}' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")

    shutil.copyfile('./configs/config.yaml', model_folder+f"config_{unique_code_str}.yaml")
    min_val_loss = float("inf")
    train_loss = []
    val_loss = []
    for t in range(config['epochs']):
        model.train()
        epoch_train_loss = []
        for i, (speed, power) in enumerate(train_dataloader):
            current_batch_size = speed.shape[0]
            optimizer.zero_grad()

            speed = speed.to(device)
            power = power.to(device)

            quantile_preds = torch.empty(size=(current_batch_size, T, len(quantile_levels)), device=device)
            for m in range(len(quantile_levels)):
                quantile_lvl = quantile_levels[m].repeat(T)
                pred = model(speed, quantile_lvl, targets=power)
                quantile_preds[:,:,m] = pred.squeeze()

            loss = criterion(quantile_levels, quantile_preds, power)

            epoch_train_loss.append(loss.detach().cpu().numpy())
            if i % 10 == 0:
                print(f'Batch {i} loss: {loss.detach().cpu().numpy()}')

            loss.backward()
            optimizer.step()
        avg_train_loss = np.mean(epoch_train_loss)
        
        model.eval()
        avg_val_loss = validate(model, val_dataloader, config)

        # Save best model checkpoint
        if(avg_val_loss < min_val_loss):
            min_val_loss = avg_val_loss
            torch.save(model.state_dict(), model_folder+f"model_{unique_code_str}.pth")
        
        # Early stopping logic
        if(early_stopper.early_stop(avg_val_loss, t)):
            save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str)
            return
        
        print(f"Epoch {t}:")
        print(f"Avg Training Loss: {avg_train_loss}")
        print(f"Validation Loss: {avg_val_loss}")

        train_loss.append(avg_train_loss)
        val_loss.append(avg_val_loss)

    # Training finished, save metrics
    save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str)

def validate(model, dataloader, config):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    criterion = CRPSLoss()

    val_loss = []

    quantile_levels = torch.tensor(config['quantile_levels'])
    B = config['batch_size']
    T = config['seq_length']

    for i, (speed, power) in enumerate(dataloader):
        current_batch_size = speed.shape[0]
        speed = speed.to(device)
        power = power.to(device)

        quantile_preds = torch.empty(size=(current_batch_size, T, len(quantile_levels)), device=device)
        for m in range(len(quantile_levels)):
            quantile_lvl = quantile_levels[m].repeat(T)
            pred = model(speed, quantile_lvl)
            quantile_preds[:,:,m] = pred.squeeze()
        loss = criterion(quantile_levels, quantile_preds, power)
        val_loss.append(loss.detach().cpu().numpy())

    if len(val_loss) == 0:
        print("Warning: No validation batches processed")
        return float('inf')
    
    return np.mean(val_loss)

def save_train_metrics(train_loss, val_loss, model_folder, config, unique_code_str):
    plot_losses(train_loss, val_loss, model_folder+f"hidden{config['hidden_size']}_seqlen{config['seq_length']}_{unique_code_str}")
    csv_filename = model_folder + f"hidden{config['hidden_size']}_seqlen{config['seq_length']}_{unique_code_str}.csv"
    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "val_loss"])
        for epoch_idx in range(len(train_loss)):
            writer.writerow([epoch_idx, train_loss[epoch_idx], val_loss[epoch_idx]])
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