from torch.utils.data import Dataset

class WindDataset(Dataset):
    def __init__(self, features, power):
        self.v = features
        self.g = power

    #Override from Dataset (required for use w/ DataLoader)
    def __len__(self):
        glen = len(self.g)
        vlen = len(self.v)
        if glen != vlen:
            print(f"Dataset Warning: power:({glen}) and speed:({vlen}) are different lengths")
        return glen

    #Override from Dataset (required for use w/ DataLoader)
    def __getitem__(self, idx):
        # (Input features, power)
        return (self.v[idx], self.g[idx])
