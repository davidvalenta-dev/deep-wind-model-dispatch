import torch
import torch.nn as nn
import torch.nn.functional as F

# VFNN_2 also takes in user load as an input feature, otherwise it is the same as VFNN
class VFNN_2(nn.Module):
    def __init__(self, hidden_size, num_layers, fc_hidden_sizes, input_size=4):
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
        # x has shape (B, T, 3) s.t. dim 2 has length 3 because it contains power, price, user load
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
    