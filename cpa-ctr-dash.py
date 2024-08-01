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
    df = pd.read_csv('aggregated_metrics.csv')
    df['3rd Party Data ID'] = df['3rd Party Data ID'].astype(str).str[:-2] + ' ' + df['3rd Party Data Brand']
    return df

def filter_data(df, selected_vertical):
    if selected_vertical == 'All Verticals':
        return df
    return df[df['Vertical'] == selected_vertical]

def aggregate_data(df, grouping_field):
    return df.groupby(grouping_field).agg({
        'Clicks': 'sum',
        'Impressions': 'sum',
        'Hypothetical Advertiser Cost (Adv Currency)': 'sum',
        'All Last Click + View Conversions': 'sum'
    }).reset_index()

def calculate_metrics(df, grouping_field):
    df['CTR'] = df['Clicks'] / df['Impressions']
    df['CPC'] = df['Hypothetical Advertiser Cost (Adv Currency)'] / df['Clicks']
    
    # Filter out invalid metrics
    df = df[~df['CPC'].isin([np.inf, -np.inf, np.nan])]
    df = df[df['CPC'] > 0]
    
    impression_threshold = 5000 if grouping_field == '3rd Party Data Brand' else 1000
    return df[df['Impressions'] >= impression_threshold]

def calculate_scores(df):
    df['CTR_zscore'] = stats.zscore(df['CTR'])
    df['CPC_zscore'] = stats.zscore(df['CPC'])
    df['composite_score'] = df['CTR_zscore'] - df['CPC_zscore']
    
    min_score, max_score = df['composite_score'].min(), df['composite_score'].max()
    df['normalized_score'] = 1 + 99 * (df['composite_score'] - min_score) / (max_score - min_score)
    return df

def prepare_data(df, selected_vertical, grouping_field):
    filtered_df = filter_data(df, selected_vertical)
    aggregated_df = aggregate_data(filtered_df, grouping_field)
    df_with_metrics = calculate_metrics(aggregated_df, grouping_field)
    return calculate_scores(df_with_metrics)


def create_chart(df, selected_metric, selected_vertical, grouping_field):
    if selected_metric == 'Normalized Score':
        selected_metric = 'normalized_score'
    
    df_sorted = df.sort_values(selected_metric, ascending=selected_metric == 'CPC')
    top_15 = df_sorted.head(15)
    
    fig = go.Figure(data=[go.Bar(
        y=top_15[grouping_field],
        x=top_15[selected_metric],
        orientation='h'
    )])
    
    x_title = {"CTR": "CTR", "CPC": "CPC ($)", "normalized_score": "Normalized Score"}[selected_metric]
    x_format = '.2%' if selected_metric == 'CTR' else '.2f' if selected_metric == 'CPC' else ''
    
    display_metric = "Normalized Score" if selected_metric == 'normalized_score' else selected_metric
    
    fig.update_layout(
        title=f"Top 15 {grouping_field}s by {display_metric} for {selected_vertical}",
        yaxis_title=grouping_field,
        xaxis_title=x_title,
        xaxis_tickformat=x_format,
        height=600,
        width=800
    )
    
    fig.update_yaxes(autorange="reversed", type='category')
    
    return fig, df_sorted

def display_chart_and_table(fig, df_sorted):
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Data Table")
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)

def main():    
    st.set_page_config(layout="wide")
    
    vertical_metrics_df = load_data()

    grouping_options = {
        'Brand': '3rd Party Data Brand',
        'Segment ID': '3rd Party Data ID'
    }

    grouping_selection = st.sidebar.selectbox(
        "Aggregate by",
        options=list(grouping_options.keys()),
        help="Choose to view results by Brand or individual Segment ID"
    )

    grouping_field = grouping_options[grouping_selection]
    
    vertical_options = ['All Verticals'] + list(vertical_metrics_df['Vertical'].unique())
    selected_vertical = st.sidebar.selectbox("Select Vertical", options=vertical_options)
    
    df_grouped = prepare_data(vertical_metrics_df, selected_vertical, grouping_field)
    
    selected_metric = st.sidebar.selectbox(
        "Select Metric",
        options=['CTR', 'CPC', 'Normalized Score'],
        help="Normalized Score balances CTR and CPC"
    )
    
    fig, df_sorted = create_chart(df_grouped, selected_metric, selected_vertical, grouping_field)
    display_chart_and_table(fig, df_sorted)

if check_password():
    main()