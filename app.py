import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from pathlib import Path
import platform
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import traceback
import plotly.express as px

class CrashGameMonitor:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.logged_in = False
        self.balance = 0.0
        self.history = []
        self.analyzing = False
        self.last_multiplier = 0.0
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            # Add stealth settings
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            st.sidebar.text("Setting up browser...")
            
            if platform.system() == 'Linux':
                st.sidebar.text("Running on Linux, using system Chrome...")
                service = Service()
            else:
                service = Service(ChromeDriverManager().install())

            st.sidebar.text("Creating WebDriver instance...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set window size
            self.driver.set_window_size(1920, 1080)
            
            # Add stealth JavaScript
            st.sidebar.text("Setting up stealth mode...")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Setup wait
            self.wait = WebDriverWait(self.driver, 10)
            return True
            
        except Exception as e:
            st.sidebar.error(f"Failed to setup browser: {str(e)}")
            if hasattr(e, '__traceback__'):
                st.sidebar.error(f"Traceback: {traceback.format_exc()}")
            return False

    def analyze_game(self):
        """Analyze the crash game and provide recommendations"""
        try:
            if not self.driver:
                return
            
            # Get current multiplier
            try:
                multiplier_elem = self.wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, ".crash-multiplier, .multiplier, .current-multiplier"
                )))
                current_multiplier = float(multiplier_elem.text.replace('x', '').strip())
                
                if current_multiplier != self.last_multiplier:
                    self.last_multiplier = current_multiplier
                    self.history.append(current_multiplier)
                    
                    # Keep last 50 rounds
                    if len(self.history) > 50:
                        self.history = self.history[-50:]
                    
                    # Analyze patterns
                    self.analyze_patterns()
                    
            except Exception as e:
                st.sidebar.warning(f"Could not get multiplier: {str(e)}")
                
        except Exception as e:
            st.sidebar.error(f"Analysis error: {str(e)}")

    def analyze_patterns(self):
        """Analyze crash patterns and make recommendations"""
        if len(self.history) < 5:
            return
        
        # Calculate statistics
        avg_multiplier = sum(self.history) / len(self.history)
        max_multiplier = max(self.history)
        min_multiplier = min(self.history)
        
        # Count crashes below 2x
        low_crashes = sum(1 for x in self.history if x < 2)
        low_crash_percent = (low_crashes / len(self.history)) * 100
        
        # Analyze recent trend
        recent_trend = self.history[-5:]
        trend_increasing = all(recent_trend[i] <= recent_trend[i+1] for i in range(len(recent_trend)-1))
        trend_decreasing = all(recent_trend[i] >= recent_trend[i+1] for i in range(len(recent_trend)-1))
        
        # Make recommendations
        st.sidebar.markdown("### Analysis")
        st.sidebar.write(f"Last crash: {self.last_multiplier}x")
        st.sidebar.write(f"Average multiplier: {avg_multiplier:.2f}x")
        st.sidebar.write(f"Max multiplier: {max_multiplier:.2f}x")
        st.sidebar.write(f"Min multiplier: {min_multiplier:.2f}x")
        st.sidebar.write(f"Low crashes (<2x): {low_crash_percent:.1f}%")
        
        st.sidebar.markdown("### Recommendations")
        if trend_increasing:
            st.sidebar.warning("⚠️ Trend is increasing - higher risk of crash")
        elif trend_decreasing:
            st.sidebar.success("✅ Trend is decreasing - potential opportunity")
        
        if low_crash_percent > 60:
            st.sidebar.warning("⚠️ High frequency of low crashes - be cautious")
        elif low_crash_percent < 40:
            st.sidebar.success("✅ Low frequency of crashes - favorable conditions")
        
        # Show recent history
        st.sidebar.markdown("### Recent History")
        history_str = " → ".join([f"{x:.2f}x" for x in self.history[-10:]])
        st.sidebar.write(history_str)

def main():
    st.set_page_config(page_title="1xBet Crash Game Analyzer", layout="wide")
    
    # Initialize session state
    if 'monitor' not in st.session_state:
        st.session_state.monitor = CrashGameMonitor()
        st.session_state.analyzing = False
    
    st.title("1xBet Crash Game Analyzer")
    
    # Create two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Embed 1xBet website
        st.markdown("### 1xBet Website")
        st.markdown("""
        1. Login to your 1xBet account
        2. Navigate to the Crash game
        3. Click 'Start Analysis' in the sidebar
        """)
        st.components.v1.iframe("https://1xbet.com", height=800, scrolling=True)
    
    with col2:
        st.markdown("### Game Analysis")
        if st.button("Start Analysis", disabled=st.session_state.analyzing):
            st.session_state.analyzing = True
            if not st.session_state.monitor.driver:
                if st.session_state.monitor.setup_driver():
                    st.success("Browser setup successful")
                else:
                    st.error("Failed to setup browser")
                    st.session_state.analyzing = False
                    return
        
        if st.session_state.analyzing:
            st.session_state.monitor.analyze_game()
            
            # Show analysis results
            if st.session_state.monitor.history:
                # Create line chart of multipliers
                df = pd.DataFrame({
                    'Round': range(len(st.session_state.monitor.history)),
                    'Multiplier': st.session_state.monitor.history
                })
                
                fig = px.line(df, x='Round', y='Multiplier', 
                            title='Crash History',
                            labels={'Multiplier': 'Crash Multiplier', 'Round': 'Game Round'})
                fig.add_hline(y=2.0, line_dash="dash", line_color="red", 
                            annotation_text="2x threshold")
                st.plotly_chart(fig)
        
        if st.button("Stop Analysis", disabled=not st.session_state.analyzing):
            st.session_state.analyzing = False
            if st.session_state.monitor.driver:
                st.session_state.monitor.driver.quit()
                st.session_state.monitor.driver = None
            st.success("Analysis stopped")

if __name__ == "__main__":
    main()
