import torch
import torch.nn as nn
import torch.nn.functional as F

import numpy as np

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class NQF_RNN(nn.Module):
    def __init__(self, hidden_size, num_layers, nqf_hidden_sizes, input_size=1):
        super(NQF_RNN, self).__init__()
        self.input_size = input_size
        self.num_layers = num_layers
        self.hidden_size = hidden_size

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.nqf = NQF(hidden_size, nqf_hidden_sizes)

    def forward(self, x, alphas):
        #alphas are the quantile levels to be passed to the NQF across timesteps (shape = [timesteps])
        #during training, this should be the same quantile level repeated across timesteps
        #during inference, this should contain uniformly random quantiles to sample from

        # x should have shape [batch size, timesteps)]
        x = x.unsqueeze(-1)
        B = x.shape[0] #batch size
        T = x.shape[1] #timesteps
        output, _ = self.lstm(x)
        assert output.shape[1] == T
        preds = torch.zeros(size=(B,T))
        for t in range(T):
            quantile_pred = self.nqf(output[:,t], alphas[t])
            preds[:,t] = quantile_pred.squeeze()
        return preds

class PLinear(nn.Module):
    """
    class Linear(nn.Module):
        def __init__(self, in_features, out_features, bias=True):
            
        def forward(self, input):
            return F.linear(input, self.weight, self.bias)
    """
    def __init__(self, in_features, out_features, bias=True):
        super(PLinear, self).__init__()
        self.linear = nn.Linear(in_features, out_features, bias=bias)

    def forward(self, input):
        return F.linear(input, self.linear.weight ** 2, self.linear.bias)


class NQF(nn.Module):
    def __init__(self, input_size, hidden_sizes, output_size=1):
        super(NQF, self).__init__()
        self.fc1 = PLinear(input_size + 1, hidden_sizes[0])
        self.fc2 = PLinear(hidden_sizes[0], hidden_sizes[1])
        self.fc3 = PLinear(hidden_sizes[1], output_size)
        self.tanh = nn.Tanh()

    def forward(self, x, alpha):
        #x has shape [batch size, input size]
        alphas = torch.full([x.shape[0]], alpha).unsqueeze(dim=1).to(device)
        #adding alpha term to each input in batch
        input = torch.concat([x, alphas], dim=1)
        x1 = self.tanh(self.fc1(input))
        x2 = self.tanh(self.fc2(x1))
        y = self.fc3(x2)
        return y