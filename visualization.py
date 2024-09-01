import streamlit as st
import requests
import pandas as pd
import seaborn as sns
import io
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
 
st.set_page_config(page_title="Data Visualization", page_icon="📊",layout='wide')



# Fetching data from the API for a given strategy.
@st.cache_data
def fetch_api_data(strategy_name, start=None, end=None, stats=True):
    url = 'https://jarvis.untrade.io/docs#/default/get_backtest_result_api_v1_get_backtest_result_get'
    params = {
        'strategy_name': str(strategy_name).lower(),
        'start': start,
        'end': end,
        'stats':stats
    }
    headers = {'accept': 'application/json'}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        static_data = data['results']['Static'] if 'Static' in data['results'] else {}
        compounding_data = data['results']['Compounding'] if 'Compounding' in data['results'] else {}
        balance_data = data['balances'] if 'balances' in data else []
        df_static = pd.DataFrame([static_data]) if static_data else pd.DataFrame()
        df_compounding = pd.DataFrame([compounding_data]) if compounding_data else pd.DataFrame()
        df_balance = pd.DataFrame(balance_data) if balance_data else pd.DataFrame()
        return df_static, df_compounding, df_balance
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
    return None, None, None

# Fetching data from the API for backtesting.
def upload_logs_for_backtest(file, futures, chain, commission, stats):
    url = 'https://jarvis.untrade.io/api/v1/backtest_engine'
    params = create_request_params(futures, chain, commission, stats)
    headers, files = create_request_headers_and_files(futures, file)
    try:
        response = requests.post(url, params=params, headers=headers, files=files)
        return process_backtest_response(response)
    except Exception as e:
        st.error(f"Error uploading logs for backtest: {str(e)}")
        return None, None
    

#Dictionary of request parameters
def create_request_params(futures, chain, commission, stats):
    params = {
        'futures': str(futures),
        'chain': str(chain),
        'commission': str(commission),
        'stats': str(stats)
    }
    return params


#headers and files for a request based on parameter.
def create_request_headers_and_files(futures, file):
    if futures:
        headers = {'accept': 'text/csv'}
        files = {'file': ('logs.csv', file, 'text/csv')}
    else:
        headers = {'accept': 'application/json'}
        files = None
    return headers, files

#Processes the response from a backtest API request.
def process_backtest_response(response):
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = response.json()
            if 'results' in data and 'Static' in data['results'] and 'Compounding' in data['results']:
                static_data = data['results']['Static']
                compounding_data = data['results']['Compounding']
                balance_data = data['balances'] if 'balances' in data else []
                df_static = pd.DataFrame(static_data.items(), columns=['Static', 'Value'])
                df_compounding = pd.DataFrame(compounding_data.items(), columns=['Compounding', 'Value'])
                df_balance = pd.DataFrame(balance_data) if balance_data else pd.DataFrame()
                return df_static, df_compounding,df_balance
            else:
                st.error("JSON structure does not match the expected format")
                return None, None
        elif 'text/csv' in content_type:
            return response.content.decode('utf-8'), 'csv'
        
        else:
            st.error("Received an unsupported response format from API")
            return None, None
    else:
        st.error(f"Error uploading logs for backtest: {response.status_code}, {response.text}")
        return None, None

#Streamlit logic to visualize strategy logs, backtest results, stock data, and PNL data.      
def visualize_data():
    #strategy logs
    st.subheader("Stats logs")
    st.write("Please enter the strategy details:")
    strategy_name = st.text_input("Strategy Name:")
    start = st.text_input("Start Date/Time YYYY-MM-DD HH:MM:")
    end = st.text_input("End Date/Time YYYY-MM-DD HH:MM:")
    stats = st.checkbox("Stats",key="stats_checkbox",value=True)
    if strategy_name:
        df_static, df_compounding, df_balance = fetch_api_data(strategy_name, start, end, stats)
        if df_static is not None and df_compounding is not None and df_balance is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.write("Static Data:")
                st.dataframe(df_static.transpose(), width=800)
            with col2:
                st.write("Compounding Data:")
                st.dataframe(df_compounding.transpose(), width=800)
            st.write('Balance Data:')
            st.dataframe(df_balance.transpose(),width=800)
            #Visualization 
            if not df_balance.empty:
                visualize_button = st.button("Visualize")
                if visualize_button:
                    fig = px.line(df_balance, x='timestamp', y='balance', title='Balance Over Time')
                    st.plotly_chart(fig)

    
    #backtest results
    st.subheader("Backtest")
    backtest_file = st.file_uploader("Choose a CSV file for backtest", type=["csv"])
    if backtest_file is not None:
        futures = st.checkbox("Futures", value=True)
        chain = st.checkbox("Chain", value=False)
        commission = st.slider("Commission", 0.0, 1.0, 0.15)
        stats = st.checkbox("Stats", value=True)
        if not stats and futures:
            csv_content, _ = upload_logs_for_backtest(backtest_file, futures, chain, commission, stats)
            if csv_content is not None:
                df = pd.read_csv(io.StringIO(csv_content))
                balance=1000
                for i in range(len(df)):
                    profit=df.iloc[i]['profit']
                    balance+=profit
                    df.at[i,'balance (Initially 1000)']=balance
                st.write("Data:")
                st.dataframe(df, width=800)
                fig=px.line(df,x='exit_at',y='balance (Initially 1000)',title='Bakance Over Time')
                st.plotly_chart(fig)
                st.download_button(
                    label="Download logs",
                    data=csv_content,
                    file_name="logs.csv",
                    key="download_button")
        else:
            df_static, df_compounding, df_balance = upload_logs_for_backtest(backtest_file, futures, chain, commission, stats)
            if df_static is not None and df_compounding is not None and df_balance is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("Static Data:")
                    st.dataframe(df_static, width=800)
                with col2:
                    st.write("Compounding Data:")
                    st.dataframe(df_compounding, width=800)
                st.write('Balance Data:')
                st.dataframe(df_balance.transpose(),width=800)
                #Visualization 
                if not df_balance.empty:
                    visualize_button = st.button("Visualization")
                    if visualize_button:
                        fig = px.line(df_balance, x='timestamp', y='balance', title='Balance Over Time')
                        st.plotly_chart(fig)
                if not stats and not futures:
                    csv_content, _ = upload_logs_for_backtest(backtest_file, futures, chain, commission, stats)
                    if csv_content is not None:
                        df = pd.read_csv(io.StringIO(csv_content))
                        st.download_button(
                            label="Download CSV",
                            data=csv_content,
                            file_name="backtest_results.csv",
                            key="download_button")
            else:
                st.error("No data received from backtest API or there was an error.")

#Main function for the Streamlit web application.
def main():
    st.markdown("<h1 style='text-align: center; color: #143047; line-height: 1.5;'>ZeltaTech</h1>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>Let's Visualize</h1>", unsafe_allow_html=True)
    visualize_data()

if __name__ == "__main__":
    main()
