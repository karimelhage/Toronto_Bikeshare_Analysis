import requests
import json
import pandas as pd
import glob
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import re


def extract_bike_stations():
    """
    Function to extract Toronto bike sharing system info
    :return: None
    """

    # Information to script
    r = requests.get('https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information')

    # Get station data
    bikeshare_stations = json.loads(r.content)['data']['stations']

    # Map data to Dataframe relevant columns
    bikeshare_stations = pd.DataFrame(bikeshare_stations)[['station_id', 'name', 'lat', 'lon', 'address',
                                                           'nearby_distance','rental_methods',
                                                           'capacity','_ride_code_support', 'is_charging_station']].astype({'station_id': 'int64' })

    # Save data as csv
    bikeshare_stations.to_csv('../data/raw/bikeshare_stations.csv', index=False)


def clean_payment_methods(word_list):
    """
    Fucntion to clean the type of payment methods available at a bike station
    :param word_list: list of bike stations
    :return: list - cleaned list of bike stations
    """

    # convert string of list into list
    return [y for x in [word.split("'") for word in word_list[1:-1].split(',')] for y in x if y not in ['', ' ']]


def one_hot_encode_payment_methods(bike_share_df):
    """
    Function to one-hot encode payment methods at stations
    :param bike_share_df: dataframe with stations
    :return: pd.DataFrame- stations ataframe with one hot encoded payment methods
    """
    df = bike_share_df.copy()

    # clean payment methods
    df['rental_methods'] = df['rental_methods'].apply(clean_payment_methods)

    # Get all unique words from the 'rental_methods' column
    unique_words = set([word for words_list in df['rental_methods'] for word in words_list])

    # Create a new DataFrame with one-hot encoded columns
    one_hot_encoded = pd.DataFrame()
    for word in unique_words:
        one_hot_encoded[word] = df['rental_methods'].apply(lambda x: True if word in x else False)

    one_hot_encoded.columns = ['rent_key', 'rent_phone', 'rent_transit_card', 'rent_credit_card']

    # Concatenate the original DataFrame with the one-hot encoded DataFrame
    df = pd.concat([df, one_hot_encoded], axis=1)

    df.drop(columns=['rental_methods'], inplace=True)

    return df


def concat_bike_data():
    """
    Function to concat different raw data sources of bike trip data with different column names etc
    :return: pd.DataFrame - containing all trips from 2017 - 2022
    """
    # Assign columns to drop pre 2019
    old_drop = ['from_station_name', 'to_station_name', 'trip_duration_seconds']

    # Assign columns to drop post 2019
    new_drop = ['Start Station Name', 'End Station Name', 'Trip  Duration']

    # Assign column names to map pre-2019
    old_mapping = {'trip_id': 'trip_id', 'from_station_id': 'start_station_id',
                   'trip_start_time': 'start_time', 'trip_stop_time': "end_time",
                   'to_station_id': "end_station_id", 'user_type': "user_type"}

    # Assign column name to map post 2019
    new_mapping = {'Trip Id': 'trip_id', 'Start Station Id': 'start_station_id', 'Start Time': 'start_time',
                   'End Station Id': 'end_station_id', 'End Time': 'end_time', 'User Type': 'user_type',
                   'Bike Id': 'bike_id'}

    # Assign order of columns
    column_order = ['trip_id', 'user_type', 'start_station_id', 'start_time', 'end_station_id', 'end_time']

    # Assign mappings to relevant years
    map_dict = {}
    for i, year in enumerate(['2017', '2018', '2019', '2020', '2021', '2022']):
        if i < 2:
            map_dict[year] = {"drop": old_drop, "mapping": old_mapping}
        else:
            map_dict[year] = {"drop": new_drop, "mapping": new_mapping}

    # Extract file names for 2018-2019
    trip_path_list_2017 = sorted(glob.glob('../data/raw/bikeshare_trip-data_2017-2019/*'))

    for i, path in enumerate(trip_path_list_2017):
        print(path)
        year = path.split('/')[-1].split('-')[0]
        if i == 0:
            df_trips = pd.read_csv(path).drop(columns=map_dict[year]['drop']) \
                .rename(columns=map_dict[year]['mapping'])[column_order]
            df_trips['bike_id'] = 0
        else:
            temp = pd.read_csv(path).drop(columns=map_dict[year]['drop']) \
                .rename(columns=map_dict[year]['mapping'])[column_order]

            if i < 4:
                temp['bike_id'] = 0
                if i == 3:
                    column_order = column_order + ['bike_id']
            else:
                temp['bike_id'] = temp['bike_id'].astype('int')

            df_trips = pd.concat([df_trips, temp], axis=0)
            temp = pd.DataFrame()

    # Get path of monthly data 2020 - 2022
    trip_path_list_2020 = sorted(glob.glob('../data/raw/bikeshare_trip-data_2020-2022/*'))

    # Get Combine monthly data into one csv
    for i, path in enumerate(trip_path_list_2020):
        print(path)
        year = path.split('/')[-1].split(' ')[-1].split('-')[0]

        temp = pd.read_csv(path).drop(columns=map_dict[year]['drop']) \
            .rename(columns=map_dict[year]['mapping'])[column_order]

        df_trips = pd.concat([df_trips, temp], axis=0)
        temp = pd.DataFrame()

    return df_trips


def clean_trip_data(df, save=False):
    """
    Function to clea the bike trip data and remove potential "fake" trips
    :param df: pd.DataFrame - dataframe with all bike share trips
    :param save: bool - If True, saves cleaned dataframe
    :return: pd.DataFrame - DataFrame with cleaned information and columns
    """
    # reset index
    df = df.reset_index()

    # remove index column
    df = df[df.columns[1:]]

    #downcast trip id for memory
    df.trip_id = df.trip_id.apply(pd.to_numeric, downcast='integer')

    # Remove na user types as these are fields where full row improperly stored
    df = df[~df.user_type.isna()]

    # Remove rows with empty end station ids and there is no station name to trace these locations
    df = df[~df.end_station_id.isna()]

    # Convert string  station id to int and downcast
    df.start_station_id = df.start_station_id.astype('int').apply(pd.to_numeric, downcast='integer')
    df.end_station_id = df.end_station_id.astype('int').apply(pd.to_numeric, downcast='integer')
    # df.bike_id = df.bike_id.astype('int').apply(pd.to_numeric, downcast='integer')
    # convert time to datetime
    df.start_time = pd.to_datetime(df.start_time)
    df.end_time = pd.to_datetime(df.end_time)

    # Create trip duration
    df['duration'] = (df.end_time - df.start_time).dt.total_seconds()/60
    df.drop(columns=['end_time'], inplace=True)

    # Remove trips with durations less than 1 minute as likely started incorrectly
    df = df[df.duration * 60 > 60]

    # remove trips with durations longer than an hour as likely started incorrectly and are outliers
    df = df[df.duration < 60]

    # Sort df
    df = df.sort_values('start_time', ascending=False)

    if save:
        df.to_csv('../data/processed/bikeshare_trips.csv', index=False)

    return df


def fetch_weather_data(station_id=51459, start_year=2017, end_year=2022):
    """
    Fetches Canadian Daily weather data of specified weather station and saves each year as csv
    :param station_id: int - the id of the Canandian weather station, by default Toronto Airport (YYZ)
    :param start_year: int - start year of collection
    :param end_year: int - end year of collection
    :return: None
    """
    # Iterate over the years and months
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Construct the URL for the data file
            url = f"https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID={station_id}&Year={year}&Month={month}&Day=1&timeframe=2&submit=Download+Data"

            # Send a request to download the file
            response = requests.get(url)

            # Save the file with the specified naming convention
            filename = f"{station_id}_{year}_{month:02d}_daily.csv"
            with open(filename, 'wb') as file:
                file.write(response.content)

            print(f"Downloaded data for {year}-{month:02d}")


def concat_weather_data():
    """
    concat yearly weather data
    :return: pd.DataFrame - cleaned dataframe
    """
    # Get weather paths
    paths = sorted(glob.glob('../data/raw/toronto_weather/*'))

    for i, path in enumerate(paths):

        # Fetch only one month of year since a month actually stores full year of data
        if i % 12 == 0:
            if i == 0:
                # Keep only relevant information
                df = pd.read_csv(path)[['Date/Time', 'Mean Temp (°C)', 'Total Rain (mm)',
                                        'Total Snow (cm)', 'Spd of Max Gust (km/h)']]
            else:
                df = pd.concat([df, pd.read_csv(path)[['Date/Time', 'Mean Temp (°C)', 'Total Rain (mm)',
                                                       'Total Snow (cm)', 'Spd of Max Gust (km/h)']]], axis=0)

    return df


def clean_weather_data(df_weather):

    """
    Function to clean weather data
    :param df_weather: pd.DataFrame - uncleaned weather data
    :return: pd.DataFrame - cleaned weather data
    """

    # Rename columns
    df_weather = df_weather.rename(
        columns={'Date/Time': 'date', 'Mean Temp (°C)': 'mean_temp', 'Total Rain (mm)': 'total_rain',
                 'Total Snow (cm)': 'total_snow', 'Spd of Max Gust (km/h)': 'max_gust'})

    # Fill <31 km/h with 29 km/h
    df_weather.max_gust[df_weather.max_gust == '<31'] = '29'

    # Convert max_gust to float
    df_weather.max_gust = df_weather.max_gust.astype('float')

    # Interpolate missing values for total_rain, mena_temp, total_snow since only 1% missing
    df_weather.total_rain = df_weather.total_rain.interpolate(method='linear')
    df_weather.mean_temp = df_weather.mean_temp.interpolate(method='linear')
    df_weather.total_snow = df_weather.total_snow.interpolate(method='linear')


    # categorize gusts based on beaufor scale as per http://www.greenmansoftware.co.uk/products/fieldnotes/documentation/answers/measurements/beaufort.htm
    df_weather['gust_type'] = np.nan
    df_weather.gust_type[(df_weather.gust_type.isna()) & (df_weather.max_gust < 30)] = 'Moderate'
    df_weather.gust_type[(df_weather.gust_type.isna()) & (df_weather.max_gust < 50)] = 'Breezy'
    df_weather.gust_type[(df_weather.gust_type.isna()) & (df_weather.max_gust < 89)] = 'Galey'
    df_weather.gust_type[(df_weather.gust_type.isna()) & (df_weather.max_gust < 118)] = 'Stormy'
    df_weather.gust_type[(df_weather.gust_type.isna()) & (df_weather.max_gust >= 118)] = 'Hurricane'

    # add column with city_id
    df_weather['city_id'] = [0] * len(df_weather)

    return df_weather


def clean_accidents(df_accidents, neighborhoods_gdf):

    # Keep only data in 2017
    df_accidents = df_accidents[df_accidents.YEAR.astype('int') > 2016]

    # Keep only relevant columns
    df_accidents = df_accidents[['DATE', 'LATITUDE', 'LONGITUDE', 'LIGHT', 'ACCLASS',
                                 'INVTYPE', 'INJURY', 'CYCLISTYPE',
                                 'CYCACT']]

    # Lower case column names
    df_accidents.columns = [col.lower() for col in df_accidents.columns]

    # Fill values missing values where should be fatal injusry
    df_accidents.injury[df_accidents.acclass == 'Fatal'] = 'Fatal'

    # covert date/time to datetime
    df_accidents.date = pd.to_datetime(df_accidents.date).dt.date

    # Create Point geometries for accidents
    accidents_points = [Point(lon, lat) for lon, lat in zip(df_accidents.longitude, df_accidents.latitude)]

    # Create a GeoDataFrame for accidents
    accidents_gdf = gpd.GeoDataFrame(df_accidents, geometry=accidents_points)

    # Perform spatial join to link accidents with neighborhoods
    accidents_with_neighborhoods = gpd.sjoin(accidents_gdf, neighborhoods_gdf, how='left', op='within')

    accidents_with_neighborhoods = accidents_with_neighborhoods[list(accidents_gdf.columns) + ['AREA_SHORT_CODE']].rename(columns={'AREA_SHORT_CODE': 'ward_id'})

    return accidents_with_neighborhoods


def clean_neighbors(neighborhoods_gdf):
    """
    Function to clean neighborhoods
    :param neighborhoods_gdf: gpd.GeoDataFrame - raw Geo Dataframe of neighborhoods
    :return: gpd.GeoDataFrame - cleaned dataframe
    """

    # drop columns not to be used
    neighborhoods_gdf.drop(columns=['AREA_ATTR_ID', '_id',
                                    'AREA_LONG_CODE', 'AREA_DESC', 'CLASSIFICATION', 'CLASSIFICATION_CODE'],
                           inplace=True)

    # lower case rename columns
    neighborhoods_gdf.columns = [col.lower() for col in neighborhoods_gdf.columns]
    neighborhoods_gdf.rename(columns={'area_short_code': 'neighborhood_id', 'parent_area_id': 'city_id'}, inplace=True)

    ## add city id
    neighborhoods_gdf.city_id = 0

    # convert id to int
    neighborhoods_gdf.neighborhood_id = neighborhoods_gdf.neighborhood_id.astype('int')

    # clean neighborhood name
    neighborhoods_gdf.area_name = neighborhoods_gdf.area_name.apply(lambda x: re.sub(r'\s*\([^()]*\)', '', x))

    # add city name
    neighborhoods_gdf.city_id = [0] * len(neighborhoods_gdf)

    return neighborhoods_gdf

def clean_stations(stations_data, df_trips,neighborhoods_gdf):
    """
    Function to clean stations data and use geo-spatial info to determine the neighborhood of stations
    :param stations_data: pd.DataFrame - raw station data
    :param df_trips: pd.DataFrame - dataframe containing the bike trips
    :return: None
    """



    neighborhoods_gdf.drop(columns=['AREA_ATTR_ID', '_id',
                                    'AREA_LONG_CODE', 'AREA_DESC'],
                           inplace=True)

    neighborhoods_gdf.columns = [col.lower() for col in neighborhoods_gdf.columns]
    neighborhoods_gdf.rename(columns={'area_short_code': 'ward_id', 'parent_area_id': 'city_id'}, inplace=True)
    neighborhoods_gdf.city_id = 0
    neighborhoods_gdf.ward_id = neighborhoods_gdf.ward_id.apply(lambda x: int(x))
    neighborhoods_gdf.area_name = neighborhoods_gdf.area_name.apply(lambda x: re.sub(r'\s*\([^()]*\)', '', x))

    # one hot encode payment methods
    stations_data = one_hot_encode_payment_methods(stations_data)

    # Create Point geometries for stations
    station_points = [Point(lon, lat) for lon, lat in zip(stations_data.lon, stations_data.lat)]

    # Create a GeoDataFrame for stations
    stations_gdf = gpd.GeoDataFrame(stations_data, geometry=station_points)

    # Perform spatial join to link stations with neighborhoods
    stations_with_neighborhoods = gpd.sjoin(stations_gdf, neighborhoods_gdf, how='left', op='within')

    # Keep pertinent columns
    df_stations = stations_with_neighborhoods[list(stations_gdf.columns) + ['ward_id']]

    # Get first trip from start/end station
    df_grouped = df_trips.groupby('start_station_id').agg({'start_time':'min'})
    df_grouped2 = df_trips.groupby('end_station_id').agg({'start_time':'min'})

    # Merge these first trips to the stations
    df_stations = df_stations.merge(df_grouped, how = 'left', left_on = 'station_id', right_index = True)
    df_stations = df_stations.merge(df_grouped2, how = 'left', left_on = 'station_id', right_index = True)

    # Remove stations that do not have a start/end station date
    df_stations = df_stations[~((pd.isna(df_stations.start_time_x) & (pd.isna(df_stations.start_time_x))))]

    # Create a new column 'first use' that stores the first time a trip was made to/from this station
    df_stations['first_use'] = np.nan
    df_stations.first_use[pd.isna(df_stations.start_time_x)] = df_stations.start_time_y[pd.isna(df_stations.start_time_x)]
    df_stations.first_use[pd.isna(df_stations.start_time_y)] = df_stations.start_time_x[pd.isna(df_stations.start_time_y)]
    df_stations.first_use[df_stations.first_use.isna()] = df_stations[['start_time_x','start_time_y']][df_stations.first_use.isna()].min(axis = 1)

    # Drop start time columns and keep date part of datetime
    df_stations.drop(columns = ['start_time_x','start_time_y'], inplace = True)
    df_stations.first_use = pd.to_datetime(df_stations.first_use).dt.date

    # keep pertinent columns
    df_stations = df_stations[['station_id', 'name', 'lat', 'lon', 'address','capacity','ward_id', 'first_use']]

    # Save station data
    df_stations.to_csv('../data/processed/bikeshare_stations.csv', index=False)


def clean_pop(df):
    """

    :param df:
    :return:
    """
    # Drop neighborhood name
    df.drop(columns=['Neighbourhood'], inplace=True)

    # Change column names
    df.rename(columns={'Neighbourhood Id': 'neighborhood_id',
                       'Total Population': 'total_population'}, inplace=True)

    # change id to int
    df.neighborhood_id = df.neighborhood_id.astype('int')

    # add column for year 2016 of population census
    df['year'] = [2016] * len(df)

    return df


def clean_wards(df_wards, df_ward_geo, save=False):
    """
    Function to add population and area to wards and geolocation and covert the ward id in geo file to int
    :param df_wards: pd.DataFrame
    :param df_ward_geo: gdp.GeoDataFrame
    :param save: bool
    :return: pd.DataFrame, gdp.GeoDataFrame
    """
    # Rename ward columns
    df_wards = df_wards.rename(columns={'Ward Number': "ward_id", "Ward Name": "ward_name"})

    # Add ward population, area and city id
    df_wards['population'] = pd.read_excel('../data/raw/2018-ward-profiles-2011-2016-census-25-ward-model-data.xlsx', header=17).iloc[0].values[2:]
    df_wards['area'] = pd.read_excel('../data/raw/2018-ward-profiles-25-ward-model-geographic-areas.xlsx', header=11)['Area (sq km)']
    df_wards['city_id'] = 0

    # add median household income
    df_incomes = pd.read_excel('../data/raw/2018-ward-profiles-2011-2016-census-25-ward-model-income.xlsx', header=17)
    df_incomes = df_incomes.drop(15).set_index('Unnamed: 0')
    income_groups = list(df_incomes['Ward 1'].index)
    median_income = {}
    for ward in df_incomes.columns:
        temp = zip(income_groups, list(df_incomes[ward].values))
        incomes = []
        for pair in temp:
            incomes += [pair[0]] * pair[1]

        middle_index = (len(incomes) - 1) // 2
        middle_value = incomes[middle_index]
        median_income[ward] = middle_value

    df_wards['median_household_income'] = median_income.values()

    # Change ward geo-location column to integer and lower case column names
    df_ward_geo['AREA_SHORT_CODE'] = df_ward_geo['AREA_SHORT_CODE'].astype('int')

    # Save files if boolean True
    if save:
        df_wards.to_csv('../data/processed/toronto_wards.csv', index=False)
        df_ward_geo.to_file('../data/processed/toronto_wards.geojson', driver='GeoJSON')

    return df_wards, df_ward_geo



