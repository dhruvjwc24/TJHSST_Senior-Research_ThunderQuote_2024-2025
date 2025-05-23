import dash
from dash import dcc, html
import dash.dependencies as dd
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json

# Load GeoDataFrames
gdf_states = gpd.read_file("data/gui/states/cb_2018_us_state_500k.shp")
gdf_counties = gpd.read_file("data/gui/counties/cb_2018_us_county_500k.shp")

# Load Claims Data
df_claims = pd.read_csv("data/combined/data_04.csv")

# State-level aggregation
df_state_claims = df_claims.groupby("State")[["Claims Paid", "Dollars Paid"]].sum().reset_index()
gdf_states = gdf_states.merge(df_state_claims, left_on="NAME", right_on="State", how="left")

# County-level aggregation (all years)
state_fips_codes = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05", "California": "06",
    "Colorado": "08", "Connecticut": "09", "Delaware": "10", "Florida": "12", "Georgia": "13",
    "Hawaii": "15", "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19", "Kansas": "20",
    "Kentucky": "21", "Louisiana": "22", "Maine": "23", "Maryland": "24", "Massachusetts": "25",
    "Michigan": "26", "Minnesota": "27", "Mississippi": "28", "Missouri": "29", "Montana": "30",
    "Nebraska": "31", "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40",
    "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46",
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56"
}
df_claims["State_FIPS"] = df_claims["State"].map(state_fips_codes)
df_county_claims = df_claims.groupby(["State_FIPS", "County"])[["Claims Paid", "Dollars Paid"]].sum().reset_index()

gdf_counties["State_FIPS"] = gdf_counties["STATEFP"]
gdf_counties = gdf_counties.merge(
    df_county_claims,
    left_on=["State_FIPS", "NAME"],
    right_on=["State_FIPS", "County"],
    how="left"
)

def create_choropleth(gdf, geojson, featureid, title, map_type):
    fig = px.choropleth(
        gdf,
        geojson=geojson,
        locations=gdf[featureid],
        featureidkey=f"properties.{featureid}",
        color="Claims Paid",
        hover_data={"NAME": True, "Claims Paid": True, "Dollars Paid": True},
        title=title,
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Claims Paid: <b>%{customdata[1]:,.0f}</b><br>Dollars Paid: <b>$%{customdata[2]:,.0f}</b>"
    )
    fig.update_layout(
        height=800,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        geo=dict(
            center={"lat": 37.8, "lon": -96},
            projection_scale=5
        )
    )
    return fig

gj_states = json.loads(gdf_states.to_json())
gj_counties = json.loads(gdf_counties.to_json())

app = dash.Dash(__name__)
app.layout = html.Div(style={"display": "flex"}, children=[
    dcc.Graph(id="map", config={"scrollZoom": True}, style={"width": "75vw", "height": "90vh"}),
    html.Div(style={"width": "25vw", "padding": "1em", "borderLeft": "1px solid #ccc"}, children=[
        html.Div(id="info-tab-content"),
        html.Button("Back to US Map", id="back-button", n_clicks=0, style={
            "width": "100%",
            "padding": "1em",
            "fontSize": "1.2em",
            "marginTop": "2em",
            "display": "none"
        })
    ]),
    dcc.Store(id="selected-state", data=None),
    dcc.Store(id="selected-county", data=None),
    dcc.Store(id="zoom-level", data="State")
])

@app.callback(
    [dd.Output("selected-state", "data"),
    dd.Output("selected-county", "data"),
    dd.Output("map", "figure"),
    dd.Output("zoom-level", "data")],
    [dd.Input("map", "clickData"), dd.Input("back-button", "n_clicks")],
    [dd.State("selected-state", "data"),
    dd.State("selected-county", "data"),
    dd.State("zoom-level", "data")]
)
def update_map(clickData, back_clicks, selected_state, selected_county, zoom_level):
    ctx = dash.callback_context

    if ctx.triggered and ctx.triggered[0]["prop_id"] == "back-button.n_clicks":
        return None, None, create_choropleth(gdf_states, gj_states, "NAME", "U.S. States", "State"), "State"

    if clickData:
        clicked_id = clickData["points"][0]["location"]

        if selected_state is None or clicked_id in gdf_states["NAME"].values:
            selected_state = clicked_id
            selected_county = None
        else:
            selected_county = clicked_id

    if selected_state:
        state_fips = state_fips_codes.get(selected_state)
        filtered_counties = gdf_counties[gdf_counties["STATEFP"] == state_fips]

        if selected_county and selected_county in filtered_counties["NAME"].values:
            county_data = filtered_counties[filtered_counties["NAME"] == selected_county]
            if not county_data.empty:
                bbox = county_data.total_bounds
                if not any(pd.isna(bbox)):
                    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
                    zoom_scale = max(640 / (bbox[2] - bbox[0]), 1)
                    fig = create_choropleth(county_data, gj_counties, "GEOID", f"{selected_county} County in {selected_state}", "County")
                    fig.update_layout(geo=dict(center=center, projection_scale=zoom_scale))
                    return selected_state, selected_county, fig, "County"

        bbox = filtered_counties.total_bounds
        if not any(pd.isna(bbox)):
            center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
            
            # Width and height of bounding box
            bbox_width = bbox[2] - bbox[0]
            bbox_height = bbox[3] - bbox[1]

            # Calculate appropriate scale to fit map tightly in frame
            scale_x = 0.8 * (400 / bbox_width)
            scale_y = 0.8 * (200 / bbox_height)

            zoom_scale = min(scale_x, scale_y)
            
            fig = create_choropleth(filtered_counties, gj_counties, "GEOID", f"Counties in {selected_state}", "County")
            fig.update_layout(geo=dict(center=center, projection_scale=zoom_scale))
            return selected_state, None, fig, "County"

    return selected_state, selected_county, create_choropleth(gdf_states, gj_states, "NAME", "U.S. States", "State"), zoom_level

@app.callback(
    dd.Output("info-tab-content", "children"),
    [dd.Input("map", "hoverData"),
    dd.Input("selected-state", "data"),
    dd.Input("zoom-level", "data")]
)
def update_info_tab(hoverData, selected_state, zoom_level):
    if not hoverData:
        return html.Div([
            html.P("Hover over a state or county for details."),
        ], style={
            "color": "#1f2d3d", "backgroundColor": "#f0f8ff", "padding": "1em", "borderRadius": "10px"
        })

    point = hoverData["points"][0]
    customdata = point.get("customdata", [])

    if customdata and len(customdata) >= 3:
        name = customdata[0]
        claims = customdata[1]
        dollars = customdata[2]
        return html.Div([
            html.H2(name, style={"color": "#0074D9", "marginBottom": "0.5em"}),
            html.P(f"Claims Paid: {claims:,.0f}", style={"fontWeight": "bold", "color": "#001f3f"}),
            html.P(f"Dollars Paid: ${dollars:,.0f}", style={"fontWeight": "bold", "color": "#001f3f"})
        ], style={
            "backgroundColor": "#e6f2ff",
            "padding": "1em",
            "border": "1px solid #0074D9",
            "borderRadius": "10px"
        })

    return html.P("No data available.", style={"color": "#001f3f"})

@app.callback(
    dd.Output("back-button", "style"),
    dd.Input("zoom-level", "data")
)
def toggle_back_button(zoom_level):
    if zoom_level == "State":
        return {"display": "none"}
    return {
        "width": "100%",
        "padding": "1em",
        "fontSize": "1.2em",
        "marginTop": "2em"
    }

if __name__ == "__main__":
    app.run(debug=True)
