import torch
import torch.nn as nn
import util

class VFLoss(nn.Module):
    def __init__(self, baseload_degree, baseload_factor, storage_degree, storage_factor, storage_threshold, epsilon):
        super().__init__()
        # Control severity of penalties
        self.baseload_degree = baseload_degree
        self.baseload_factor = baseload_factor
        self.storage_factor = storage_factor
        self.storage_degree = storage_degree
        # Controls threshold, below which the model is not penalized for its stored energy
        self.storage_threshold = storage_threshold
        # Prevents division by 0 in COVE computation
        self.epsilon = epsilon

    def forward(self, released, stored, power, price):
        B = power.shape[0]
        T = power.shape[1]
        power_avg = torch.mean(power)
        price_avg = torch.mean(price)
        assert B == price.shape[0]
        # Take batchwise loss
        brev = util.batchwise_revenue(released, price)
        cove = 1 / (torch.abs(brev) + self.epsilon)
        baseline_penalty = (self.baseload_factor * torch.maximum(released - power_avg, torch.zeros(B,T))) ** self.baseload_degree
        storage_penalty = (self.storage_factor * torch.maximum(stored - self.storage_threshold, torch.zeros(B,T))) ** self.storage_degree
        price_factor = torch.minimum(price / price_avg, torch.ones(B,T))
        # Average over batches
        loss = torch.mean(cove) + torch.mean(baseline_penalty) + torch.mean(storage_penalty * price_factor)
        return loss