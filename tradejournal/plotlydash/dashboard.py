"""Instantiate a Dash app."""
import numpy as np
import pandas as pd
import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from .data import create_dataframe
from .layout import html_layout
from ..models import azuretablestorage
import plotly.graph_objs as go


def create_dashboard(server):
    """Create a Plotly Dash dashboard."""
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/dashboard/',
    )

    # Custom HTML layout
    dash_app.index_string = html_layout

    # Create Layout
    dash_app.layout = layout_func
    return dash_app.server

def getFY(datestr):
    year, month, day = map(lambda x: int(x), datestr.split('-'))
    if month <= 3:
        return year - 1
    else: 
        return year

def layout_func():
    # Load DataFrame
    df_orig = create_dataframe()
    df_orig["FY"] = df_orig['RowKey'].apply(getFY)
    df = df_orig.tail(18)
    df_yearly = df_orig.groupby(['FY']).sum().reset_index()

    return  html.Div(
        children=[dcc.Graph(
            id='monthly-chart',
            figure={
                'data': [go.Bar(
                    x = df['RowKey'],
                    y = df['NetRealizedPnL'],
                    text=df['NetRealizedPnL'].apply(lambda x: "%0.2fL"%(x/100000.0)),
                    textposition='auto',
                )],
                'layout': {
                    'title': 'Monthly Profit/Loss table',
                    'plot_bgcolor': '#f8f8f8'
                }
            }),
            dcc.Graph(
            id='yearly-chart',
            figure={
                'data': [go.Bar(
                    x = df_yearly['FY'],
                    y = df_yearly['NetRealizedPnL'],
                    text=df_yearly['NetRealizedPnL'].apply(lambda x: "%0.2fL"%(x/100000.0)),
                    textposition='auto',
                    marker_color='lightsalmon'
                )],
                'layout': {
                    'title': 'Yearly Profit/Loss table',
                    'plot_bgcolor': '#f8f8f8'
                }
            }),
        ],
        id='dash-container'
    )

def create_data_table(df):
    """Create Dash datatable from Pandas DataFrame."""
    table = dash_table.DataTable(
        id='database-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        sort_action="native",
        sort_mode='native',
        page_size=300
    )
    return table
