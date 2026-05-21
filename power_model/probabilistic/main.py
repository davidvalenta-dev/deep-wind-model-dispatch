import numpy as np
import pandas as pd
from model import ProbModel
from sklearn.metrics import mean_squared_error
import json
import itertools
import pickle


def main():
    df = pd.read_csv('../../data/processed/dataset_clean_no-outliers.csv').drop(columns=['Unnamed: 0.1', 'Unnamed: 0'])
    df['speed'] = df['speed'][6:].reset_index(drop=True)
    df['power'] = df['power'][:-6].reset_index(drop=True)
    normalized = (df['power'] - df['power'].min()) / (df['power'].max() - df['power'].min()) # normalize
    df['power'] = np.clip(normalized, 1e-15, 1 - 1e-15)
    df.dropna(inplace=True)

    # train validate test split
    # first 70% for training, next 20% for validation, last 10% for testing
    n = len(df)
    train_size = int(0.7 * n)
    val_size = int(0.2 * n)

    train_df = df.iloc[:train_size].reset_index(drop=True)
    val_df = df.iloc[train_size:train_size+val_size].reset_index(drop=True)
    test_df = df.iloc[train_size+val_size:].reset_index(drop=True)

    param_grid = {
        'spline_k': [1, 2, 3, 4, 5],
        'spline_s': [0, 0.01, 0.1, 0.5, 1, 2, 5, 25, 100, 250],
        'smoothing_factor': [0.0001, 0.001, 0.01, 0.05, 0.1, 0.2],
        'drift_factor': [0.00001, 0.0001, 0.001, 0.01, 0.1],
        'reset_prev_w': [0.0001, 0.001, 0.01, 0.02, 0.05, 0.1]
    }

    # Generate all combinations of parameters
    keys, values = zip(*param_grid.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

    best_mse = float('inf')
    best_params = None
    best_model = None
    logs = []

    for params in param_combinations:
        model = ProbModel(
            binning_method='equal_width',
            interval_params=1,
            **params
        )

        mses = []
        for i in range(3):
            model.fit(train_df['speed'], train_df['power'])
            pred = model.predict(val_df['speed'])
            mses.append(mean_squared_error(val_df['power'], pred))
        mse = np.mean(mses)

        log = {
            'mse': mse,
            'params': params
        }
        # print(log)
        #print(mse)
        logs.append(log)

        if mse < best_mse:
            best_mse = mse
            best_params = params
            best_model = ProbModel(
                binning_method='equal_width',
                interval_params=1,
                **params
            )
            best_model.fit(train_df['speed'], train_df['power'])
            print(f"New best mse: {best_mse}, with parameters: {best_params}")


        # periodically save logs
        if len(logs) % 100 == 0:
            save_logs(logs)
            # print(f"Best Validation MSE: {best_mse} and Best Params: {best_params}")
            # print(f"Current MSE: {mse} and Params: {params}\n")

    save_logs(logs)
    print(f"Final logs saved")
    print(f"Best Validation MSE: {best_mse} and Best Params: {best_params}\n")

    # Save the best model using pickle
    with open('best_probmodel2.pkl', 'wb') as f:
        pickle.dump({
            'params': best_params,
            'model': best_model
        }, f)

    # evaluate on the test set
    test_pred = best_model.predict(test_df['speed'])
    test_mse = mean_squared_error(test_df['power'], test_pred)
    print(f"Test MSE of best model: {test_mse}")


def save_logs(logs, filename='logs2.jsonl'):
    with open(filename, "w") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
    print(f"{len(logs)} logs saved to {filename}")


if __name__ == '__main__':
    main()