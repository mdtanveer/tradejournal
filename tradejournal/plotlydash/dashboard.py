"""Instantiate a Dash app."""
import numpy as np
import pandas as pd
import dash
from dash import dash_table
from dash import html
from dash import dcc
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

def getFY(date):
    year, month = date.year, date.month
    if month <= 3:
        return year - 1
    else: 
        return year

def toLakhs(amount):
    return  "%0.2fL"%(amount/100000.0)

def layout_func():
    # Load DataFrame
    df_orig = create_dataframe()
    df_orig["FY"] = df_orig['RowKey'].apply(getFY)
    #df_orig["NetRealizedPnL"] = df_orig['NetRealizedPnL'].apply(lambda x: "%0.2fL"%(x/100000.0))
    df = df_orig
    
    df_nfo = df[df['PartitionKey']=='NFO']
    df_mcx = df[df['PartitionKey']=='MCX']
    df_tot = df.groupby('RowKey', as_index=False).agg({'FY':'first', 'NetRealizedPnL':'sum'})

    df_nfo_yearly = df_nfo[["FY", "NetRealizedPnL"]].groupby('FY', as_index=False).agg('sum')
    df_mcx_yearly = df_mcx[["FY", "NetRealizedPnL"]].groupby('FY', as_index=False).agg('sum')
    df_tot_yearly = df_tot[["FY", "NetRealizedPnL"]].groupby('FY', as_index=False).agg('sum')

    return  html.Div(
        children=[dcc.Graph(
            id='line-chart',
            figure={
                'data': [
                    go.Line(
                        name="Total",
                        x = df_tot['RowKey'],
                        y = df_tot['NetRealizedPnL'].cumsum(),
                        text=df_tot['NetRealizedPnL'].cumsum().apply(toLakhs),
                        textposition='auto',
                    )
                    ],
                'layout': {
                    'title': 'Cumulative profit/loss',
                    'plot_bgcolor': '#f8f8f8'
                }
            }),
            dcc.Graph(
            id='monthly-chart',
            figure={
                'data': [
                    go.Bar(
                        name="MCX",
                        x = df_mcx['RowKey'],
                        y = df_mcx['NetRealizedPnL'],
                        text=df_mcx['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                    ),
                    go.Bar(
                        name="NFO",
                        x = df_nfo['RowKey'],
                        y = df_nfo['NetRealizedPnL'],
                        text=df_nfo['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                    ),
                    go.Bar(
                        name="Total",
                        x = df_tot['RowKey'],
                        y = df_tot['NetRealizedPnL'],
                        text=df_tot['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                    ),
                    ],
                'layout': {
                    'title': 'Monthly Profit/Loss table',
                    'plot_bgcolor': '#f8f8f8'
                }
            }),
            dcc.Graph(
            id='yearly-chart',
            figure={
                'data': [
                    go.Bar(
                        name="MCX",
                        x = df_mcx_yearly['FY'],
                        y = df_mcx_yearly['NetRealizedPnL'],
                        text=df_mcx_yearly['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                        ),
                    go.Bar(
                        name="NFO",
                        x = df_nfo_yearly['FY'],
                        y = df_nfo_yearly['NetRealizedPnL'],
                        text=df_nfo_yearly['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                        ),
                    go.Bar(
                        name="Total",
                        x = df_tot_yearly['FY'],
                        y = df_tot_yearly['NetRealizedPnL'],
                        text=df_tot_yearly['NetRealizedPnL'].apply(toLakhs),
                        textposition='auto',
                        ),
                    ],
                'layout': {
                    'title': 'Yearly Profit/Loss table',
                    'plot_bgcolor': '#f8f8f8',
                    'xaxis': {'type':'category'}
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
