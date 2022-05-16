# Map related functions
# Time-stamp: <2022-05-16 13:37:51 zshuang>
import streamlit as st
import folium
from folium.plugins import MarkerCluster, BeautifyIcon
from single_marker import SingleClickForMarker

import seaborn as sns

SPACE_NEEDLE = (47.6205, -122.3493)
STATION_PALETTE='colorblind'
MAP_WIDTH=1500
MAP_HEIGHT=800

ICON_SIZE=40

def create_empty_map():
    m = folium.Map(location = SPACE_NEEDLE, zoom_start = 16)
    m.add_child(SingleClickForMarker(tooltip = 'Click on the map to<br> change destination'))
    return m

def restore_map(m, last_click, map_bounds):
    """ add a permanent marker at last_click, and fit into map_bounds """

    if last_click:
        m.add_child(folium.Marker(
            last_click, #tooltip='Destination', popup=last_click,
            #icon=folium.Icon(color='red'),
            icon=BeautifyIcon(icon='car',
                              inner_icon_style='font-size:20px;',
                              inner_icon_anchor=[-3,5],
                              icon_shape='marker', border_color='red',
                              icon_size=[ICON_SIZE,ICON_SIZE]),
        ))
    m.fit_bounds(map_bounds)
    return m

def add_stations_cluster(m,s):
    """ add parking stations <s> to a Map m """
    map_stations = MarkerCluster(locations = s[['latitude', 'longitude']],
                                 icons = [folium.Icon(color='green') for _ in range(len(s))],
                                 popups=s['sourceelementkey'].tolist()).add_to(m)    

def get_human_time(tmin, tmax=None):
    """ convert <tmin>, <tmax> in minutes to a more human-friendly unit """
    if tmin > 60*24:
        tmin = tmin/(60*24)
        tmax = tmax/(60*24) if tmax else tmax
        unit = 'day'
    elif tmin > 60:
        tmin = tmin/60
        tmax = tmax/60 if tmax else tmax
        unit = 'hour'
    else:
        unit = 'min'
    return f"{'%g'%tmin}{' to %g '%tmax if tmax else ' '}{unit}"

def add_stations(m,s, icon_size=ICON_SIZE, font_size='+2.5'):
    # [1] https://github.com/masajid390/BeautifyMarker
    # [2] https://python-visualization.github.io/folium/plugins.html
    #
    # NB: properties like icon_size are translated in via **kwargs of
    # BeautifyIcon.__init__. For a list of properties, see [1]
    nstations = len(s)
    palette = sns.color_palette(STATION_PALETTE, nstations).as_hex()
    for _, (sid, lat,lng,tmin,tmax,scount,dist) in s[
            ['sourceelementkey', 'latitude', 'longitude','time_limit_min', 'time_limit_max', 'space_count', 'dist']
    ].iterrows():
        
        tlim = get_human_time(tmin, None if tmin == tmax else tmax)
        #tlim = '%g %s'%get_human_time(tmax) if tmin == tmax else '%d to %d min'%(tmin,tmax)
        info = f"""<h4>Time limit: <b>{tlim}</b>
                 <h4>Distance: <b>{'%.2f'%(dist * 1609.34)} m</b>
                 <h4>Spaces: <b>{'%d'%scount}</b>"""
        m.add_child(folium.Marker( (lat,lng), popup=folium.Popup(info, max_width=500),
            icon = BeautifyIcon(icon='arrow-down', icon_shape='marker',
                                #number=sid,
                                number = f'<font size="{font_size}">{int(sid)}</font>',
                                background_color=palette[int(sid)-1], border_color='green',
                                text_color='white', icon_size=[icon_size,icon_size])))

def get_map_info(map_data):
    """ Get last click location and bound box from st_folium's map data:

    map_data = st_folium(m, ...) """

    c = map_data.get('last_clicked', None)

    last_click = (c['lat'], c['lng']) if c else None
    map_bounds = [ list(map_data['bounds'][c].values()) for c in map_data['bounds'].keys() ]

    return last_click, map_bounds

def update_map_info(map_data, stations):
    """Check if last_click and map_bounds have changed since refresh. Save
    changes to session dict if any, and propose a new map to draw for
    next refresh

    stations, if not None, is a df of available parking stations. So
    we add them to the map

    """

    ss = st.session_state

    last_click, map_bounds = get_map_info(map_data)
    # Use click from previous UI cycles in case change is initiated
    # not because of new click but because of updated search params
    last_click = last_click or ss['search_params']['location']

    m = create_empty_map()
    if stations is not None:
        add_stations(m, stations)
    restore_map(m, last_click, map_bounds)
    ss['new_map'] = m

def update_map_info_lazy(map_data, stations):
    """Check if last_click and map_bounds have changed since refresh. Save
    changes to session dict if any, and propose a new map to draw for
    next refresh

    stations, if not None, is a df of available parking stations. So
    we add them to the map

    """

    ss = st.session_state

    last_click, map_bounds = get_map_info(map_data)
    #last_click = last_click or ss['search_params']['location']

    #changed = True
    changed = None
    if ss.get('last_click', None) != last_click:
        ss['last_click'] = last_click
        changed = True
    if ss.get('map_bounds', None) != map_bounds:
        ss['map_bounds'] = map_bounds
        changed = True
    if changed:
        # if map info changed, propose a new map to draw for next
        # refresh
        m = create_empty_map()
        if stations is not None:
            add_stations(m, stations)
        restore_map(m, last_click, map_bounds)
        ss['new_map'] = m


