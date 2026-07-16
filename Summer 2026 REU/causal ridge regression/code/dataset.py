from torch.utils.data import Dataset

# Same as VFDataset, but also contains user load
class VF2Dataset(Dataset):
    def __init__(self, data):
        self.data = data
        self.g = data[:,:,0].squeeze()
        self.p = data[:,:,1].squeeze()
        self.u = data[:,:,2].squeeze()

    #Override from Dataset (required for use w/ DataLoader)
    def __len__(self):
        glen = len(self.g)
        plen = len(self.p)
        ulen = len(self.u)
        if glen != plen:
            print(f"Dataset Warning: power:({glen}) and price:({plen}) are different lengths")
        if glen != ulen:
            print(f"Dataset Warning: power:({glen}) and loads:({ulen}) are different lengths")
        return glen

    #Override from Dataset (required for use w/ DataLoader)
    def __getitem__(self, idx):
        # (full data, power, price, user load), this is redundant but makes loss computation clear
        return (self.data[idx], self.g[idx], self.p[idx])
    
class VFDataset(Dataset):
    def __init__(self, data):
        self.data = data
        self.g = data[:,:,0].squeeze()
        self.p = data[:,:,1].squeeze()

    #Override from Dataset (required for use w/ DataLoader)
    def __len__(self):
        glen = len(self.g)
        plen = len(self.p)
        if glen != plen:
            print(f"Dataset Warning: power:({glen}) and price:({plen}) are different lengths")
        return glen

    #Override from Dataset (required for use w/ DataLoader)
    def __getitem__(self, idx):
        # (Full data, price), this is redundant but makes loss computation clear
        return (self.data[idx], self.g[idx], self.p[idx])