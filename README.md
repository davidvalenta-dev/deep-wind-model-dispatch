# wind-energy-forecasting

## Setting up the environment
In order to simplify package management, create and activate a new virtual environment with the following command in the root directory:
```
python -m venv venv
source ./venv/bin/activate
```
Then install required packages to this virtual environment using the requirements listed in ```requirements.txt```:
```
pip install -r requirements.txt
```
Whenever you run code in this repository, be sure you're doing so using the activated virtual environment.

## Dataset Specifications
TODO

## Downloading custom ERA5 data
If you need ERA5 data that is not included in the dataset used in this repository (see specifications above), you can use the script at ```src/download_era5.py``` as a reference for using the CDS API to download ERA5 data. Follow the instructions at https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download for information on how to generate download scripts with the CDS API, and see the instructions at https://cds.climate.copernicus.eu/how-to-api for information on how to use the CDS API. 