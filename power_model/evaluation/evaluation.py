import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial.distance import jensenshannon
import matplotlib.ticker as mtick


class Metrics():
    def __init__(self, name, speeds, power, preds):
        self.name = name
        self.speeds = speeds
        self.power = power
        self.preds = preds
        self.npower = power / np.max(power)
        self.npreds = preds / np.max(preds)
    
    def rmse(self):
        return float(np.sqrt(np.mean((self.npower - self.npreds) ** 2)))

    def cross_correlation(self):
        return float(np.corrcoef(self.npower, self.npreds)[0, 1])

    def similarity(self, bins=50): # power curve similarity
        H_true, _, _ = np.histogram2d(self.speeds, self.power, bins=bins)
        H_pred, _, _ = np.histogram2d(self.speeds, self.preds, bins=bins)
        H_true_norm = H_true / H_true.sum()
        H_pred_norm = H_pred / H_pred.sum()
        js_div = jensenshannon(H_true_norm.flatten(), H_pred_norm.flatten())
        similarity = 1 - js_div
        return float(similarity)
    
    def bias(self):
        return float(np.mean(self.npreds - self.npower))
    
    def PLF5(self, v, P, L, A, B, C):
        return L + (P - L) / (1 + (v / B) ** A) ** C
    
    # compare predictions against steady and loss power curves
    def rms_theoretical(self):
        power_steady = 163 * self.PLF5(self.speeds, 1.5, 0, -161.50069891, 10.15104929, 0.01857233)
        power_loss = self.PLF5(self.speeds, 244.4718239, 0, -10.9176942, 10.8237373, 0.2852041)
        rms_steady = np.sqrt(np.mean((power_steady) ** 2))
        rms_loss = np.sqrt(np.mean((power_loss) ** 2))
        return rms_steady, rms_loss

    def rms(self):
        rms_true = np.sqrt(np.mean((self.power) ** 2))
        rms_pred = np.sqrt(np.mean((self.preds) ** 2))
        # steady, true, predicted
        return rms_true, rms_pred
    
    def print_metrics(self):
        print(f"{self.name} Metrics:")
        print(f"RMSE: {self.rmse()}")
        print(f"Cross Correlation: {self.cross_correlation()}")
        print(f"Similarity: {self.similarity()}")
        print(f"Bias: {self.bias()}")
        print(f"RMS Steady: {self.rms_theoretical()[0]}")
        print(f"RMS Loss: {self.rms_theoretical()[1]}")
        print(f"RMS True: {self.rms()[0]}")
        print(f"RMS Predicted: {self.rms()[1]}")
        return
    
    def get_metrics(self):
        return {
            'RMSE': self.rmse(),
            'Cross Correlation': self.cross_correlation(),
            'Similarity': self.similarity(),
            'Bias': self.bias(),
            'RMS Steady': self.rms_theoretical()[0],
            'RMS Loss': self.rms_theoretical()[1],
            'RMS True': self.rms()[0],
            'RMS Predicted': self.rms()[1]
        }


class Plot():
    def __init__(self, name, speeds, power, preds):
        self.name = name
        self.speed = speeds
        self.power = power
        self.preds = preds
        self.npower = power / np.max(power)
        self.npreds = preds / np.max(preds)

    def power_curve(self, figsize=(7, 5), alpha=0.002):
        plt.figure(figsize=figsize)
        plt.scatter(self.speed, self.power, alpha=alpha, label='Historical')
        plt.scatter(self.speed, self.preds, alpha=alpha, label='Predicted')
        plt.xlabel('Wind Speed (m/s)')
        plt.ylabel('Power (MW)')
        plt.title(f'{self.name} Power Curves')
        leg = plt.legend()
        for leg in leg.legend_handles:
            leg.set_alpha(0.5)
        plt.show()

    def time_series(self, figsize=(7, 5)):
        plt.figure(figsize=figsize)
        # plt.figure(figsize=figsize, dpi=200)

        plt.plot(self.power[:200].reset_index(drop=True), label='Historical', linewidth=2)
        plt.plot(self.preds[:200].reset_index(drop=True), label='Predicted', linewidth=2)
        
        # plt.xlabel('Time (Hours)', fontsize=28)
        # plt.ylabel('Power (MW)', fontsize=28)
        # plt.xticks(fontsize=18)
        # plt.yticks(fontsize=18)
        # plt.legend(fontsize=22)

        plt.xlabel('Time (Hours)')
        plt.ylabel('Power (MW)')
        plt.title(f'{self.name} Power Time Series')
        plt.legend()

        plt.tight_layout()
        plt.show()

    # update with the difference hotspots plot later
    def power_density(self, figsize=(10, 4)):
        H_true, _, _ = np.histogram2d(self.speed, self.power, bins=50)
        H_pred, _, _ = np.histogram2d(self.speed, self.preds, bins=50)
        H_true_norm = H_true / H_true.sum()
        H_pred_norm = H_pred / H_pred.sum()
        js_div = jensenshannon(H_true_norm.flatten(), H_pred_norm.flatten())  # Value between 0 and 1
        similarity = 1 - js_div
        match_percentage = np.round(similarity * 100, 2)

        # log transform
        vals_true = np.log(H_true.T)
        vals_true[np.isneginf(vals_true)] = 0
        vals_true = vals_true / vals_true.max()
        vals_pred = np.log(H_pred.T)
        vals_pred[np.isneginf(vals_pred)] = 0
        vals_pred = vals_pred / vals_pred.max()

        fig, axs = plt.subplots(1, 2, figsize=figsize)
        axs[0].imshow(vals_true, origin='lower', cmap='viridis')
        axs[0].set_title("Historical Density")
        axs[1].imshow(vals_pred, origin='lower', cmap='viridis')
        axs[1].set_title("Predicted Density")

        cbar = fig.colorbar(axs[1].imshow(vals_pred, origin='lower', cmap='viridis'), ax=axs, orientation='vertical')
        cbar.set_label('Density')
        fig.suptitle(f"{self.name} Power Curve Density (Match: {match_percentage}%)")
        plt.show()

    def density_difference(self, figsize=(7, 5)):
        H_true, _, _ = np.histogram2d(self.speed, self.power, bins=50)
        H_pred, _, _ = np.histogram2d(self.speed, self.preds, bins=50)
        H_true_norm = H_true / H_true.sum()
        H_pred_norm = H_pred / H_pred.sum()
        js_div = jensenshannon(H_true_norm.flatten(), H_pred_norm.flatten())  # Value between 0 and 1
        similarity = 1 - js_div
        match_percentage = np.round(similarity * 100, 2)

        # log transform
        vals_true = np.log(H_true.T)
        vals_true[np.isneginf(vals_true)] = 0
        vals_true = vals_true / vals_true.max()
        vals_pred = np.log(H_pred.T)
        vals_pred[np.isneginf(vals_pred)] = 0
        vals_pred = vals_pred / vals_pred.max()
        # difference
        diff = vals_pred - vals_true


        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(diff, origin='lower', cmap='bwr', vmin=-np.max(np.abs(diff)), vmax=np.max(np.abs(diff)))
        ax.set_xlabel("Speed Bin")
        ax.set_ylabel("Power Bin")
        ax.tick_params(axis='both', which='major')
        ax.set_title(f"{self.name} Density Difference (Match: {match_percentage}%)")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Density Diff. (Pred - Hist)")
        cbar.ax.tick_params()

        # fig, ax = plt.subplots(figsize=figsize, dpi=200)
        # im = ax.imshow(diff, origin='lower', cmap='bwr', vmin=-np.max(np.abs(diff)), vmax=np.max(np.abs(diff)))
        # ax.set_xlabel("Speed Bin", fontsize=28)
        # ax.set_ylabel("Power Bin", fontsize=28)
        # ax.tick_params(axis='both', which='major', labelsize=18)
        # cbar = fig.colorbar(im, ax=ax)
        # cbar.set_label("Density Diff. (Pred - Hist)", fontsize=24)
        # cbar.ax.tick_params(labelsize=18)

        plt.tight_layout()
        plt.show()

    def avg_powers(self, years=10, start_year=2014, figsize=(10, 5)):
        power_mean = np.mean(np.array_split(self.power, years), axis=1)
        pred_mean = np.mean(np.array_split(self.preds, years), axis=1)

        plt.figure(figsize=figsize)
        plt.plot(power_mean, label='Historical')
        plt.plot(pred_mean, label='Predicted')
        plt.xlabel('Year')
        plt.xticks(ticks=np.arange(0, years), labels=[str(start_year + i) for i in range(years)])
        plt.ylim(0, max(np.max(pred_mean), np.max(power_mean)) * 1.1)
        plt.ylabel('Power (MW)')
        plt.title(f'{self.name} Average Power ({years}-Year Means)')
        plt.legend()
        plt.grid(axis='x')
        plt.show()
    
    def avg_powers_percentage(self, years=10, start_year=2014, figsize=(10, 5)):
        power_mean = np.mean(np.array_split(self.power, years), axis=1)
        pred_mean = np.mean(np.array_split(self.preds, years), axis=1)

        plt.figure(figsize=figsize)
        ax = plt.gca()
        plt.bar(np.arange(years), (pred_mean - power_mean) / power_mean, label='(Pred - Hist) / Hist', edgecolor='black', zorder=3)
        plt.xlabel('Year')
        plt.xticks(ticks=np.arange(0, years), labels=[str(start_year + i) for i in range(years)])
        plt.ylabel('Percentage Power Difference')
        plt.title(f'{self.name} Average Power Percentage Difference ({years}-Year Means)')
        plt.legend()
        plt.grid(axis='y', alpha=0.5, zorder=0)
        plt.axhline(0, color='black', linewidth=0.8)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
        plt.show()

    def plot_all(self):
        self.power_curve()
        self.time_series()
        self.power_density()
        self.density_difference()
        self.avg_powers()
        self.avg_powers_percentage()


if __name__ == "__main__":
    # df = pd.read_csv('data/processed/dataset_14-23.csv')
    df = pd.read_csv('power_model/probabilistic/results/rnn_168hr_1423.csv')

    metrics = Metrics(df['speed'], df['power'], df['preds'])
    plot = Plot('RNN 168hr', df['speed'], df['power'], df['preds'])

    # plot.power_curve()
    # plot.time_series()
    # plot.power_density()
    plot.avg_powers()
    plot.power_density()
    plot.density_difference()
