# The SeaPark App
# Time-stamp: <2022-05-18 19:05:36 zshuang>

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import joblib
from datetime import datetime
from math import ceil

from model import load_models_near, predict
from mapper import create_empty_map, get_map_info, update_map_info
from mapper import STATION_PALETTE, SPACE_NEEDLE
from plotter import plot_predictions, compute_width, time_to_y

# Set website title and layout
st.set_page_config(
    page_title = 'SeaPark!',
    layout='wide',
)

SS = st.session_state

# Space needle location
SPACE_NEEDLE = (47.6205, -122.3493)

# Map size
#MAP_WIDTH=1000
#MAP_HEIGHT=800
MAP_WIDTH=800
MAP_HEIGHT=800

# Pagination of prediction results
STATIONS_PERPAGE=8
PLOT_HEIGHT=9.5 # Not an exact science but should be set proportional to MAP_HEIGHT
#PLOT_HEIGHT=7.5
PLOT_COL_WIDTH=0.1 # Approximate width of each col in unit of PLOT_HEIGHT

# Helper for keeping tabs on the UI cycle, a numbered print if you will
def counter(pre='', post=''):
    SS.counter = SS.get('counter', 0) + 1 # increment counter
    st.text('%s%d%s'%(pre, SS.counter, post))


model_dir = 'models/' # Pretrained models station-wise
def run_model(search_params):
    """ run model according to search parameters """
    models, stations = load_models_near( location = search_params['location'], within = search_params['dist'] , model_dir = model_dir)
    if models is None:
        return None,None
    predictions = predict(models, stations, date = search_params['date'], return_proba=True)
    return predictions, stations


################################################################
# UI helper
################
def enable_go():
    if SS.get('search_params', None): # ensure search parameters exist from past cycles
        SS['activate_go'] = SS.get('activate_go', None) or True
    #st.header('activate_go is ', SS['activate_go'])
def disable_go():
    if SS.get('activate_go', None):
        SS['activate_go'] = None

def add_datetime_picker():
    st.subheader('When are you arriving?')
    UI_DATE = st.date_input(
        label = 'Date',
        min_value = datetime.today().date(),
        key = 'date_picker',
        on_change = enable_go,
    )
    time_slots = [ x.strftime('%H:%M') for x in pd.date_range('8:00', '18:00', freq='5min') ]
    UI_TIME = st.selectbox(
        label = 'Time',
        options = time_slots,
        index = int(time_to_y('11:00')),
        key = 'time_picker',
    )
    return UI_DATE, UI_TIME

def add_dist_picker():
    st.subheader('How far are you willing to walk?')
    UI_DIST = st.slider(
        label = 'An average city block is about 0.07 mi (5 min walk)',
        min_value = 1,
        max_value = 10,
        value = 1,
        step = 1,
        format = ('%g blocks'),
        key = 'max_dist',
        on_change = enable_go,
    )
    return UI_DIST

#def add_weather_checker():
#    st.subheader('Incorporate weather information?')
#    ui_use_forecast = st.checkbox(
#        label = 'Use forecast if available',
#        value = True,
#        key = 'use_forecast',
#    )
#    st.write('Fall back: monthly average weather data over the past decade')
#    return ui_use_forecast
    

def update_stage():
    """Update the "stage" for the next UI cycle.
 
    This should NOT be called UNLESS there is some change to the
    search parameters
    
    """
    # NB: simply adding this counter will cause the map to flash twice at
    # reload.
    #counter('', ' : update_stage') 

    disable_go()
    #SS['activate_go'] = None # disable search by default unless requested explicitly

    last_click, map_bounds = get_map_info(UI_MAP)
    # If map has not been clicked since ui refresh, use past ui cycle
    # data instead. This is so that go_button activated by other UI
    # element can still find a parking target. NB: User should MAKE
    # SURE it has been recorded
    last_click = last_click or SS['search_params']['location']
    
    search_params = {
        'location': last_click,
        'date': UI_DATE,
        'time': UI_TIME,
        'dist': UI_DIST * 0.07, # raw read in city blocks
        #'use_forecast': ui_use_forecast,
    }
    SS['search_params'] = search_params
    predictions, stations = run_model(search_params)
    if stations is not None:
        # rename stations
        stations.sourceelementkey = predictions.columns = list(range(1, len(stations)+1))
    SS['predictions'] = predictions # save predictions even if it's None (i.e., no data or no stations available)

    # Also reset page information
    SS['page']=1

    update_map_info(UI_MAP, stations)
    SS.stage = 'pred'

def add_go_button(override=True):
    # NB: It's important to update internal state, map, etc.,
    # using the on_click here. on_click is called _between_ the
    # end of this run, and the beginning of the next run.
    #
    # Do NOT put the state update code in `if UI_GO: ...`, i.e. the
    # button ui code, otherwise expect weird and potentially infinite
    # flashing loops!

    disabled = not UI_MAP.get('last_clicked', None)
    # override if other UI elements requested activation
    if override:
        disabled = disabled and (not SS.get('activate_go', None))


    UI_GO =  st.button(
        label = "Let's find out!",
        disabled = disabled,
        on_click = update_stage,
    )

def prepare_map():
    """ prepare map for this run """
    # get the map of last refresh, create an empty one if necessary
    res = SS.get('current_map', create_empty_map())
    
    # If not the first run, check if a new map is proposed at last
    # button click
    if SS.stage != 'init':
        new_map = SS.get('new_map', None)
        if new_map and (new_map != res):
            SS['current_map'] = res = new_map
    return res

def prev_page():
    SS['page'] -= 1

def next_page():
    SS['page'] = SS.get('page',1) + 1


################################################################
# UI
################
st.title('Welcome to SeaPark!')
#st.markdown(f"""
#<h1>Welcome to SeaPark!&nbsp;&nbsp;
#<span style="font-size:80%; color:blue;"><u>https://bit.ly/seaparker</u></span>
#</h1>""", unsafe_allow_html=True)

# Center-align:
#st.markdown("<h1 style='text-align: center; '>Welcome to SeaPark!</h1>", unsafe_allow_html=True)

# Set init stage for first run
SS.stage = SS.get('stage', 'init')

################
# side bar widgets
with st.sidebar:
    st.title('')
    st.text('')
    st.text('')
    st.text('')
    st.text('')    
    UI_DATE, UI_TIME = add_datetime_picker()
    UI_DIST = add_dist_picker()
    #ui_use_forecast = add_weather_checker()
    st.title('')
    # UI_GO = add_go_button() # Go button must come after UI_MAP creation, to verify if it should be enabled

################
# main panel
col1,col2 = st.columns([0.618,1])

with col1:
    st.subheader('Where are you going?')
    current_map = prepare_map()
    UI_MAP = st_folium(current_map, width=MAP_WIDTH, height=MAP_HEIGHT)
with st.sidebar:
    cs1,cs2,cs3 = st.columns([2,0.5,0.5])
    with cs1:
        # Go button must come after UI_MAP creation, to verify if it should be enabled
        UI_GO = add_go_button(override=True)
    #with cs2:
    #    st.button('a')
    #with cs3:
    #    st.button('4')

if SS.stage != 'init':
    with col2:
        predictions = SS.get('predictions', None)
        if predictions is None:
            st.subheader(f'No parking available')
        else:
            nstations = len(predictions.columns)
            #st.subheader(f'Found {nstations} results')
            st.markdown(f"""
<h3>Found {nstations} results &nbsp;
<span style="font-size:60%; color: white; background-color:#029e37"> Available </span>
<span style="font-size:60%; color: white; background-color:lightgray"> Maybe </span>
<span style="font-size:60%; color: white; background-color:#ef5b66"> Not available </span>
</h3>""", unsafe_allow_html=True)

            page = SS.get('page',1)
            width = compute_width(PLOT_HEIGHT, PLOT_COL_WIDTH,
                                  nstations, page, STATIONS_PERPAGE)
            
            st.image(plot_predictions(predictions, (width,PLOT_HEIGHT),
                                      page, perpage=STATIONS_PERPAGE, hline = UI_TIME),
                     width=int(width*85),
                     #use_column_width='auto',
                     use_column_width='never'
                     )
            pmax = ceil(nstations / STATIONS_PERPAGE)
            if page < pmax:
                with cs3:
                    st.button(label='>>', on_click = next_page)
            if page > 1:
                with cs2:
                    st.button(label='<<', on_click = prev_page)



