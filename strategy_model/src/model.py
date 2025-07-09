import torch
import torch.nn as nn
import torch.nn.functional as F
import util

# VFNN_2 also takes in user load as an input feature, otherwise it is the same as VFNN
class VFNN_2(nn.Module):
    def __init__(self, hidden_size, num_layers, fc_hidden_sizes, wf_rating, battery_rating, battery_duration, input_size=4):
        super().__init__()
        self.input_size = input_size
        self.num_layers = num_layers
        self.hidden_size = hidden_size

        # BATTERY SPECS
        self.battery_rating = battery_rating # should be in MW
        self.duration = battery_duration # should be in hrs
        self.capacity = battery_rating * battery_duration # should be in MWh

        # WIND FARM SPECS
        self.wf_rating = wf_rating

        self.rte = util.RTE

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)

        # Custom PLinear class squares weights to ensure monotonicity
        fc1 = PLinear(hidden_size, fc_hidden_sizes[0])
        fc2 = PLinear(fc_hidden_sizes[0], fc_hidden_sizes[1])
        fc3 = PLinear(fc_hidden_sizes[1], 1)

        # Apply Xavier weight initialization to LSTM
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.0)

        # Apply Kaiming weight initialization to layers that use ReLU
        torch.nn.init.kaiming_uniform_(fc1.linear.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc2.linear.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc3.linear.weight, mode='fan_in', nonlinearity='relu')

        # Zero biases, in-keeping with Kaiming method
        torch.nn.init.constant_(fc1.linear.bias, 0)
        torch.nn.init.constant_(fc2.linear.bias, 0)
        torch.nn.init.constant_(fc3.linear.bias, 0)

        # tanh, alongside PLinear, ensures monotonicity
        self.nn = nn.Sequential(
            fc1,
            nn.ReLU(),
            fc2,
            nn.ReLU(),
            fc3,
            nn.ReLU()
        )
    
    def forward(self, x):
        # x has shape (B, T, 3) s.t. dim 2 has length 3 because it contains power, price, user load
        B = x.shape[0] # batch size
        T = x.shape[1] # seq_length (num timesteps)
        input = x[:,0,:]
        s = torch.tensor(0, dtype=torch.float32)
        s = torch.Tensor.repeat(s, B).unsqueeze(1)
        input = torch.cat([input, s], dim=1)
        # preds contains [Batch size, time steps, 3] where the last dimension 
        # contains the following values: [released power, stored power, lost power]
        preds = torch.zeros(B, T, 3)
        lost = torch.zeros((B,1))
        for t in range(T):
            out, hidden = self.lstm(input)
            r = self.nn(out) * self.wf_rating
            g = input[:,0]
            # Ensure availability condition not violated (cannot release energy > stored + generated)
            r = torch.minimum(torch.reshape(g, (B,1)) + torch.reshape(s, (B,1)), r)
            g_regen = torch.maximum(r - torch.reshape(g, (B,1)), torch.zeros((B,1)))
            # Update lost power with any power that could have been stored but was not due to the battery rating
            lost += torch.maximum(torch.zeros((B,1)), g_regen - torch.full_like(g_regen, self.battery_rating))
            # Ensure power regenerated (discharged) from battery does not exceed battery power rating
            g_regen = torch.minimum(g_regen, torch.full_like(g_regen, self.battery_rating))
            g_direct = torch.maximum(r - g_regen, torch.zeros((B,1)))
            assert (g_regen + g_direct == r).all()
            # Multiply energy discharged by battery by round trip efficiency (RTE) to accurately model physical losses
            lost += g_regen * (1 - self.rte)
            r_curtailed = g_direct + (g_regen * self.rte)
            preds[:, t, :] = torch.cat([r_curtailed, s, lost], dim=-1)
            # Reset lost to zero
            lost = torch.zeros((B,1))
            # Update stored energy for next time step
            charge = torch.reshape(g, (B,1)) - torch.reshape(r, (B,1))
            # Ensure charge does not exceed battery power rating
            s += torch.minimum(charge, torch.full_like(charge, self.battery_rating))
            # Ensure storage is non-negative
            s = torch.maximum(s, torch.zeros((B,1)))
            # If storage exceeds capacity, add any power that will be capped to lost
            lost += torch.maximum(torch.zeros((B,1)), s - torch.full_like(s, self.capacity))
            # Ensure storage does not exceed battery capacity
            s = torch.minimum(s, torch.full_like(s, self.capacity))
            # If there are more inputs left, append this prediction to next input 
            if t < T - 1:
                input = torch.cat([x[:,t+1,:], s], dim=1)
        return preds
    
class VFNN(nn.Module):
    def __init__(self, hidden_size, num_layers, fc_hidden_sizes, input_size=3):
        super().__init__()
        self.input_size = input_size
        self.num_layers = num_layers
        self.hidden_size = hidden_size
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)

        # Custom PLinear class squares weights to ensure monotonicity
        fc1 = PLinear(hidden_size, fc_hidden_sizes[0])
        fc2 = PLinear(fc_hidden_sizes[0], fc_hidden_sizes[1])
        fc3 = PLinear(fc_hidden_sizes[1], 1)

        # Apply Xavier weight initialization to LSTM
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.0)

        # Apply Kaiming weight initialization to layers that use ReLU
        torch.nn.init.kaiming_uniform_(fc1.linear.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc2.linear.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc3.linear.weight, mode='fan_in', nonlinearity='relu')

        # Zero biases, in-keeping with Kaiming method
        torch.nn.init.constant_(fc1.linear.bias, 0)
        torch.nn.init.constant_(fc2.linear.bias, 0)
        torch.nn.init.constant_(fc3.linear.bias, 0)

        # tanh, alongside PLinear, ensures monotonicity
        self.nn = nn.Sequential(
            fc1,
            nn.ReLU(),
            fc2,
            nn.ReLU(),
            fc3,
            nn.ReLU()
        )
    
    def forward(self, x):
        # x has shape (B, T, 2) s.t. dim 2 has length 2 because it contains power, price
        B = x.shape[0] # batch size
        T = x.shape[1] # seq_length (num timesteps)
        input = x[:,0,:]
        s = torch.tensor(0, dtype=torch.float32)
        s = torch.Tensor.repeat(s, B).unsqueeze(1)
        input = torch.cat([input, s], dim=1)
        preds = torch.zeros(B, T, 2)
        for t in range(T):
            out, hidden = self.lstm(input)
            r = self.nn(out)
            g = input[:,0]
            # Ensure availability condition not violated
            r = torch.minimum(torch.reshape(g, (B,1)) + torch.reshape(s, (B,1)), r)
            preds[:, t, :] = torch.cat([r, s], dim=-1)
            # Update stored for next time step
            s += torch.reshape(g, (B,1)) - torch.reshape(r, (B,1))
            # print(f'in_{t} = {input}')
            # print(f'out_{t} = {out}')
            # print(f'r_{t} = {r}')
            # If there are more inputs left, append this prediction to next input 
            if t < T - 1:
                input = torch.cat([x[:,t+1,:], s], dim=1)
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
    