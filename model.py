# Module for calling pickled models to predict parking
# Time-stamp: <2022-05-16 07:02:37 zshuang>

from sklearnex import patch_sklearn
patch_sklearn()

from datetime import datetime
import os
import pandas as pd

#from seattle_parking import * #read_noaa_weather_data, find_nearby_stations, SPACE_NEEDLE
import seattle_parking as sp
#from seattle_parking import TimeSplitter

import joblib
import dill

def get_module_path():
    try:
        return os.path.dirname(__file__)
    except:
        return '.'

def load_dill(p):
    with open(p, 'rb') as f:
        m = dill.load(f)
    return m
def dump_dill(obj,p):
    with open(p, 'wb') as f:
        dill.dump(obj,p)

def load_models_near(location = sp.SPACE_NEEDLE, within = 0.3, station_coord_fn='data/Pay_Stations.csv', model_dir = 'models/',station_spacetime_fn='data/pay_station_time_limit_space_count.csv'):
    """ load models for stations within some distance of a target location 

    returns (None, None) if no stations found, or no model available
    else, returns (models_dict, stations_df)
    """
    stations = sp.find_nearby_stations(location, within, coord_fn=station_coord_fn, spacetime_fn=station_spacetime_fn)
    if len(stations) == 0: # nothing found
        return None,None
    model_path = lambda sid: os.path.join(model_dir, '%d.joblib'%sid)
    model_exists = lambda p: os.path.exists(p)

    stations['model_path'] = stations.sourceelementkey.apply(model_path)
    stations['model_exists'] = stations.model_path.apply(model_exists)
    
    # only add existing models
    stations = stations[stations.model_exists]

    if len(stations) == 0: # no model available, perhaps not trained yet
        return None,None

    models = dict(( (sid, joblib.load(p)) for sid,p in stations[['sourceelementkey', 'model_path']].values) )

    return models, stations
        
def impute_weather(date=datetime.today(), wwin=10):
    """ impute weather information for a given day_of_year in a +/- wwin day window """
    doy = date.timetuple().tm_yday # day of year for input date

    # NB: weather data path is semi hard-coded
    weather_path = os.path.join(get_module_path(), 'data/seattle_weather.csv.gz')
    
    df = sp.read_noaa_weather_data(weather_path)

    wsel = abs(df.index.day_of_year - doy) <= wwin
    res = df.iloc[wsel].apply('mean')
    return res

def predict(models, stations, date, time = '8:00', wwin=10, reformat_date = True, return_proba = False):
    """(models, stations) are returns of load_models_near, but it is the
    user's responsibility to check if either of them is None (meaning
    no model/station available)

    date: a datetime.date() object as returned from streamlit
    time: a string
    wwin: weather window in days
    reformat_date: if True, replace datetime index with time-of-day string
    return_proba: if True, return the probability of having parking available
    
    for a given date, will use days within a window of +/-
    weather_window_days to inpute weather info

    """

    # currently model needs the following input:
    #
    # occupancydatetime: 2012-01-03 08:00
    # parkingspacecount
    # tmax
    # tmin
    # prcp
    # snow
    # snwd

    # We will predict a full day's worth of time. User input time
    # right now will not be considered, except perhaps in calculating
    # a score to rank the parking lots
    
    w = impute_weather(date, wwin)
    # a time series from 8:00 to 17:55 with 5min freq on the input date
    ts = pd.timedelta_range('8h', '18h', freq='5min')[:-1] + pd.to_datetime(date)
    X = pd.DataFrame(ts, columns=['occupancydatetime'])
    X[w.keys()] = w # broadcasting imputed weather info into X

    # # We didn't save the parking space count of individual stations so
    # # will just use some reasonable const here
    # X['parkingspacecount'] = 5

    def insert_spacecount(X,sid):
        X['parkingspacecount'] = stations.set_index('sourceelementkey').loc[sid].space_count
        return X

    predictions = pd.DataFrame(
        #{ sid: pd.Series(m.predict(X), index=ts) for sid,m in models.items() }
        { sid: pd.Series(
            m.predict_proba(
                insert_spacecount(X,sid)
            )[:,1] if return_proba else m.predict(X),
            index=ts) for sid,m in models.items() }
        # dict[sid] => predicted Series bools.
    )
    # columns are station ids, index is the time series, so
    # predictions.loc[timeslot, station] = true/false

    # # Eliminate stations with no parking available
    # has_parking = predictions.apply(any).index # stations that has parking
    # predictions = predictions[has_parking]

    # Reformat index to show time of day only
    if reformat_date:
        predictions.index = predictions.index.strftime('%H:%M')
    #stations = 
    
    
    return predictions
