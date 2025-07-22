import torch
import torch.nn as nn
import util

class VFLoss(nn.Module):
    def __init__(self, config):
        super().__init__()
        # Control severity of penalties
        self.baseload_degree = config['baseload_degree']
        self.baseload_factor =  config['baseload_factor']
        self.storage_factor =  config['storage_factor']
        self.storage_degree =  config['storage_degree']
        self.price_factor =  config['price_factor']
        self.price_degree =  config['price_degree']
        # Controls threshold, below which the model is not penalized for its stored energy
        self.storage_threshold =  config['storage_threshold']
        # Prevents division by 0 in COVE computation
        self.epsilon =  config['epsilon']
        # For adaptive term
        self.adaptive_degree =  config['adaptive_degree']
        self.adaptive_factor = config['adaptive_factor']
        self.adaptive_epoch = config['adaptive_epoch']
        self.epoch = 0
    
    def step(self):
        self.epoch += 1

    def forward(self, released, stored, power, price, storage_rating=None, storage_duration=None):
        B = power.shape[0]
        T = power.shape[1]
        power_avg = torch.mean(power)
        price_avg = torch.mean(price)
        assert B == price.shape[0]
        # Compute cove, which we want to minimize
        cove = util.batchwise_cove(released, price, self.epsilon, storage_rating, storage_duration)
        # Compute penalties
        baseload_penalty = (self.baseload_factor * torch.maximum(released - power_avg, torch.zeros(B,T))) ** self.baseload_degree
        storage_penalty = (self.storage_factor * torch.maximum(stored - self.storage_threshold, torch.zeros(B,T))) ** self.storage_degree
        # The following modify the above penalties
        price_factor = torch.minimum(price / price_avg, torch.full(size=(B,T), fill_value=self.price_factor)) #(self.price_factor * (price / price_avg)) ** self.price_degree
        inverse_price_factor = torch.minimum(torch.abs(torch.full(size=(B,T), fill_value=price_avg) / price), torch.full(size=(B,T), fill_value=self.price_factor))
        # Compute adaptive term to reduce effect of penalties over time
        adaptive_factor = 1
        if self.epoch >= self.adaptive_epoch:
            adaptive_factor = self.adaptive_factor / (self.epoch ** self.adaptive_degree)
        # Average over batches
        # penalties = adaptive_factor * (torch.mean(baseload_penalty * inverse_price_factor) + torch.mean(storage_penalty * price_factor))
        penalties = adaptive_factor * (torch.mean(baseload_penalty * inverse_price_factor) + torch.mean(storage_penalty * price_factor))
        loss = torch.mean(cove) + penalties
        return loss