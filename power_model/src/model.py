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
        preds = torch.zeros(size=(B,T), device=x.device)
        for t in range(T):
            quantile_pred = self.nqf(output[:,t], alphas[t])
            preds[:,t] = quantile_pred.squeeze()
        return preds

class NQF_RNN_AR(nn.Module):
    def __init__(self, hidden_size, num_layers, nqf_hidden_sizes, input_size=1):
        super(NQF_RNN_AR, self).__init__()
        self.input_size = input_size
        self.num_layers = num_layers
        self.hidden_size = hidden_size

        self.lstm = nn.LSTM(input_size+1, hidden_size, num_layers=num_layers, batch_first=True)
        self.nqf = NQF(hidden_size, nqf_hidden_sizes)

    def forward(self, x, alphas, targets=None, teacher_forcing_prob=1.0):
        x = x.unsqueeze(-1)
        B = x.shape[0] #batch size
        T = x.shape[1] #timesteps
        
        hidden = None
        prev_pred = torch.zeros(B, 1).to(device)
        
        preds = []
        for t in range(T):
            if self.training and targets is not None and np.random.rand() < teacher_forcing_prob:
                # teacher forcing during training
                power_input = targets[:, t-1:t] if t > 0 else prev_pred
            else:
                # autoregressive method during testing
                power_input = prev_pred
            
            lstm_input = torch.cat([x[:, t:t+1, :], power_input.unsqueeze(-1)], dim=2)
            output, hidden = self.lstm(lstm_input, hidden)
            
            quantile_pred = self.nqf(output.squeeze(1), alphas[t])
            # clamp predictions to stay within [0, 1] bounds
            quantile_pred = torch.clamp(quantile_pred, 0, 1)

            preds.append(quantile_pred)
            prev_pred = quantile_pred

        return torch.cat(preds, dim=1)


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
        self.fc1 = nn.Linear(input_size + 1, hidden_sizes[0])
        self.fc2 = nn.Linear(hidden_sizes[0], hidden_sizes[1])
        self.fc3 = nn.Linear(hidden_sizes[1], output_size)
        self.tanh = nn.Tanh()
        self.init_weights()

    def init_weights(self):
        for layer in [self.fc1, self.fc2]:
            nn.init.xavier_uniform_(layer.weight, gain=0.5)
            nn.init.constant_(layer.bias, 0.0)
        
        nn.init.xavier_uniform_(self.fc3.weight, gain=0.1)
        nn.init.constant_(self.fc3.bias, 0.0)

    def forward(self, x, alpha):
        #x has shape [batch size, input size]
        alphas = torch.full([x.shape[0]], alpha).unsqueeze(dim=1).to(device)
        #adding alpha term to each input in batch
        input = torch.concat([x, alphas], dim=1)
        x1 = self.tanh(self.fc1(input))
        x2 = self.tanh(self.fc2(x1))
        y = self.fc3(x2)
        return y