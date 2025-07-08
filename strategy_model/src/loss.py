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
        self.price_factor = 3 # price_factor
        self.price_degree = 2 # price_degree
        # Controls threshold, below which the model is not penalized for its stored energy
        self.storage_threshold = storage_threshold
        # Prevents division by 0 in COVE computation
        self.epsilon = epsilon
        # For adaptive term
        self.epoch = 0
    
    def step(self):
        self.epoch += 1

    def forward(self, released, stored, power, price, ground_truth_avg=-1):
        B = power.shape[0]
        T = power.shape[1]
        if ground_truth_avg == -1:
            power_avg = torch.mean(power)
        else:
            power_avg = ground_truth_avg
        price_avg = torch.mean(price)
        assert B == price.shape[0]
        # Take batchwise loss
        brev = util.batchwise_revenue(released, price)
        cove = 1 / (torch.abs(brev) + self.epsilon)
        # baseload_penalty = (self.baseload_factor * torch.maximum(released - power_avg, torch.zeros(B,T))) ** self.baseload_degree
        #baseload_penalty_L2 = (self.baseload_factor * torch.sqrt((released - power_avg) ** 2)) ** self.baseload_degree
        baseload_penalty = (self.baseload_factor * torch.maximum(released - power_avg, torch.zeros(B,T))) ** self.baseload_degree
        storage_penalty = (self.storage_factor * torch.maximum(stored - self.storage_threshold, torch.zeros(B,T))) ** self.storage_degree
        price_penalty = torch.minimum(price / price_avg, torch.full(size=(B,T), fill_value=self.price_factor)) #(self.price_factor * (price / price_avg)) ** self.price_degree
        inverse_price_penalty = torch.minimum(torch.abs(torch.full(size=(B,T), fill_value=price_avg) / price), torch.full(size=(B,T), fill_value=self.price_factor))
        adaptive_term = 1 / ((self.epoch + 1) ** (1/3))
        # Average over batches
        loss = torch.mean(cove) + (torch.mean(baseload_penalty * inverse_price_penalty) + torch.mean(storage_penalty * price_penalty)) # * adaptive_term
        # loss = torch.mean(baseload_penalty_L2)
        return loss