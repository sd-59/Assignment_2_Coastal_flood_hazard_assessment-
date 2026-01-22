'''This script downloads and constructs a csv file of hourly water levels in the 'NOAA Tides and Currents' dataset based on user defined start and end years. 
LT 2022
'''

import os
import requests
import pandas as pd
import csv
import time
import numpy as np
import datetime

def process_API_request(year, station_id, datum='MSL'):
    '''This function generates the URL and performs and processes the API request. 
    Args:
        year (int): The year for which to request data
        station_id (int): The station id to request the data from
        datum (str): vertical reference datum, by default MSL
    
    Returns:
        df (pandas dataframe): The data retrieved from the API request'''

    # Construct URL and do the API request
    start_string = f'begin_date={year}0101'
    end_string = f'end_date={year}1231'
    station_string = f'station={station_id}'
    url = f'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?{start_string}&{end_string}&{station_string}&product=hourly_height&datum={datum}&time_zone=gmt&units=metric&format=csv'
    response = requests.get(url=url)
    
    # Allow time for download
    # time.sleep(1)
    print(f'Downloaded year {year}')
    
    # Process response and convert to pandas dataframe
    decoded_content = response.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    data = list(cr)
    df = pd.DataFrame(data[1:], columns=data[0])

    
    # Check if data is found. If year is missing fill with NaN.
    error_message = 'Error: No data was found. This product may not be offered at this station at the requested time.'
    if df.iloc[0].name == error_message:
        print(f'Year {year}: {error_message}')
        df['Date Time'] = f'{year}-01-01 00:00'
        df = df.set_index('Date Time', drop=True)
        for col in df.columns:
            df[col].iloc[0] = np.nan    

    # missing observations to nan
    df = df.replace('', np.nan)      

    return df   

def download_data(fn, station_id, start_year, end_year, datum='MSL'):
    '''This function iterates over the years defined by the user and retrieves the data.
    Args:
        fn (str): filename to save output csv
        station_id (int): The station id to request the data from
        start_year (int): First year from which to request data
        end_year (int): Last year from which to request data
        datum (str): vertical reference datum, by default MSL
        backward_compatible (bool): If True, the output csv file will be formatted in the same way as the csv files used in previous years of the course.
    Retruns:
        export_data (pandas dataframe): The data retrieved from the API request in csv format.'''
    os.makedirs(os.path.dirname(fn), exist_ok=True)

    # initiate response dictionary
    retrieved_data = {}
    
    # iterate over years defined by user and retrieve data8531680 
    for year in np.arange(start_year, end_year+1, dtype=np.int32):   
        retrieved_data[year] = process_API_request(year, station_id, datum=datum)
    
    # now iterate over retrieved data to merge datasets
    df = pd.concat(retrieved_data.values())
    df = df.rename(columns={' Water Level': 'waterlevel', 'Date Time': 'datetime'})
    df = df.set_index('datetime', drop=True).sort_index()
    drop_cols = [col for col in df.columns if col != 'waterlevel']
    df = df.drop(drop_cols, axis=1, errors='ignore')

    df.to_csv(fn)
    print(f'data stored to {fn}')

    return df


if __name__ == '__main__':
    print('Busy...') 
    station_id = 8534720
    download_data(
        fn = f'./hourly_water_levels_{station_id}.csv',
        station_id = station_id,
        start_year = 2021,  
        end_year = 2022
    )

    print('Done')