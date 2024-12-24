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
import threading
import queue

# Page configuration
st.set_page_config(
    page_title="CrashPredict AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = pd.DataFrame()
if 'model' not in st.session_state:
    st.session_state.model = None
if 'scaler' not in st.session_state:
    st.session_state.scaler = StandardScaler()
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = None
if 'auto_update' not in st.session_state:
    st.session_state.auto_update = False
if 'data_queue' not in st.session_state:
    st.session_state.data_queue = queue.Queue()

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
    .latest-crash {
        font-size: 24px;
        font-weight: bold;
        padding: 15px;
        border-radius: 10px;
        background-color: #2E2E2E;
        margin: 10px 0;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

class CrashGamePredictor:
    def __init__(self):
        self.model = st.session_state.model
        self.scaler = st.session_state.scaler
    
    def scrape_latest_game(self):
        """Simulate scraping the latest game data"""
        try:
            # Simulated latest game data
            latest_data = {
                'timestamp': pd.Timestamp.now(),
                'bet_amount': np.random.uniform(10, 1000),
                'odds': np.random.uniform(1.1, 10.0),
                'crash_point': np.random.uniform(1.0, 15.0),
            }
            return pd.Series(latest_data)
        except Exception as e:
            st.error(f"Error scraping data: {str(e)}")
            return None

    def prepare_features(self, data):
        if len(data) < 1:
            return None, None
        
        # Feature engineering
        data['hour'] = data['timestamp'].dt.hour
        data['minute'] = data['timestamp'].dt.minute
        data['rolling_avg_crash'] = data['crash_point'].rolling(window=5, min_periods=1).mean()
        data['rolling_std_crash'] = data['crash_point'].rolling(window=5, min_periods=1).std()
        data['rolling_min_crash'] = data['crash_point'].rolling(window=5, min_periods=1).min()
        data['rolling_max_crash'] = data['crash_point'].rolling(window=5, min_periods=1).max()
        
        features = ['hour', 'minute', 'rolling_avg_crash', 'rolling_std_crash', 
                   'rolling_min_crash', 'rolling_max_crash']
        X = data[features].fillna(0)
        y = (data['crash_point'] >= data['odds']).astype(int)
        return X, y

    def train_model(self, data):
        X, y = self.prepare_features(data)
        if X is None or len(X) < 10:
            return None
            
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train XGBoost model
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Save model and scaler to session state
        st.session_state.model = self.model
        st.session_state.scaler = self.scaler
        return True

    def predict_crash_point(self, current_data):
        if self.model is None or len(current_data) < 5:
            return None, None
        
        X, _ = self.prepare_features(current_data.tail(10))
        if X is None:
            return None, None
            
        X_latest = X.iloc[-1:].copy()
        X_scaled = self.scaler.transform(X_latest)
        
        # Predict crash point range
        predicted_value = self.model.predict(X_scaled)[0]
        
        # Calculate confidence based on recent prediction accuracy
        recent_predictions = current_data['crash_point'].tail(5)
        confidence = max(0, min(100, 100 - recent_predictions.std() * 10))
        
        return predicted_value, confidence

def update_data():
    predictor = CrashGamePredictor()
    latest_data = predictor.scrape_latest_game()
    
    if latest_data is not None:
        # Add to historical data
        st.session_state.historical_data = pd.concat([
            st.session_state.historical_data,
            pd.DataFrame([latest_data])
        ]).tail(100)  # Keep last 100 records
        
        # Train model periodically
        if len(st.session_state.historical_data) >= 10:
            predictor.train_model(st.session_state.historical_data)
        
        # Make prediction
        predicted_crash, confidence = predictor.predict_crash_point(st.session_state.historical_data)
        if predicted_crash is not None:
            st.session_state.last_prediction = {
                'crash_point': predicted_crash,
                'confidence': confidence
            }

def main():
    st.title("🎮 CrashPredict AI - Live Predictions")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Settings")
        auto_update = st.toggle("Enable Live Updates", value=st.session_state.auto_update)
        update_interval = st.slider("Update Interval (seconds)", 1, 10, 2)
        
        if auto_update != st.session_state.auto_update:
            st.session_state.auto_update = auto_update
            st.experimental_rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Live Game Data")
        if len(st.session_state.historical_data) > 0:
            latest_crash = st.session_state.historical_data['crash_point'].iloc[-1]
            st.markdown(f"""
                <div class='latest-crash'>
                    Latest Crash Point: {latest_crash:.2f}x
                </div>
            """, unsafe_allow_html=True)
        
        # Recent games table
        if not st.session_state.historical_data.empty:
            st.dataframe(
                st.session_state.historical_data.tail(10)[['timestamp', 'crash_point']],
                hide_index=True,
                use_container_width=True
            )
    
    with col2:
        st.subheader("Next Crash Prediction")
        if st.session_state.last_prediction:
            pred = st.session_state.last_prediction
            st.markdown(f"""
                <div class='prediction-box'>
                    <h3>Predicted Crash Point</h3>
                    <h2 style='color: #4CAF50'>{pred['crash_point']:.2f}x</h2>
                    <p>Confidence: {pred['confidence']:.1f}%</p>
                    <p>Recommended Bet: {max(1.0, min(pred['crash_point'] - 0.5, 2.0)):.2f}x</p>
                </div>
            """, unsafe_allow_html=True)
    
    # Auto-update loop
    if st.session_state.auto_update:
        update_data()
        time.sleep(update_interval)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
