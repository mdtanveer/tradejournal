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
import plotly.express as px
from plotly.subplots import make_subplots

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
    
    df_tot = df.groupby('RowKey', as_index=False).agg({'FY':'first', 'NetRealizedPnL':'sum'}).reset_index()
    df_tot["PartitionKey"] = "Total"
    df = df[['PartitionKey', 'RowKey', 'NetRealizedPnL', 'FY']].append(df_tot)

    df_tot_yearly = df[["PartitionKey", "FY", "NetRealizedPnL"]].groupby(["PartitionKey", 'FY'], as_index=False).agg('sum').reset_index()
    yearly_chart = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "table"},
               {"type": "bar"}],
               ]
    )

    groups =  df_tot_yearly.groupby("PartitionKey")
    for groupid in groups.groups:
        dfg = groups.get_group(groupid)
        yearly_chart.append_trace(
            go.Bar( x = dfg['FY'],
                        y = dfg['NetRealizedPnL'],
                        text=dfg['NetRealizedPnL'].apply(toLakhs),
                        name=groupid
                    ),
            row=1, col=2
        )

    tab = pd.pivot_table(df_tot_yearly, values='NetRealizedPnL', index='FY',
            columns=['PartitionKey'], aggfunc=np.sum).fillna(0).applymap(toLakhs).reset_index()
    yearly_chart.add_trace(
        go.Table(
            header=dict(
                values=list(tab.columns), 
                font=dict(size=10),
                align="left"
            ),
            cells=dict(
                values=[tab[k].tolist() for k in tab.columns[:]],
                align = "left")
        ),
        row=1, col=1
    )

    yearly_chart.update_layout(
        #height=800,
        title_text="Yearly profit/loss", plot_bgcolor="#f8f8f8"
    )

    monthly_chart = px.bar(df_orig,
                        y = 'RowKey',
                        x = 'NetRealizedPnL',
                        text=df_orig['NetRealizedPnL'].apply(toLakhs),
                        orientation='h',
                        color='PartitionKey'
                    )
    monthly_chart.update_layout(title_text="Monthly profit/loss", height=1200, plot_bgcolor="#f8f8f8")

    return  html.Div(
        children=[
            dcc.Graph(
            id='yearly-chart',
            figure = yearly_chart),
            dcc.Graph(
            id='line-chart',
            figure={
                'data': [
                    go.Line(
                        name="Total",
                        x = df_tot['RowKey'],
                        y = df_tot['NetRealizedPnL'].cumsum(),
                        text=df_tot['NetRealizedPnL'].cumsum().apply(toLakhs),
                        textposition='auto',
                        markers=True,
                    ),
                    go.Bar(
                        name="Total",
                        x = df_tot['RowKey'],
                        y = df_tot['NetRealizedPnL'],
                        text=df_tot['NetRealizedPnL'].apply(toLakhs),
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
            figure = monthly_chart,
            ),
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
