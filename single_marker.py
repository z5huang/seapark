from branca.element import MacroElement
from jinja2 import Template

class SingleClickForMarker(MacroElement):
    """
    Create a single marker at click, eliminate the previous one if present

    Parameters
    ----------
    tooltip. If none, show Latitude and Longitude

    """
    # see https://gis.stackexchange.com/a/238419
    _template = Template(u"""
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = {};
                function singleMarker(e){
                    lat = e.latlng.lat;
                    lng = e.latlng.lng;
                    if ({{this.get_name()}} != undefined) {
                        {{this._parent.get_name()}}.removeLayer({{this.get_name()}});
                        //{{this.get_name()}}.setLatLng(e.latlng);
                    }
                    {{this.get_name()}} = L.marker().setLatLng(e.latlng).bindTooltip({{this.tooltip}}).addTo({{this._parent.get_name()}});
                    };
                {{this._parent.get_name()}}.on('click', singleMarker);
            {% endmacro %}
            """)  # noqa

    def __init__(self, tooltip=None):
        super(SingleClickForMarker, self).__init__()
        self._name = 'SingleClickForMarker'

        if tooltip:
            self.tooltip = ''.join(['"', tooltip, '"'])
        else:
            self.tooltip = '"Latitude: " + lat.toFixed(4) + "<br>Longitude: " + lng.toFixed(4) '
