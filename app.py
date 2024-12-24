import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="CrashPredict AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'model' not in st.session_state:
    st.session_state.model = None
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = None
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = None

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        width: 100%;
    }
    .prediction-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #2E2E2E;
        margin: 10px 0;
    }
    .metric-card {
        background-color: #2E2E2E;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

class CrashGamePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
    
    def scrape_data(self):
        try:
            # Simulated data for demonstration
            np.random.seed(int(time.time()))
            n_samples = 1000
            data = {
                'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=n_samples, freq='1min'),
                'round_id': range(n_samples),
                'bet_amount': np.random.uniform(10, 1000, n_samples),
                'odds': np.random.uniform(1.1, 10.0, n_samples),
                'crash_point': np.random.uniform(1.0, 15.0, n_samples),
            }
            df = pd.DataFrame(data)
            df['win'] = df['crash_point'] >= df['odds']
            df['profit'] = np.where(df['win'], 
                                  df['bet_amount'] * (df['odds'] - 1),
                                  -df['bet_amount'])
            return df
        except Exception as e:
            st.error(f"Error scraping data: {str(e)}")
            return None

    def prepare_features(self, data):
        # Feature engineering
        data['hour'] = data['timestamp'].dt.hour
        data['minute'] = data['timestamp'].dt.minute
        data['rolling_avg_crash'] = data['crash_point'].rolling(window=10, min_periods=1).mean()
        data['rolling_std_crash'] = data['crash_point'].rolling(window=10, min_periods=1).std()
        
        features = ['bet_amount', 'odds', 'hour', 'minute', 'rolling_avg_crash', 'rolling_std_crash']
        return data[features], data['win']

    def train_model(self, data):
        X, y = self.prepare_features(data)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train XGBoost model
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Calculate accuracy
        accuracy = self.model.score(X_test_scaled, y_test)
        return accuracy

    def predict(self, bet_amount, odds, current_data):
        if self.model is None:
            return None
        
        # Prepare features for prediction
        current_time = pd.Timestamp.now()
        features = pd.DataFrame({
            'bet_amount': [bet_amount],
            'odds': [odds],
            'hour': [current_time.hour],
            'minute': [current_time.minute],
            'rolling_avg_crash': [current_data['crash_point'].tail(10).mean()],
            'rolling_std_crash': [current_data['crash_point'].tail(10).std()]
        })
        
        features_scaled = self.scaler.transform(features)
        probability = self.model.predict_proba(features_scaled)[0][1]
        return probability

def create_metrics_chart(data):
    metrics_data = {
        'Average Crash Point': data['crash_point'].mean(),
        'Win Rate': (data['win'].sum() / len(data)) * 100,
        'Total Profit': data['profit'].sum(),
        'ROI': (data['profit'].sum() / data['bet_amount'].sum()) * 100
    }
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Crash Point", f"{metrics_data['Average Crash Point']:.2f}")
    with col2:
        st.metric("Win Rate", f"{metrics_data['Win Rate']:.1f}%")
    with col3:
        st.metric("Total Profit", f"${metrics_data['Total Profit']:.2f}")
    with col4:
        st.metric("ROI", f"{metrics_data['ROI']:.1f}%")

def create_crash_history_chart(data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['crash_point'],
        mode='lines',
        name='Crash Points',
        line=dict(color='#4CAF50')
    ))
    fig.update_layout(
        title='Crash Point History',
        xaxis_title='Time',
        yaxis_title='Crash Point',
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎮 CrashPredict AI")
    
    predictor = CrashGamePredictor()
    
    with st.sidebar:
        st.header("Controls")
        if st.button("🔄 Scrape New Data"):
            with st.spinner("Scraping data..."):
                data = predictor.scrape_data()
                if data is not None:
                    st.session_state.historical_data = data
                    with st.spinner("Training model..."):
                        accuracy = predictor.train_model(data)
                        st.success(f"Model trained with accuracy: {accuracy:.2%}")
                        st.session_state.model = predictor.model
        
        st.markdown("---")
        st.subheader("Prediction Settings")
        bet_amount = st.number_input("Bet Amount ($)", min_value=1.0, value=100.0, step=10.0)
        odds = st.number_input("Target Odds", min_value=1.1, value=2.0, step=0.1)
        
        if st.button("🎯 Predict"):
            if st.session_state.model is None:
                st.warning("Please scrape data and train the model first")
            else:
                probability = predictor.predict(bet_amount, odds, st.session_state.historical_data)
                st.session_state.last_prediction = probability
    
    if st.session_state.historical_data is not None:
        create_metrics_chart(st.session_state.historical_data)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            create_crash_history_chart(st.session_state.historical_data)
        
        with col2:
            if st.session_state.last_prediction is not None:
                st.markdown("### 🎯 Prediction Results")
                prob_pct = st.session_state.last_prediction * 100
                st.markdown(f"""
                    <div class='prediction-box'>
                        <h4>Win Probability</h4>
                        <h2 style='color: {"#4CAF50" if prob_pct > 50 else "#ff4444"}'>{prob_pct:.1f}%</h2>
                        <p>Expected Value: ${(bet_amount * (odds - 1) * st.session_state.last_prediction - bet_amount * (1 - st.session_state.last_prediction)):.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("### 📊 Recent Games")
            st.dataframe(
                st.session_state.historical_data.tail(5)[['timestamp', 'crash_point', 'win']],
                hide_index=True
            )

if __name__ == "__main__":
    main()
