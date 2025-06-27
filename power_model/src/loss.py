import torch
import torch.nn as nn

# * * * * * * * * * * * * * * * * * * * * * 
#           Probabilistic Loss 
# * * * * * * * * * * * * * * * * * * * * * 

class CRPSLoss(nn.Module):
    """
    CRPSLoss for quantile regression.

    Args:
        tail (str, optional): Specifies the tail to weight the loss. 
                                Options are 'left', 'right', or None. 
                                Default is None, which means no weighting.
    """
    def __init__(self):
        super(CRPSLoss, self).__init__()

    #Computes CRPS loss using Riemmanian approximation (trapezoidal rule)
    def forward(self, quantile_levels, quantile_preds, target):
        # #Expected shape for Quantile Preds: [batch size, time steps ahead to predict, quantile levels]
        M = quantile_preds.shape[2]
        device = quantile_preds.device
        quantile_levels = quantile_levels.to(device)
        target = target.to(device)

        # Compute pinball loss using the vectorized function

        #First term in trapezoidal rule
        pinball_1 = self.pinball_loss(quantile_levels[:M-1], quantile_preds[:, :, :M-1], target)
        #Second term in trapezoidal rule
        pinball_2 = self.pinball_loss(quantile_levels[1:M], quantile_preds[:, :, 1:M], target)
        # Compute CRPS loss by averaging over quantiles, timesteps, and batch size
        avg_crps = (torch.sum(pinball_1) + torch.sum(pinball_2)) / M
        
        return avg_crps

    def pinball_loss(self, quantile_levels, quantile_preds, target):
        """
        Vectorized pinball loss computation for all quantiles at once.
    
        Args:
            quantile_levels: Tensor of shape [num_quantiles] containing quantile levels.
            quantile_preds: Tensor of shape [batch_size, timesteps, num_quantiles] containing predicted quantiles.
            target: Tensor of shape [batch_size, timesteps] containing true target values.
    
        Returns:
            Tensor of shape [batch_size, timesteps, num_quantiles] representing pinball loss.
        """
        target_expanded = target.unsqueeze(-1).expand_as(quantile_preds)  # Shape: [batch_size, timesteps, num_quantiles]
        pinball = (target_expanded - quantile_preds) * (quantile_levels - (target_expanded < quantile_preds).float())
    
        return pinball  # Shape: [batch_size, timesteps, num_quantiles]

class QuantileLoss(nn.Module):
    """
    QuantileLoss
    """
    def __init__(self, quantile_idx, T):
        super(QuantileLoss, self).__init__()
        self.T = T
        self.m = quantile_idx
    
    def forward(self, quantile_levels, quantile_preds, target):
        N = target.shape[0]
        t_0 = self.T - quantile_preds.shape[1]

        pinball_sum = 0
        for i in range(N):
            for t in range(self.T - t_0):
                pinball_sum += self.pinball_loss(quantile_levels[self.m], quantile_preds[i, t, self.m], target[i, t])

        return pinball_sum / (N * (self.T - t_0))  # Average over all sequences and timesteps

    def pinball_loss(self, quantile_level, quantile_pred, target):
        """
        Vectorized pinball loss computation for all quantiles at once.
    
        Args:
            quantile_leves: Scalar
            quantile_pred: Scalar
            target: Scalar
    
        Returns:
            Scalar
        """
        pinball = (target - quantile_pred) * (quantile_level - (target < quantile_pred).float())
    
        return pinball 
    
class wCRPSLoss(nn.Module):
    def __init__(self, T, tail):
        super(wCRPSLoss, self).__init__()
        self.T = T
        self.tail = tail
    
    def forward(self, quantile_levels, quantile_preds, target):
        N = target.shape[0]
        M = quantile_preds.shape[2]
        t_0 = self.T - quantile_preds.shape[1]

        device = quantile_preds.device
        quantile_levels = quantile_levels.to(device)
        target = target.to(device)

        # Compute pinball loss using the vectorized function
        wcrps = 0
        for i in range(N):
            for t in range(self.T - t_0):
                avg_pinball = 0
                for m in range(M):
                    avg_pinball += 2 * self.w_pinball_loss(quantile_levels[m], quantile_preds[i,t,m], target[i,t])
                wcrps += avg_pinball / M

        return wcrps / (N * (self.T - t_0))

    def w_pinball_loss(self, quantile_level, quantile_pred, target):
        """
        Vectorized pinball loss computation for all quantiles at once.

        Args:
            quantile_level: Scalar 
            quantile_pred: Scalar
            target: Scalar

        Returns:
            Scalar 
        """
        pinball = (target - quantile_pred) * (quantile_level - (target< quantile_pred).float())

        if self.tail == 'right':
            weight = quantile_level ** 2
        elif self.tail == 'left':
            weight = (1 - quantile_level) ** 2
        
        return pinball * weight 
class sumCRPSLoss(nn.Module):
    def __init__(self, T):
        super(sumCRPSLoss, self).__init__()
        self.T = T

    def forward(self, quantile_levels, quantile_preds, target):
        N = target.shape[0]
        t_0 = self.T - quantile_preds.shape[1]

        eCRPS = self.forward_eCRPS(quantile_levels, quantile_preds, target)

        eCRPS_sum = torch.sum(eCRPS, dim=1)  # Sum over timesteps for each sequence
        eCRPS_sum = torch.sum(eCRPS_sum, dim=0)  # Sum over sequences

        return eCRPS_sum / (N * (self.T - t_0))  # Average over all sequences and timesteps

    def forward_eCRPS(self, quantile_levels, quantile_preds, target):
        yhat = quantile_preds
        y = target

        M = quantile_levels.shape[0]  # Number of quantile levels

        first_sum = 0
        for m in range(M):
            first_sum += torch.abs(y - yhat[:, :, m])
        first_part = first_sum / M

        second_double_sum = 0
        for m in range(M):
            for k in range(M):
                second_double_sum += torch.abs(yhat[:, :, m] - yhat[:, :, k])
        second_part = second_double_sum / (2*(M**2))

        return first_part - second_part

# * * * * * * * * * * * * * * * * * * * * * 
#              Point Loss 
# * * * * * * * * * * * * * * * * * * * * * 
class NDLoss(nn.Module):
    """
    NDLoss, or Normalized Deviation loss.
    """
    def __init__(self):
        super(NDLoss, self).__init__()
    
    def forward(self, quantile_levels, quantile_preds, target):
        yhat = quantile_preds[:, :, 3]
        y = target

        # numerator
        diff = y - yhat
        abs_diff = torch.abs(diff)
        sum_abs_diff = torch.sum(abs_diff, dim=1)
        sum_abs_diff = torch.sum(sum_abs_diff, dim=0)

        # denominator
        abs_y = torch.abs(y)
        sum_abs_y = torch.sum(abs_y, dim=1)
        sum_abs_y = torch.sum(sum_abs_y, dim=0)

        return sum_abs_diff / sum_abs_y
    
class NRMSELoss(nn.Module):
    """
    NRMSELoss, or Normalized Root Mean Squared Error loss.
    """
    def __init__(self, T):
        super(NRMSELoss, self).__init__()
        self.T = T
    
    def forward(self, quantile_levels, quantile_preds, target):
        N = target.shape[0]
        t_0 = self.T - quantile_preds.shape[1]

        yhat = quantile_preds[:, :, 3]
        y = target

        # numerator
        diff = y - yhat
        sq_diff = diff ** 2
        sum_sq_diff = torch.sum(sq_diff, dim=1)
        sum_sq_diff = torch.sum(sum_sq_diff, dim=0)

        # denominator
        abs_y = torch.abs(y)
        sum_abs_y = torch.sum(abs_y, dim=1)
        sum_abs_y = torch.sum(sum_abs_y, dim=0)

        norm_factor = 1 / (N * (self.T - t_0))
        return ((norm_factor * sum_sq_diff) ** 0.5) / (norm_factor * sum_abs_y.mean()) 