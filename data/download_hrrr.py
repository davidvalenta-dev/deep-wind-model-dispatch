# downloads and processes HRRR wind speed data for Pyron Wind Farm using Herbie package
from herbie import Herbie
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import time


def get_wind_speed(H):
    # only get UGRD and VGRD at 80 m above the ground
    df_u = H.xarray("UGRD:80 m above ground").to_dataframe()
    df_v = H.xarray("VGRD:80 m above ground").to_dataframe()

    # location of the closest coords to pyron
    sub_u = df_u.iloc[560289]
    sub_v = df_v.iloc[560289]

    # double check if latitude and longitude are good
    if not (np.isclose(sub_u['latitude'], 32.580306, atol=1e-6) and
        np.isclose(sub_u['longitude'], 259.340082, atol=1e-6) and
        np.isclose(sub_v['latitude'], 32.580306, atol=1e-6) and
        np.isclose(sub_v['longitude'], 259.340082, atol=1e-6)):

        try: # try to find a fallback coords that are close enough
            sub_u = df_u[(df_u['latitude'] > 32.5686) & (df_u['latitude'] < 32.6086) & 
                (df_u['longitude'] > 259.3072) & (df_u['longitude'] < 259.3472)].iloc[0]
            sub_v = df_v[(df_v['latitude'] > 32.5686) & (df_v['latitude'] < 32.6086) & 
                (df_v['longitude'] > 259.3072) & (df_v['longitude'] < 259.3472)].iloc[0]
        except IndexError:
            print(f"Skipping {date}, no data found for specified coordinates")
            date += timedelta(hours=1)
            return None
    
    speed = (sub_u['u']**2 + sub_v['v']**2)**0.5

    new_row = pd.Series({
        'datetime': sub_u['valid_time'],
        'latitude': sub_u['latitude'],
        'longitude': sub_u['longitude'],
        'u': sub_u['u'],
        'v': sub_v['v'],
        'speed': speed
    })

    return new_row


DELAY = 0.5
SAVE_EVERY = 1000 # save backup csv every 1000 rows


if __name__ == "__main__":
    original_stdout = sys.stdout

    num = 1
    i = 0

    # save print logs
    with open(f'data/processed/hrrr/hrrr_logs_{num}.txt', 'w') as f:
        sys.stdout = f

        # hrrr starts recording at 7/30/14 18:00 UTC
        start_date = datetime(2014, 7, 30, 18)
        end_date = datetime(2025, 7, 20, 23)
        date = start_date

        df = pd.DataFrame(columns=['datetime', 'latitude', 'longitude', 'u', 'v', 'speed'])

        while date <= end_date:
            success = False

            try:
                H = Herbie(
                    date,
                    model="hrrr",
                    product="nat",
                    fxx=0,
                )
                f.flush() # update logs immediately
                H.inventory()  # check if the data is available
                new_row = get_wind_speed(H)
                if new_row is not None:
                    df.loc[len(df)] = new_row
                    i += 1
                    success = True

            except Exception as e:
                time.sleep(DELAY)

            if not success:
                # fallback to previous hours with future forecasts, try up to 2 back
                for fxx in range(1, 3):
                    try:
                        H = Herbie(
                            date - timedelta(hours=fxx),
                            model="hrrr",
                            product="nat",
                            fxx=fxx,
                        )
                        f.flush()  # update logs immediately
                        H.inventory()  # check if the data is available
                        new_row = get_wind_speed(H)
                        if new_row is not None:
                            df.loc[len(df)] = new_row
                            i += 1
                            success = True
                    except Exception as e:
                        pass
                
                    if success:
                        break
            
            if i % SAVE_EVERY == 0:
                df.to_csv(f'data/processed/hrrr/hrrr_speeds_{num}_backup.csv', index=False)
                print(f"Saved {i} rows")

            date += timedelta(hours=1)

    
    sys.stdout = original_stdout  # reset system output


    print(df.head())
    print(df.tail())

    df.to_csv(f'data/processed/hrrr/hrrr_speeds_{num}.csv', index=False)
