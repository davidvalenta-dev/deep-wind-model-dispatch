import numpy as np

# Abstract storage class 
class Storage:  
    def get_ratings(self):
        return self.ratings

    def get_durations(self):
        return self.durations
    
    def get_rte(self, rating, duration):
        return self.rtes[self.get_rating_index(rating), self.get_duration_index(duration)][0]
    
    def get_capex(self, rating, duration):
        return self.capex[self.get_rating_index(rating), self.get_duration_index(duration)][0]

    def get_opex(self, rating, duration):
        return self.opex[self.get_rating_index(rating), self.get_duration_index(duration)][0]
    
    def get_rating_index(self, rating):
        return np.where(self.ratings == rating)[0]
    
    def get_duration_index(self, duration):
        return np.where(self.durations == duration)[0]

class BatteryLI(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/lithium-ion-battery
        self.ratings = np.array([1, 10, 100, 1000])
        self.durations = np.array([2, 4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.83, 0.83, 0.83, 0.83, 0.83, 0.83, 0.83],
                              [0.83, 0.83, 0.83, 0.83, 0.83, 0.83, 0.83],
                              [0.83, 0.83, 0.83, 0.83, 0.83, 0.83, 0.83],
                              [0.83, 0.83, 0.83, 0.83, 0.83, 0.83, 0.83]])
        # indexed by [rating, duration]
        self.capex = np.array([[1040.88, 1841.72, 2648.46, 3453.84, 4256.60, 9840.96, 39754.00],
                  [904.44, 1618.62, 2350.83, 3070.57, 3793.15, 8815.37, 35696.05],
                  [846.01, 1490.89, 2158.16, 2823.31, 3490.67, 8120.59, 32913.67],
                  [787.51, 1406.11, 2036.53, 2672.06, 3311.12, 7727.58, 29945.62]])
        self.opex = np.array([[3.17, 5.47, 6.98, 8.76, 10.59, 23.30, 90.47],
                 [2.79, 4.59, 6.37, 8.12, 9.87, 21.98, 85.98],
                 [2.56, 4.27, 5.96, 7.63, 9.33, 20.84, 81.82],
                 [2.37, 3.99, 5.63, 7.21, 8.79, 19.78, 77.88]])
        
class CAES(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/compressed-air-energy-storage
        self.ratings = np.array([100, 1000])
        self.durations = np.array([4, 10, 24, 100])
        self.rtes = np.array([[0.55, 0.55, 0.55, 0.55],
                             [0.55, 0.55, 0.55, 0.55]])
        # indexed by [rating, duration]
        self.capex = np.array([[1090.24, 1125.33, 1207.53, 1637.13],
                       [992.93, 1025.37, 1101.30, 1497.66]])
        self.opex = np.array([[17.02, 15.43, 14.88, 16.50],
                       [9.35, 9.18, 9.13, 9.28]])

class Hydro(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/pumped-storage-hydropower
        self.ratings = np.array([100, 1000])
        self.durations = np.array([4, 10, 24, 100])
        self.rtes = np.array([[0.80, 0.80, 0.80, 0.80],
                             [0.80, 0.80, 0.80, 0.80]])
        # indexed by [rating, duration]
        self.capex = np.array([[2703.26, 2786.84, 2950.29, 3415.97],
                        [2011.66, 2019.89, 2154.67, 3179.96]])
        self.opex = np.array([[27.21, 27.21, 27.21, 27.21],
                        [14.62, 14.62, 14.62, 14.62]])

class BatteryLA(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/lead-acid-battery
        self.ratings = np.array([1, 10, 100, 1000])
        self.durations = np.array([2, 4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.77, 0.77, 0.78, 0.79, 0.79, 0.79, 0.80],
                             [0.77, 0.77, 0.78, 0.79, 0.79, 0.79, 0.80],
                             [0.77, 0.77, 0.78, 0.79, 0.79, 0.79, 0.80],
                             [0.77, 0.77, 0.78, 0.79, 0.79, 0.79, 0.80]])
        # indexed by [rating, duration]
        self.capex = np.array([[1140.07, 1984.73, 2832.67, 3659.37, 4489.13, 10229.05, 40634.93],
                               [1028.17, 1832.63, 2629.93, 3423.71, 4228.25, 9667.39, 38498.15],
                               [957.58, 1723.50, 2483.42, 3241.70, 3993.20, 9190.10, 36461.10],
                               [896.89, 1622.89, 2348.03, 3070.25, 3782.53, 8725.13, 34872.33]])
        self.opex = np.array([[3.96, 6.11, 8.24, 10.36, 12.46, 26.99, 103.69],
                              [2.80, 4.46, 6.10, 7.71, 9.32, 20.46, 79.27],
                              [2.98, 4.80, 6.60, 8.39, 10.17, 22.44, 87.28],
                              [2.75, 4.49, 6.20, 7.90, 9.59, 21.26, 82.89]])
        
class BatteryVRF(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/vanadium-redox-flow-battery
        self.ratings = np.array([1, 10, 100, 1000])
        self.durations = np.array([2, 4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65],
                             [0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65],
                             [0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65],
                             [0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65]])
        # indexed by [rating, duration]
        self.capex = np.array([[2311.98, 3240.52, 4308.08, 4923.12, 5609.40, 11705.80, 44902.80],
                               [2026.41, 2875.91, 3828.66, 4389.08, 5047.20, 10634.78, 41003.67],
                               [1818.21, 2599.45, 3420.59, 3846.21, 4462.31, 9469.28, 36568.08],
                               [1725.13, 2469.43, 3248.67, 3652.63, 4238.31, 8679.60, 34739.98]])
        self.opex = np.array([[5.65, 7.52, 9.40, 11.30, 13.19, 26.48, 98.58],
                              [4.85, 6.67, 8.47, 10.27, 12.82, 24.73, 93.45],
                              [4.44, 6.16, 7.88, 9.59, 11.39, 23.33, 88.57],
                              [4.24, 5.87, 7.55, 9.13, 10.76, 22.18, 84.16]])
        
class Zinc(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/zinc
        self.ratings = np.array([1, 10])
        self.durations = np.array([2, 4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.79, 0.74, 0.73, 0.70, 0.70, 0.69, 0.69],
                            [0.72, 0.69, 0.73, 0.70, 0.70, 0.69, 0.69]])
        # indexed by [rating, duration]
        self.capex = np.array([[1312.14, 2157.48, 2505.44, 3692.88, 4756.60, 10797.92, 41458.60],
                               [1172.31, 1866.89, 2278.63, 3736.81, 4491.11, 10564.33, 45663.61]])
        self.opex = np.array([[6.85, 15.96, 1.40, 11.15, 11.77, 27.65, 61.65],
                              [10.56, 21.98, 16.52, 11.06, 11.68, 27.56, 61.56]])

class Hydrogen(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/hydrogen-bi-directional
        self.ratings = np.array([100, 1000])
        self.durations = np.array([10, 24, 100])
        self.rtes = np.array([[0.31, 0.31, 0.31],
                            [0.31, 0.31, 0.31]])
        # indexed by [rating, duration]
        self.capex = np.array([[2953.69, 3033.37, 3446.69],
                               [2948.99, 3022.33, 3400.69]])
        self.opex = np.array([[23.21, 23.90, 27.47],
                              [16.89, 17.52, 20.79]])
        
class Gravitational(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/gravitational
        self.ratings = np.array([100, 1000])
        self.durations = np.array([2, 4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.83, 0.83, 0.83, 0.83, 0.83, 0.83, 0.83],
                            [0.84, 0.84, 0.84, 0.84, 0.84, 0.84, 0.84]])
        # indexed by [rating, duration]
        self.capex = np.array([[2232.46, 2925.70, 3504.98, 4103.14, 4549.24, 7601.06, 20172.34],
                               [1325.18, 1706.52, 2045.06, 2359.88, 2664.20, 4559.00, 13121.20]])
        self.opex = np.array([[21.60, 22.80, 23.89, 25.06, 26.22, 34.37, 78.60],
                              [13.12, 14.28, 15.44, 16.61, 17.77, 25.92, 70.15]])
        
class Thermal(Storage):
    def __init__(self):
        # These estimates are all sourced from 2023 PNNL data at the following: https://www.pnnl.gov/projects/esgc-cost-performance/thermal
        self.ratings = np.array([100, 1000])
        self.durations = np.array([4, 6, 8, 10, 24, 100])
        self.rtes = np.array([[0.48, 0.48, 0.50, 0.50, 0.48, 0.47],
                            [0.46, 0.47, 0.49, 0.50, 0.48, 0.47]])
        # indexed by [rating, duration]
        self.capex = np.array([[2509.17, 2761.02, 2806.51, 3024.94, 4053.34, 8088.29],
                               [1552.93, 1844.78, 1925.92, 2094.31, 3079.24, 6906.02]])
        self.opex = np.array([[30.65, 31.26, 32.17, 37.26, 47.69, 102.08],
                              [20.09, 19.91, 20.52, 25.24, 35.86, 88.94]])
