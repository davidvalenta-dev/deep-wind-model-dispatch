import torch
import torch.nn as nn
import util

class VFLoss(nn.Module):
    def __init__(self, baseload_degree, baseload_factor, peaker_degree, peaker_factor, epsilon, eta, gamma, s_threshold=10):
        super().__init__()
        # Control severity of penalties
        self.baseload_degree = baseload_degree
        self.baseload_factor = baseload_factor
        self.peaker_degree = peaker_degree
        self.peaker_factor = peaker_factor
        # Control storage threshold
        self.s_threshold = s_threshold
        # Control gradient of peaker goal
        self.eta = eta
        self.gamma = gamma
        # Prevents division by 0 error for inverse LCOE computation
        self.epsilon = epsilon

    def forward(self, released, stored, power, price):
        B = power.shape[0]
        T = power.shape[1]
        power_avg = torch.mean(power)
        price_avg = torch.mean(price)
        assert B == price.shape[0]
        # Take batchwise loss
        brev = util.batchwise_revenue(released, price)
        lcoe = 1 / (torch.abs(brev) + self.epsilon)
        peaker_goal_high =  ((self.eta * torch.maximum(price - price_avg, torch.zeros(B,T))) ** self.gamma) * price_avg
        peaker_goal_low =  (((1 / self.eta) * torch.maximum(price_avg - price, torch.zeros(B,T))) ** (1 / self.gamma)) * price_avg
        # Add soft constraints
        storage_condition = stored > self.s_threshold
        baseload_condition = released < power_avg
        price_above_avg = price > price_avg
        peaker_condition_high = released < peaker_goal_high
        peaker_condition_low = released > peaker_goal_low
        # We only care about following the high or low peaker conditions when the price is above or below avg.
        peaker_condition_high = torch.logical_and(price_above_avg, peaker_condition_high)
        peaker_condition_low = torch.logical_and(torch.logical_not(price_above_avg), peaker_condition_low)
        # If condition is not met, penalty is 0
        storage_penalty = 0
        baseload_penalty = 0
        peaker_penalty_high = 0
        peaker_penalty_low = 0
        # Otherwise, penalize
        if storage_condition.any():
            storage_penalty = (self.baseload_factor * torch.abs(stored - self.s_threshold)) ** self.baseload_degree
            storage_penalty = torch.mean(storage_penalty[storage_condition])
            # print(storage_penalty)
        if baseload_condition.any():
            baseload_penalty = (self.baseload_factor * torch.abs(released - power_avg)) ** self.baseload_degree
            baseload_penalty = torch.mean(baseload_penalty[baseload_condition])
        if peaker_condition_high.any():
            peaker_penalty_high = (self.peaker_factor * torch.abs(released - peaker_goal_high)) ** self.peaker_degree
            peaker_penalty_high = torch.sum(peaker_penalty_high[peaker_condition_high])
            # print(f'High = {peaker_penalty_high}')
            
        if peaker_condition_low.any():
            peaker_penalty_low = (self.peaker_factor * torch.abs(released - peaker_goal_low)) ** self.peaker_degree
            peaker_penalty_low = torch.sum(peaker_penalty_low[peaker_condition_low])
            # print(f'Low = {peaker_penalty_low}')
            
        # Average over batches, sum penalties 
        loss = torch.mean(lcoe) + baseload_penalty + storage_penalty # + peaker_penalty_high + peaker_penalty_low
        return loss