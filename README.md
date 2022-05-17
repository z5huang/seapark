# SeaPark

The city of Seattle publishes on-street paid parking occupancy data at https://data.seattle.gov. These are derived from transaction records whenever someone makes a payment for their street parking. The difference between the total number of spots available at a parking lot, and those that have been paid for, can be used to estimate how many spots are open at that time. Note that this is not exact science. Illegal parking, for example, could lead to over-estimation of available spots. Conversely, early departure before ticket expiary will cause an open spot to remain 'occupied' in the system, resulting in under-estimation. These caveats should be kept in mind when interpreting predictions. 

This repository contains frontend code built on the `streamlit` framework. A [demo](https://tinyurl.com/seaparker) of about 200 parking lots near the Space Needle is live on streamlit share. Screenshot:
![image](https://user-images.githubusercontent.com/57611601/168700994-194461f8-28df-4146-a8c1-c48ab78f8436.png)
The models, as pickled in `models/`, are trained and tested on (5+1) years of historical parking data together with daily weather information, and should improve with more data. The repo is organized as follows:

- `app.py`: main UI driver
- `mapper.py`: code related to managing markers on the map
- `plotter.py`: code related to presenting prediction results as a heatmap
- `model.py`: code related to calling pre-trained models from the app
- `seattle_parking.py`: code related to reading data and interfacing with pre-trained models
- `single_marker.py`: a single marker version of folium's [`ClickForMarker`](https://python-visualization.github.io/folium/modules.html#folium.features.ClickForMarker) feature. This is used to get user input of parking destination through a pin drop.
-  `data/`: pay station and weather data
- `models/`: pre-trained models named after `sourceelementkey`
- `requirements.txt`: dependencies for online deployment
- `Procfile` and `setup.sh`: for Heroku deployment. (I've since moved to [streamlit share](https://share.streamlit.io) due to Heroku's more restrictive size limit)
