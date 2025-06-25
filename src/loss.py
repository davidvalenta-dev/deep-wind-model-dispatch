import torch
import torch.nn as nn
import util

class VFLoss(nn.Module):
    def __init__(self, degree=1, factor=4, epsilon=0.0001):
        super().__init__()
        self.degree = degree
        self.factor = factor
        self.epsilon = epsilon

    def forward(self, power, price):
        B = power.shape[0]
        assert B == price.shape[0]
        # Take batchwise loss
        bvf = util.batchwise_value_factor(power, price)
        # loss = torch.abs(self.factor * (bvf - torch.ones(B))) ** self.degree
        loss = 1 / (torch.abs(bvf) + self.epsilon)
        # Average over batches
        loss = torch.mean(loss)
        return loss