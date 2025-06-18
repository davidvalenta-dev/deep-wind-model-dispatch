import cdsapi

# WARNING: ---------------------------------
# Don't run this unless you want to change it in order to download a different dataset 
# than the one contained in this repository.

# This is included for reproducibility purposes and the data that would be downloaded by this request 
# is already formatted into a more workable .csv and .npy file that is used by other code in this repository.

dataset = "reanalysis-era5-single-levels"
request = {
    "product_type": ["reanalysis"],
    "year": [
        "2020", "2021", "2022",
        "2023", "2024"
    ],
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "01:00", "02:00",
        "03:00", "04:00", "05:00",
        "06:00", "07:00", "08:00",
        "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00",
        "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00",
        "21:00", "22:00", "23:00"
    ],
    "data_format": "grib",
    "download_format": "zip",
    "variable": [
        "100m_u_component_of_wind",
        "100m_v_component_of_wind"
    ],
    "area": [32.75, -100.80, 32.5, -100.55]
}

client = cdsapi.Client()
client.retrieve(dataset, request).download()
