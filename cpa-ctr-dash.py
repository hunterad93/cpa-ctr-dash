import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np
from scipy import stats

def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", key="app_password", on_change=validate_password)
        return False
    return st.session_state["password_correct"]

def validate_password():
    """Validates the entered password."""
    if st.session_state["app_password"] == st.secrets["app_password"]:
        st.session_state["password_correct"] = True
        del st.session_state["app_password"]
    else:
        st.session_state["password_correct"] = False
        st.error("😕 Password incorrect")

@st.cache_data
def load_data():
    return pd.read_csv('processed_vertical_metrics.csv')

def prepare_data(df, selected_vertical):
    if selected_vertical == 'All Verticals':
        df_grouped = df.groupby('3rd Party Data Brand').agg({
            'Clicks': 'sum',
            'Impressions': 'sum',
            'Hypothetical Advertiser Cost (Adv Currency)': 'sum',
            'All Last Click + View Conversions': 'sum'
        }).reset_index()
    else:
        df_filtered = df[df['Vertical'] == selected_vertical]
        df_grouped = df_filtered.groupby(['Vertical', '3rd Party Data Brand']).agg({
            'Clicks': 'sum',
            'Impressions': 'sum',
            'Hypothetical Advertiser Cost (Adv Currency)': 'sum',
            'All Last Click + View Conversions': 'sum'
        }).reset_index()
    
    df_grouped['CTR'] = df_grouped['Clicks'] / df_grouped['Impressions']
    df_grouped['CPA'] = df_grouped['Hypothetical Advertiser Cost (Adv Currency)'] / df_grouped['All Last Click + View Conversions']
    
    df_grouped = df_grouped[df_grouped['Impressions'] >= 1000]
    
    df_grouped['CTR_zscore'] = stats.zscore(df_grouped['CTR'])
    df_grouped['CPA_zscore'] = stats.zscore(df_grouped['CPA'])
    df_grouped['composite_score'] = df_grouped['CTR_zscore'] - df_grouped['CPA_zscore']
    
    min_score, max_score = df_grouped['composite_score'].min(), df_grouped['composite_score'].max()
    df_grouped['normalized_score'] = 1 + 99 * (df_grouped['composite_score'] - min_score) / (max_score - min_score)
    
    return df_grouped

def create_chart(df, selected_metric, selected_vertical):
    if selected_metric == 'Normalized Score':
        selected_metric = 'normalized_score'
    
    df_sorted = df.sort_values(selected_metric, ascending=selected_metric == 'CPA')
    top_15 = df_sorted.head(15)
    
    fig = go.Figure(data=[go.Bar(
        y=top_15['3rd Party Data Brand'],
        x=top_15[selected_metric],
        orientation='h'
    )])
    
    x_title = {"CTR": "CTR", "CPA": "CPA ($)", "normalized_score": "Normalized Score"}[selected_metric]
    x_format = '.2%' if selected_metric == 'CTR' else '.2f' if selected_metric == 'CPA' else ''
    
    display_metric = "Normalized Score" if selected_metric == 'normalized_score' else selected_metric
    
    fig.update_layout(
        title=f"Top 15 Brands by {display_metric} for {selected_vertical}",
        yaxis_title="3rd Party Data Brand",
        xaxis_title=x_title,
        xaxis_tickformat=x_format,
        height=600,
        width=800
    )
    
    fig.update_yaxes(autorange="reversed")
    
    return fig, df_sorted

def main():    
    st.set_page_config(layout="wide")
    
    vertical_metrics_df = load_data()
    
    st.sidebar.header("Filters")
    vertical_options = ['All Verticals'] + list(vertical_metrics_df['Vertical'].unique())
    selected_vertical = st.sidebar.selectbox("Select Vertical", options=vertical_options)
    
    df_grouped = prepare_data(vertical_metrics_df, selected_vertical)
    
    selected_metric = st.sidebar.selectbox(
        "Select Metric",
        options=['CTR', 'CPA', 'Normalized Score'],
        help="Normalized Score balances CTR and CPA"
    )
    
    fig, df_sorted = create_chart(df_grouped, selected_metric, selected_vertical)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Data Table")
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)

if check_password():
    main()