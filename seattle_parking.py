# Seattle parking, TDI capstone
import pandas as pd
import numpy as np
import os
import sys

from functools import partial

# space needle location
SPACE_NEEDLE = (47.6205, -122.3493)

################################################################
# Data processing

station_astype = {
    'occupancydatetime': 'datetime64',
    'paidoccupancy': int,
    'parkingspacecount': int
}

def read_noaa_weather_data(fn='data/weather/seattle_weather.csv.gz'):
    """ Prepare weather information from csv file.

    Will NOT check if file exists
    """
    df = pd.read_csv(fn, low_memory=False).astype({'DATE':'datetime64'})
    #df.DATE = df.DATE.astype('datetime64')

    # aggregate by date
    daily = df.groupby('DATE')[['TMAX', 'TMIN', 'PRCP', 'SNOW', 'SNWD']].agg('median')
    return daily

def read_parking_data(fn='data/station_data/2012/11133.csv.gz'):
    """ Read station data from csv file. 

    Will NOT check if file exists """
    df = pd.read_csv(fn, low_memory=False).astype(station_astype).sort_values('occupancydatetime')
    return df        

def read_parking_data_multiyear(station, years, dir):
    """ Read multiple years data for <station>

    years: iterable

    dir: base directory for data. Full station data files dir/year/station.csv.gz

    Returns None if no data file found
    """

    dir = os.path.realpath(dir)
    files = [ os.path.join(dir, str(y), f'{station}.csv.gz') for y in years ]

    def check_path(p):
        if os.path.exists(p):
            return True
        print(f'File not found: {p}', file=sys.stderr)
        return None

    files = filter(check_path, files)

    dfs = [ read_parking_data(fn) for fn in files ]
    if dfs:
        return pd.concat(dfs)
    else:
        print(f'No available data for station {station}', file=sys.stderr)
        return None

def merge_station_weather(station,weather):
    """ merge weather data into station data """

    station_date = station.occupancydatetime.dt.date.astype('datetime64')
    return station.merge(weather, how='left', left_on = station_date, right_index=True)

def resample_parking_data(df, freq='5min', method='min'):
    """Resample the time axis of a station dataframe

    freq: frequency of resampling for the column <occupancydatetime>

    method: aggregation applied to <paidoccupancy>. A reasonable
    choice is 'min' since we only care about if a spot has /ever/ been
    available during that time window. 

    Returns a DataFrame that has the same structure as if returned from <read_parking_data>
    """

    g = pd.Grouper(key='occupancydatetime', freq=freq, origin='epoch')
    res = df.groupby(g).agg({
        'paidoccupancy': method,
        'parkingspacecount': 'max' # Just need a number. It should be a constant over the 5min
        }).reset_index().dropna()
    res.columns = ['occupancydatetime', 'paidoccupancy', 'parkingspacecount']
    return res


def read_station_coord(fn='data/Pay_Stations.csv'):
    """ Return a dataframe with columns ['sourceelementkey', 'lat',
    'long'] specifying coordinate of each station """
    
    res = pd.read_csv(fn)[['ELMNTKEY', 'SHAPE_LAT', 'SHAPE_LNG']]
    res.columns = ['sourceelementkey', 'latitude', 'longitude']
    return res

def read_station_space_time(fn='data/pay_station_time_limit_space_count.csv'):
    """Return a dataframe with columns ['sourceelementkey',
    'time_limit_min', 'time_limit_max', 'space_count']"""
    res = pd.read_csv(fn).astype(int)
    return res

def latlng_dist(locations, ref=None, r=3963):
    """distances from locations to a ref point on a sphere of radius
    <r>. Default of <r> is the radius of the Earth

    locations: list of (latitude,longitude) pairs
    ref: reference point. If None, then take locations[0]

    NB: latitude = 90 - theta, longitude = phi for polar angles (theta, phi)

    """

    lat,lng = (np.asarray(locations) / 180 * np.pi).T
    if ref:
        lat0, lng0 = np.asarray(ref) / 180 * np.pi
    else:
        lat0, lng0 = lat[0], lng[0]

    proj_ref = np.cos(lat) * np.cos(lat0) * np.cos(lng - lng0) + np.sin(lat) * np.sin(lat0) # dot product of all locations with ref point
    angles = np.arccos(proj_ref)

    return angles * r

def find_nearby_stations(location=SPACE_NEEDLE, within=0.3, coord_fn='data/Pay_Stations.csv', spacetime_fn='data/pay_station_time_limit_space_count.csv'):
    """ find parking stations within <within> miles of <location> """
    df = read_station_coord(coord_fn)
    df_st = read_station_space_time(spacetime_fn)
    df = pd.merge(left=df, right=df_st, left_on='sourceelementkey', right_on='elmntkey').drop('elmntkey', axis=1)
    dist = latlng_dist(df[['latitude', 'longitude']], location)
    df['dist'] = dist
    return df.iloc[dist <= within].sort_values('dist')

################################################################
# Learning

from sklearn.preprocessing import FunctionTransformer
def trig(func, period, as_transformer=False):
    """ currying a trignometric function with custom period

    returns a function f, such that f(x) = func(x / period * 2*pi)
    
    If as_transformer = True, then wrap it as a FunctionTransformer
    """
    def _trig(x, func, period):
        return func(x/period*2*np.pi)

    f = partial(_trig, func=func, period=period)
    if as_transformer:
        f = FunctionTransformer(f)
    return f

from sklearn.base import BaseEstimator, TransformerMixin
class TimeSplitter(BaseEstimator, TransformerMixin):
    """Split timestamps into separate columns of ['mon', 'day', 'dow',
    'doy', 'hr', 'min']. If include_year=True, also include 'yr' in
    the result.

    This is to be used as part of a ColumnTransformer

    """
    def __init__(self, include_year=False):
        self.include_year = include_year

    def fit(self,X=None,y=None):
        return self
    
    def transform(self,X):
        """ this assumes X is a series of timestamps """
        X = X.astype('datetime64')
        dt = X.dt
        res = {}
        if self.include_year:
            res = {'yr': dt.year}
        res.update({
            'mon': dt.month,
            'day': dt.day,
            'dow': dt.day_of_week,
            'doy': dt.day_of_year,
            'hr': dt.hour,
            'min': dt.minute,
        })
        
        return pd.DataFrame(res).reset_index(drop=True)

class TrigTransformer(BaseEstimator, TransformerMixin):
    """Apply trignometric functions to selected columns with customizable
    period and harmonics """

    def __init__(self, concat=True, h=[1,2], plan=None):
        """Apply trignometric transformation.

        h: harmonics to apply

        concat: if True, return concat of raw input and the trig
        transformations. Otherwise, just return the trig
        transformations

        plan should be a dict where each key value pair has the form
        column: (period, [harmonics]), e.g., 'mon': (12,[1,2,3]),
        where `mon' is the name of a column in the data to be
        transformed. Harmonics specified in kwargs will override the
        `global' <h>
        
        default: apply to dow (day_of_week), doy (day_of_year), hr, min, with harmonics [1,2]

        """
        # NB: MUST save input variables AND under the same name,
        # otherwise will cause error if put inside a ColumnTransformer.
        self.concat = concat
        self.h = h

        self.plan = plan

    def fit(self, X=None, y=None):
        return self

    def transform(self, X):
        # default if plan is None
        plan = self.plan or {
            'doy': (365.25, h),
            'dow': (5, h), # only work days, so period = 5
            'hr': (10,h), # only 8 am to 17:55 pm
            'min': (60,h)
        }

        
        data = []
        label = []

        for column, (period, harmonics) in self.plan.items():
            for f in (np.sin, np.cos):
                for h in harmonics:
                    label.append(f'{f.__name__}_{column}_{h}')
                    func = trig(f, period/h)
                    data.append(func(X[column]))
        trig_data = pd.DataFrame(np.asarray(data).T, columns = label)
        if self.concat:
            return pd.concat([X,trig_data], axis=1)
        return trig_data

################################################################
# For older notebooks. Consider remove in future
read_station_data = read_parking_data
read_station_data_multiyear = read_parking_data_multiyear
resample_station_data = resample_parking_data
