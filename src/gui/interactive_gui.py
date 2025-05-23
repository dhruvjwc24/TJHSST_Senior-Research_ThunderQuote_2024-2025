import dash
from dash import dcc, html
import dash.dependencies as dd
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json
import math

gdf_states = gpd.read_file("data/gui/states/cb_2018_us_state_500k.shp")
gdf_counties = gpd.read_file("data/gui/counties/cb_2018_us_county_500k.shp")
df_claims = pd.read_csv("data/combined/data_04.csv")

df_state_claims = df_claims.groupby("State")[["Claims Paid", "Dollars Paid", "Total Storms"]].sum().reset_index()
gdf_states = gdf_states.merge(df_state_claims, left_on="NAME", right_on="State", how="left")

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
df_county_claims = df_claims.groupby(["State_FIPS", "County"])[["Claims Paid", "Dollars Paid", "Total Storms"]].sum().reset_index()

gdf_counties["State_FIPS"] = gdf_counties["STATEFP"]
gdf_counties = gdf_counties.merge(
    df_county_claims,
    left_on=["State_FIPS", "NAME"],
    right_on=["State_FIPS", "County"],
    how="left"
)

def create_choropleth(gdf, geojson, featureid, title, map_type):
    gdf["Average Claim Amount"] = gdf.apply(
        lambda row: row["Dollars Paid"] / row["Claims Paid"] if row["Claims Paid"] and row["Dollars Paid"] else 0,
        axis=1
    )
    fig = px.choropleth(
        gdf,
        geojson=geojson,
        locations=gdf[featureid],
        featureidkey=f"properties.{featureid}",
        color="Claims Paid",
        hover_data={"NAME": True, "Claims Paid": True, "Dollars Paid": True, "Average Claim Amount": True, "Total Storms": True},
        title=title,
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Claims Paid: <b>%{customdata[1]:,.0f}</b><br>"
            "Dollars Paid: <b>$%{customdata[2]:,.0f}</b><br>"
            "Average Claim Amount: <b>$%{customdata[3]:,.2f}</b><br>"
            "Total Storms: <b>%{customdata[4]:,.0f}</b>"
        )
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

app = dash.Dash(__name__, suppress_callback_exceptions=True)
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
    dcc.Store(id="zoom-level", data="State"),
    dcc.Store(id="user-inputs", data={})
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
        return None, None, create_choropleth(gdf_states, gj_states, "NAME", "U.S. States Since 1980", "State"), "State"

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
            bbox_width = bbox[2] - bbox[0]
            bbox_height = bbox[3] - bbox[1]
            scale_x = 0.8 * (400 / bbox_width)
            scale_y = 0.8 * (200 / bbox_height)
            zoom_scale = min(scale_x, scale_y)

            fig = create_choropleth(filtered_counties, gj_counties, "GEOID", f"Counties in {selected_state} Since 1980", "County")
            fig.update_layout(geo=dict(center=center, projection_scale=zoom_scale))
            return selected_state, None, fig, "County"

    return selected_state, selected_county, create_choropleth(gdf_states, gj_states, "NAME", "U.S. States Since 1980", "State"), zoom_level

@app.callback(
    dd.Output("info-tab-content", "children"),
    [dd.Input("map", "hoverData"),
        dd.Input("user-inputs", "data")],
    [dd.State("selected-state", "data"),
        dd.State("zoom-level", "data")]
)
def update_info_tab(hoverData, user_inputs, selected_state, zoom_level):
    if not hoverData:
        return html.Div([
            html.P("Hover over a state or county for details."),
        ], style={
            "color": "#1f2d3d", "backgroundColor": "#f0f8ff", "padding": "1em", "borderRadius": "10px"
        })

    point = hoverData["points"][0]
    customdata = point.get("customdata", [])

    if customdata and len(customdata) >= 4:
        name = customdata[0]
        claims = customdata[1]
        dollars = customdata[2]
        avg_claim = customdata[3]
        storms = customdata[4]
        
        breakdown = [((dollars / (claims * 15)) / 0.7),
                    (1 + (0.0000025 * storms)),
                    (1 + (0.005 * (1981.5 - (user_inputs.get('year-built-dropdown') or 1981.5)))),
                    (1.1 if user_inputs.get('residence-type-dropdown') == '3+ Stories' else 0.9 if user_inputs.get('residence-type-dropdown') == '1 Story' else 1),
                    (1 + (0.0001 * ((user_inputs.get('square-footage-input') or 2200.5) - 2200.5))),
                    (0.975 if user_inputs.get('single-family-dropdown') == 'Yes' else 1.025 if user_inputs.get('single-family-dropdown') == 'No' else 1),
                    (1.1 if user_inputs.get('primary-residence-dropdown') == 'Yes' else 0.9 if user_inputs.get('primary-residence-dropdown') == 'No' else 1),
                    (1 + (0.001 * ((user_inputs.get('year-bought-dropdown') or 2015.5) - 2015.5))),
                    (0.975 if 'Burglar Alarm' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (0.975 if 'Fire Alarm' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (0.975 if 'Fire Sprinklers' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (0.975 if 'Emergency Backup Generator' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (0.975 if 'Home Automation System' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (1.05 if 'None of the above' in (user_inputs.get('protective-devices-dropdown') or []) else 1),
                    (0.95 if user_inputs.get('wall-type-dropdown') == 'Brick Frame' else 
                        0.975 if user_inputs.get('wall-type-dropdown') == 'Stucco Block' else
                        0.99 if user_inputs.get('wall-type-dropdown') == 'Stucco Frame' else
                        1.01 if user_inputs.get('wall-type-dropdown') == 'Wood Siding' else
                        1.025 if user_inputs.get('wall-type-dropdown') == 'Non-Wood/Vinyl' else 1),
                    (0.95 if user_inputs.get('roof-material-dropdown') == 'Slate' else
                        0.975 if user_inputs.get('roof-material-dropdown') == 'Metal' else
                        0.99 if user_inputs.get('roof-material-dropdown') == 'Tile' else
                        1.01 if user_inputs.get('roof-material-dropdown') == 'Asphalt' else
                        1.025 if user_inputs.get('roof-material-dropdown') == 'Wood' else 1),
                    (1 + (0.01 * ((user_inputs.get('roof-age-input') or 5.5) - 5.5))),
                    (0.95 if user_inputs.get('foundation-type-dropdown') == 'Basement' else
                        0.975 if user_inputs.get('foundation-type-dropdown') == 'Slab' else
                        0.99 if user_inputs.get('foundation-type-dropdown') == 'Hillside with Basement' else
                        1.01 if user_inputs.get('foundation-type-dropdown') == 'Crawl Space' else
                        1.025 if user_inputs.get('foundation-type-dropdown') == 'Hillside without Basement' else
                        1.05 if user_inputs.get('foundation-type-dropdown') == 'Piers' else 1)]
                
        premium_calculation_year = round(math.prod(breakdown), 2)
        premium_calculation_month = round((math.prod(breakdown) / 12), 2)

        return html.Div([
            html.H2(name, style={"color": "#0074D9", "marginBottom": "0.5em"}),
            html.P(f"Claims Paid: {claims:,.0f}", style={"fontWeight": "bold", "color": "#001f3f"}),
            html.P(f"Dollars Paid: ${dollars:,.0f}", style={"fontWeight": "bold", "color": "#001f3f"}),
            html.P(f"Average Claim Amount: ${avg_claim:,.2f}", style={"fontWeight": "bold", "color": "#001f3f"}),
            html.P(f"Total Storms: {storms:,.0f}", style={"fontWeight": "bold", "color": "#001f3f"}),

            html.Hr(),

            html.Label("Year Constructed", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[{"label": str(year), "value": year} for year in range(2025, 1899, -1)],
                placeholder="Select Year Constructed",
                id="year-built-dropdown",
                value=user_inputs.get("year-built-dropdown")
            ),

            html.Label("Residence Type", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "1 Story", "value": "1 Story"},
                    {"label": "2 Stories", "value": "2 Stories"},
                    {"label": "3+ Stories", "value": "3+ Stories"},
                ],
                placeholder="Select Residence Type",
                id="residence-type-dropdown",
                value=user_inputs.get("residence-type-dropdown")
            ),

            html.Label("Square Footage", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Input(
                type="number",
                placeholder="Enter Square Footage",
                id="square-footage-input",
                value=user_inputs.get("square-footage-input"),
                style={"width": "100%"}
            ),

            html.Label("Single-Family", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Yes", "value": "Yes"},
                    {"label": "No", "value": "No"},
                ],
                placeholder="Is it Single-Family?",
                id="single-family-dropdown",
                value=user_inputs.get("single-family-dropdown")
            ),

            html.Label("Primary Residence", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Yes", "value": "Yes"},
                    {"label": "No", "value": "No"},
                ],
                placeholder="Is it Primary Residence?",
                id="primary-residence-dropdown",
                value=user_inputs.get("primary-residence-dropdown")
            ),

            html.Label("Purchase Year", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[{"label": str(year), "value": year} for year in range(2025, 1899, -1)],
                placeholder="Select Purchase Year",
                id="year-bought-dropdown",
                value=user_inputs.get("year-bought-dropdown")
            ),

            html.Label("Protective Devices", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Burglar Alarm", "value": "Burglar Alarm"},
                    {"label": "Fire Alarm", "value": "Fire Alarm"},
                    {"label": "Fire Sprinklers", "value": "Fire Sprinklers"},
                    {"label": "Emergency Backup Generator", "value": "Emergency Backup Generator"},
                    {"label": "Home Automation System", "value": "Home Automation System"},
                    {"label": "None of the above", "value": "None of the above"},
                ],
                placeholder="Select Protective Devices",
                id="protective-devices-dropdown",
                multi=True,
                value=user_inputs.get("protective-devices-dropdown"),
                style={"width": "100%"}
            ),

            html.Label("Exterior Wall Type", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Brick Frame", "value": "Brick Frame"},
                    {"label": "Stucco Block", "value": "Stucco Block"},
                    {"label": "Stucco Frame", "value": "Stucco Frame"},
                    {"label": "Wood Siding", "value": "Wood Siding"},
                    {"label": "Non-Wood/Vinyl", "value": "Non-Wood/Vinyl"},
                    {"label": "Other", "value": "Other"},
                ],
                placeholder="Select Wall Type",
                id="wall-type-dropdown",
                value=user_inputs.get("wall-type-dropdown")
            ),

            html.Label("Roof Material", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Asphalt", "value": "Asphalt"},
                    {"label": "Wood", "value": "Wood"},
                    {"label": "Tile", "value": "Tile"},
                    {"label": "Metal", "value": "Metal"},
                    {"label": "Slate", "value": "Slate"},
                    {"label": "Other", "value": "Other"},
                ],
                placeholder="Select Roof Material",
                id="roof-material-dropdown",
                value=user_inputs.get("roof-material-dropdown")
            ),

            html.Label("Roof Age", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Input(
                type="number",
                placeholder="Enter Roof Age (years)",
                id="roof-age-input",
                value=user_inputs.get("roof-age-input"),
                style={"width": "100%"}
            ),
            
            html.Label("Foundation Type", style={"marginTop": "1em", "fontWeight": "bold"}),
            dcc.Dropdown(
                options=[
                    {"label": "Slab", "value": "Slab"},
                    {"label": "Basement", "value": "Basement"},
                    {"label": "Crawl Space", "value": "Crawl Space"},
                    {"label": "Piers", "value": "Piers"},
                    {"label": "Hillside with Basement", "value": "Hillside with Basement"},
                    {"label": "Hillside without Basement", "value": "Hillside without Basement"},
                    {"label": "Other", "value": "Other"},
                ],
                placeholder="Select Foundation Type",
                id="foundation-type-dropdown",
                value=user_inputs.get("foundation-type-dropdown")
            ),
            
            html.Hr(),
                        
            html.H3("Premium Calculation Estimate", style={"marginTop": "1em", "color": "#0074D9"}),
            html.P(f"${premium_calculation_year:.2f} a year or ${premium_calculation_month:.2f} a month", style={"fontWeight": "bold", "color": "#001f3f", "fontSize": "1.2em"})

        ], style={
            "backgroundColor": "#e6f2ff",
            "padding": "1em",
            "border": "1px solid #0074D9",
            "borderRadius": "10px",
            "overflowY": "auto",
            "maxHeight": "85vh"
        })

    return html.P("No data available.", style={"color": "#001f3f"})

@app.callback(
    dd.Output("user-inputs", "data"),
    [dd.Input("year-built-dropdown", "value"),
        dd.Input("residence-type-dropdown", "value"),
        dd.Input("square-footage-input", "value"),
        dd.Input("single-family-dropdown", "value"),
        dd.Input("primary-residence-dropdown", "value"),
        dd.Input("year-bought-dropdown", "value"),
        dd.Input("protective-devices-dropdown", "value")],
        dd.Input("wall-type-dropdown", "value"),
        dd.Input("roof-material-dropdown", "value"),
        dd.Input("roof-age-input", "value"),
        dd.Input("foundation-type-dropdown", "value"),
    [dd.State("user-inputs", "data")]
)
def store_user_inputs(year_built, residence_type, square_footage, single_family, primary_residence, year_bought, protective_devices, wall_type, roof_material, roof_age, foundation_type, current_data):
    current_data.update({
        "year-built-dropdown": year_built,
        "residence-type-dropdown": residence_type,
        "square-footage-input": square_footage,
        "single-family-dropdown": single_family,
        "primary-residence-dropdown": primary_residence,
        "year-bought-dropdown": year_bought,
        "protective-devices-dropdown": protective_devices,
        "wall-type-dropdown": wall_type,
        "roof-material-dropdown": roof_material,
        "roof-age-input": roof_age,
        "foundation-type-dropdown": foundation_type,
    })
    return current_data

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
