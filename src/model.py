import torch
import torch.nn as nn

class VFNN(nn.Module):
    def __init__(self, hidden_size, num_layers, fc_hidden_sizes, input_size=3):
        super().__init__()
        self.input_size = input_size
        self.num_layers = num_layers
        self.hidden_size = hidden_size

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)

        fc1 = nn.Linear(hidden_size, fc_hidden_sizes[0])
        fc2 = nn.Linear(fc_hidden_sizes[0], fc_hidden_sizes[1])
        fc3 = nn.Linear(fc_hidden_sizes[1], 1)

        # Apply Xavier weight initialization to LSTM
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.0)

        # Apply Kaiming weight initialization to layers that use ReLU
        torch.nn.init.kaiming_uniform_(fc1.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc2.weight, mode='fan_in', nonlinearity='relu')
        torch.nn.init.kaiming_uniform_(fc3.weight, mode='fan_in', nonlinearity='relu')

        # Zero biases, in-keeping with Kaiming method
        torch.nn.init.constant_(fc1.bias, 0)
        torch.nn.init.constant_(fc2.bias, 0)
        torch.nn.init.constant_(fc3.bias, 0)

        self.nn = nn.Sequential(
            fc1,
            nn.Sigmoid(),
            # nn.ReLU(),
            fc2,
            nn.Sigmoid(),
            # nn.ReLU(),
            fc3
            # nn.ReLU()
        )
    
    def forward(self, x):
        # x has shape (B, T, 2) s.t. dim 2 has length 2 because it contains power, price
        B = x.shape[0] # batch size
        T = x.shape[1] # seq_length (num timesteps)
        input = x[:,0,:]
        R = input[:,0].unsqueeze(1) 
        input = torch.cat([input, R], dim=1)
        preds = torch.zeros(B, T)
        for t in range(T):
            # print(f'in_{t} = {input}')
            out, hidden = self.lstm(input)
            # print(f'out_{t} = {out}')
            R = torch.abs(self.nn(out))
            # print(f'R_{t} = {R}')
            preds[:, t] = R.squeeze()
            # If there are more inputs left, append this prediction to next input 
            if t < T - 1:
                input = torch.cat([x[:,t+1,:], R], dim=1)
        # a = 1/0
        return preds