"""Prepare data for Plotly Dash."""
import pandas as pd
import numpy as np
import os
from tradejournal.views import repository

def create_dataframe():
    """Create Pandas DataFrame from local CSV."""
    summaries = repository.get_summary_pnl()
    df = pd.DataFrame(summaries)
    return df.tail(18)
