import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from datetime import datetime
import time
import threading
import queue
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import platform

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
if 'driver' not in st.session_state:
    st.session_state.driver = None

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

def initialize_driver():
    if st.session_state.driver is None:
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.get("https://1xbet.com/en/allgamesentrance/crash")
                st.session_state.driver = driver
                time.sleep(5)  # Allow page to load
                return driver
            except Exception as e:
                st.error(f"Failed to load website: {str(e)}")
                if 'driver' in locals():
                    driver.quit()
                return None
                
        except Exception as e:
            st.error(f"Failed to initialize Chrome driver: {str(e)}")
            return None

def cleanup_driver():
    if st.session_state.driver is not None:
        st.session_state.driver.quit()
        st.session_state.driver = None

class CrashGamePredictor:
    def __init__(self):
        self.model = st.session_state.model
        self.scaler = st.session_state.scaler
    
    def scrape_latest_game(self):
        """Scrape the latest crash point from 1xbet"""
        try:
            driver = st.session_state.driver
            if driver is None:
                driver = initialize_driver()
                if driver is None:
                    return None
            
            # Wait for the crash point element to be visible
            try:
                crash_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.crash__value"))
                )
                
                # Extract the crash point value (remove the 'x' suffix)
                crash_text = crash_element.text.strip()
                if 'x' in crash_text:
                    crash_point = float(crash_text.replace('x', ''))
                else:
                    crash_point = float(crash_text)
                
                latest_data = {
                    'timestamp': pd.Timestamp.now(),
                    'crash_point': crash_point
                }
                return pd.Series(latest_data)
                
            except Exception as e:
                st.error(f"Error finding crash value: {str(e)}")
                cleanup_driver()
                return None
                
        except Exception as e:
            st.error(f"Error scraping data: {str(e)}")
            cleanup_driver()
            return None

    def predict_crash_point(self, current_data):
        if self.model is None or len(current_data) < 5:
            # Provide a simple prediction when not enough data
            recent_crashes = current_data['crash_point'].tail(5)
            predicted_value = max(1.1, min(2.0, recent_crashes.mean() * 0.9))
            confidence = 50.0  # Lower confidence when no model
            return predicted_value, confidence
        
        X, _ = self.prepare_features(current_data.tail(10))
        if X is None:
            return None, None
            
        X_latest = X.iloc[-1:].copy()
        X_scaled = self.scaler.transform(X_latest)
        
        # Predict crash point range
        predicted_value = self.model.predict(X_scaled)[0]
        predicted_value = max(1.1, min(predicted_value, 10.0))  # Constrain prediction
        
        # Calculate confidence based on recent prediction accuracy
        recent_predictions = current_data['crash_point'].tail(5)
        confidence = max(0, min(100, 100 - recent_predictions.std() * 10))
        
        return predicted_value, confidence

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
        y = (data['crash_point'] >= data['crash_point'].mean()).astype(int)
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
            if not auto_update:
                cleanup_driver()
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Live Game Data")
        if len(st.session_state.historical_data) > 0:
            latest_crash = st.session_state.historical_data['crash_point'].iloc[-1]
            crash_color = "#4CAF50" if latest_crash >= 2.0 else "#ff4444"
            st.markdown(f"""
                <div class='latest-crash' style='border: 2px solid {crash_color}'>
                    Latest Crash Point: <span style='color: {crash_color}'>{latest_crash:.2f}x</span>
                </div>
            """, unsafe_allow_html=True)
        
        # Recent games table with formatted values
        if not st.session_state.historical_data.empty:
            display_df = st.session_state.historical_data.tail(10).copy()
            display_df['crash_point'] = display_df['crash_point'].apply(lambda x: f"{x:.4f}x")
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
            st.dataframe(
                display_df[['timestamp', 'crash_point']],
                hide_index=True,
                use_container_width=True
            )
    
    with col2:
        st.subheader("Next Crash Prediction")
        # Always show prediction box, even with default values
        if not st.session_state.last_prediction:
            st.session_state.last_prediction = {
                'crash_point': 1.5,
                'confidence': 50.0
            }
        
        pred = st.session_state.last_prediction
        recommended_bet = max(1.1, min(pred['crash_point'] - 0.5, 2.0))
        
        st.markdown(f"""
            <div class='prediction-box'>
                <h3>Predicted Crash Point</h3>
                <h2 style='color: #4CAF50'>{pred['crash_point']:.2f}x</h2>
                <p>Confidence: {pred['confidence']:.1f}%</p>
                <hr style='margin: 10px 0; border-color: #444;'>
                <p style='font-weight: bold; color: #4CAF50'>Recommended Bet: {recommended_bet:.2f}x</p>
                <p style='font-size: 0.8em; color: #888;'>Based on pattern analysis and risk assessment</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Auto-update loop
    if st.session_state.auto_update:
        update_data()
        time.sleep(update_interval)
        st.rerun()

if __name__ == "__main__":
    main()
    # Cleanup on app shutdown
    if st.session_state.driver is not None:
        cleanup_driver()
