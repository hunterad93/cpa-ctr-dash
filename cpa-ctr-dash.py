import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["app_password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["app_password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="app_password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="app_password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    # Load the processed data
    @st.cache_data
    def load_data():
        return pd.read_csv('processed_vertical_metrics.csv')

    vertical_metrics_df = load_data()

    # Streamlit app
    st.title("TTD Report Analysis")

    # Sidebar for filters
    st.sidebar.header("Filters")
    vertical_options = ['All Verticals'] + list(vertical_metrics_df['Vertical'].unique())
    selected_vertical = st.sidebar.selectbox(
        "Select Vertical",
        options=vertical_options
    )

    selected_metric = st.sidebar.selectbox(
        "Select Metric",
        options=['CTR', 'CPA']
    )

    # Filter and prepare data
    if selected_vertical == 'All Verticals':
        df_filtered = vertical_metrics_df
    else:
        df_filtered = vertical_metrics_df[vertical_metrics_df['Vertical'] == selected_vertical]

    df_grouped = df_filtered.groupby('3rd Party Data Brand').agg({
        selected_metric: 'mean',
        'Impressions': 'sum'
    }).reset_index()

    df_sorted = df_grouped.sort_values(selected_metric, ascending=True if selected_metric == 'CPA' else False)
    top_10 = df_sorted.head(10)

    # Create chart
    fig = go.Figure(data=[
        go.Bar(
            x=top_10['3rd Party Data Brand'],
            y=top_10[selected_metric]
        )
    ])

    y_title = "CTR" if selected_metric == 'CTR' else "CPA ($)"
    y_format = '.2%' if selected_metric == 'CTR' else '.2f'

    fig.update_layout(
        title=f"Top 10 Brands by {selected_metric} for {selected_vertical}",
        xaxis_title="3rd Party Data Brand",
        yaxis_title=y_title,
        yaxis_tickformat=y_format,
        height=500,
        width=800
    )

    fig.update_xaxes(tickangle=45)

    # Display chart
    st.plotly_chart(fig, use_container_width=True)

    # Display data table
    st.subheader("Data Table")
    st.dataframe(top_10)