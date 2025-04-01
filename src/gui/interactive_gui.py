import dash
from dash import dcc, html
import dash.dependencies as dd
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json

gdf_states = gpd.read_file("data/gui/states/cb_2018_us_state_500k.shp")
gdf_counties = gpd.read_file("data/gui/counties/cb_2018_us_county_500k.shp")

df_claims = pd.read_csv("data/combined/data_03.csv")

df_state_claims = round(df_claims.groupby("State")["Claims Paid"].sum().reset_index())

gdf_states = gdf_states.merge(df_state_claims, left_on="NAME", right_on="State", how="left")

def create_choropleth(gdf, geojson, featureid, title, map_type):
    fig = px.choropleth(
        gdf,
        geojson=geojson,
        locations=gdf[featureid],
        featureidkey=f"properties.{featureid}",
        color="Claims Paid",
        hover_data={featureid: False, 'NAME': True},
        title=title
    )
    
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Claims Paid: <b>%{z:,.0f}</b>"
        if map_type == "State"
        else "<b>%{customdata[1]}</b><br>Claims Paid: <b>%{z:,.0f}</b>"
    )
    
    fig.update_layout(
        height=800,
        margin={"r":0,"t":50,"l":0,"b":0},
        geo=dict(
            center={"lat": 37.8, "lon": -96},
            projection_scale=5
        )
    )
    return fig

gj_states = json.loads(gdf_states.to_json())
gj_counties = json.loads(gdf_counties.to_json())

app = dash.Dash(__name__)
app.layout = html.Div([
    dcc.Graph(id="map", config={"scrollZoom": True}, style={"width": "100vw", "height": "90vh"}),
    dcc.Store(id="selected-state", data=None),
    dcc.Store(id="selected-county", data=None)
])

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

@app.callback(
    dd.Output("map", "figure"),
    dd.Input("map", "clickData"),
    dd.State("selected-state", "data"),
    dd.State("selected-county", "data")
)
def update_map(clickData, selected_state, selected_county):
    if clickData:
        clicked_id = clickData["points"][0]["location"]
        
        if selected_state is None or clicked_id in gdf_states["NAME"].values:
            selected_state = clicked_id
            selected_county = None  # Reset county when clicking a state
        else:
            selected_county = clicked_id
    
    if selected_state:
        state_fips = state_fips_codes.get(selected_state)
        
        filtered_counties = gdf_counties[gdf_counties["STATEFP"] == state_fips]
        df_claims["State_FIPS"] = df_claims["State"].map(state_fips_codes)
        df_state_claims = df_claims[df_claims["State_FIPS"] == state_fips]
        
        filtered_counties = filtered_counties.merge(df_state_claims, left_on=["NAME", "STATEFP"], right_on=["County", "State_FIPS"], how="left")
        
        if selected_county and selected_county in filtered_counties["NAME"].values:
            county_data = filtered_counties[filtered_counties["NAME"] == selected_county]
            if not county_data.empty:
                bbox = county_data.total_bounds
                if not any(pd.isna(bbox)):
                    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
                    zoom_scale = max(640 / (bbox[2] - bbox[0]), 1)
                    fig = create_choropleth(county_data, gj_counties, "GEOID", f"{selected_county} County in {selected_state}", "County")
                    fig.update_layout(geo=dict(center=center, projection_scale=zoom_scale))
                    return fig
        
        bbox = filtered_counties.total_bounds
        if not any(pd.isna(bbox)):
            center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
            zoom_scale = max(320 / (bbox[2] - bbox[0]), 1)
            fig = create_choropleth(filtered_counties, gj_counties, "GEOID", f"Counties in {selected_state}", "County")
            fig.update_layout(geo=dict(center=center, projection_scale=zoom_scale))
            return fig
    
    return create_choropleth(gdf_states, gj_states, "NAME", "U.S. States", "State")

if __name__ == "__main__":
    app.run(debug=True)
