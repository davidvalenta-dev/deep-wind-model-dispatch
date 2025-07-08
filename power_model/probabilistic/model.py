import numpy as np
import pandas as pd
from scipy.stats import beta, norm
from scipy.interpolate import make_splrep
from sklearn.metrics import mean_squared_error
import random



class ProbModel:
    def __init__(self,
            binning_method = 'fixed', # 'fixed', 'equal_freq', 'equal_width', 'moving_window'
            interval_params = None, # specifications for intervals
            spline_k = 3,
            spline_s = 0.2,
            smoothing_factor = 0.01,
            drift_factor = 0.001,
            reset_prev_w = 0.02):
        
        self.binning_method = binning_method
        self.interval_params = interval_params
        self.spline_k = spline_k
        self.spline_s = spline_s
        self.smoothing_factor = smoothing_factor
        self.drift_factor = drift_factor
        self.reset_prev_w = reset_prev_w

        self.intervals = None
        self.a_spline = None
        self.b_spline = None


    def normalize_power(self, power, epsilon=1e-15):
        # normalize power values to [0, 1] and clip to (0, 1) to ensure beta distribution can fit
        normalized = (power - power.min()) / (power.max() - power.min())
        clipped = np.clip(normalized, epsilon, 1 - epsilon)
        return clipped
    

    def fit(self, speeds, power):
        #power = self.normalize_power(power)
        self.create_intervals(speeds)
        lowers, uppers = self.intervals
        
        #print(f"Parameters: {self.get_params()}")

        params = pd.DataFrame(columns=['avg_speed', 'a', 'b', 'loc', 'scale'])
        num_intervals = len(lowers)

        for i in range(num_intervals):
            lower = lowers[i]
            upper = uppers[i]
            avg_speed = (lower + upper) / 2
            filtered_power = power[(speeds >= lower) & (speeds < upper)]
            params.loc[len(params)] = [avg_speed] + list(beta.fit(filtered_power, floc=0, fscale=1))

        self.a_spline = make_splrep(np.array(params['avg_speed']), np.array(params['a']), k=self.spline_k, s=self.spline_s)
        self.b_spline = make_splrep(np.array(params['avg_speed']), np.array(params['b']), k=self.spline_k, s=self.spline_s)

        return

    # brownian motion sampling with splining
    def predict(self, speeds):
        predictions = []
        prev_w = None  # w is the inverse CDF input to get the sampled power
        reset_counter = 0

        for speed in speeds:
            a = self.a_spline(speed)
            b = self.b_spline(speed)
            # make sure a and b are valid
            if a <= 0 or b <= 0:
                a = 1e-2
                b = 1e-2

            if prev_w is None or random.random() < self.reset_prev_w: # randomly reset w occasionally
                w = np.random.rand(1)[0]
                reset_counter += 1
            else:
                # use previous w to smooth the current w; brownian motion
                smoothing_condition = norm.rvs(0, 1, size=1)[0] * self.smoothing_factor
                drift_condition = self.drift_factor * (0.5 - prev_w) # drift towards median 0.5
                w = prev_w + smoothing_condition + drift_condition

                # ensure w stays within [0, 1]
                if w < 0: w = -w
                if w > 1: w = 2 - w

            prev_w = w
            pred = beta.ppf(w, a, b, loc=0, scale=1)

            if np.isnan(pred):
                #print(f"Predicted {pred} for speed {speed} with a={a} and b={b}")
                pred = 0.5

            predictions.append(pred)
        
        #print(f"Reset counter: {reset_counter}")

        return predictions
    


    # interval creation
    def create_intervals(self, speed):
        binning_method = self.binning_method
        interval_params = self.interval_params

        if binning_method == 'fixed':
            lowers = interval_params[:-1]
            uppers = interval_params[1:]

        elif binning_method == 'equal_width':
            width = interval_params
            lowers = np.arange(0, 20, width)
            uppers = np.arange(width, 20 + width, width)
            lowers, uppers = self.check_intervals(lowers, uppers, speed, min_points=30)

        elif binning_method == 'equal_freq':
            freq = interval_params
            sorted_speed = np.sort(speed)
            n = len(sorted_speed)
            indexes = np.arange(0, n, freq)
            indexes[-1] = n - 1
            lowers = sorted_speed[indexes[:-1]]
            uppers = sorted_speed[indexes[1:]]
        
        elif binning_method == 'moving_window':
            width, overlap = interval_params
            lowers = np.arange(0, 20, overlap)
            uppers = np.arange(width, 20 + width, overlap)
            lowers, uppers = self.check_intervals(lowers, uppers, speed)

        self.intervals = (lowers, uppers)

        return

    # check intervals and merge if not enough data points
    def check_intervals(self, lowers, uppers, speed, min_points=30):
        i = 0
        while i < len(lowers):
            lower = lowers[i]
            upper = uppers[i]
            count = np.sum((speed >= lower) & (speed < upper))

            if count < min_points:
                if i < len(lowers) - 1:
                    uppers[i] = uppers[i + 1]
                    lowers = np.delete(lowers, i + 1)
                    uppers = np.delete(uppers, i + 1)
                else:
                    # backwards merge
                    uppers[i - 1] = upper
                    lowers = np.delete(lowers, i)
                    uppers = np.delete(uppers, i)
                    i -= 1
            else:
                i += 1

        # last check
        for i in range(len(lowers)):
            lower = lowers[i]
            upper = uppers[i]
            count = np.sum((speed >= lower) & (speed < upper))
            assert count >= min_points, f"Interval ({lower} to {upper}) has only {count} points."

        return lowers, uppers
    

    # helpers for scikit-learn compatibility
    def get_params(self, deep=True):
        return {
            'binning_method': self.binning_method,
            'interval_params': self.interval_params,
            'spline_k': self.spline_k,
            'spline_s': self.spline_s,
            'smoothing_factor': self.smoothing_factor,
            'drift_factor': self.drift_factor,
            'reset_prev_w': self.reset_prev_w
        }
    
    def get_var(self, var_name):
        return getattr(self, var_name, None)
    
    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self
    

    def score(self, X, y):
        preds = self.predict(X)
        mse = mean_squared_error(y, preds)
        return -mse  # return negative MSE for minimization