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
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            
            # Add stealth settings
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            try:
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.wait = WebDriverWait(self.driver, 10)
                return True
            except Exception as e:
                st.error(f"Failed to create Chrome WebDriver: {str(e)}")
                return False
                
        except Exception as e:
            st.error(f"Failed to setup Chrome options: {str(e)}")
            return False

    def start_monitoring(self):
        """Start monitoring the crash game"""
        if not self.driver:
            st.error("Browser not initialized. Please try again.")
            return

        try:
            self.driver.get("https://1xbet.com/casino/games/provider/1xGames/crash")
            st.success("Successfully loaded the crash game page")
            
            # Start monitoring in session state
            if 'history' not in st.session_state:
                st.session_state.history = []
            
            # Add some sample data for testing
            st.session_state.history.extend([1.5, 2.3, 1.8, 3.2, 1.2])
            
        except Exception as e:
            st.error(f"Error accessing the game: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None

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
    st.set_page_config(page_title="Crash Game Analyzer", layout="wide")
    
    st.title("Crash Game Analyzer")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Instructions")
        st.markdown("""
        1. Click the button below to open 1xBet Crash Game in a new tab
        2. Log in to your account
        3. Navigate to the Crash game
        4. Return to this window and start the analysis
        """)
        
        st.link_button("Open 1xBet Crash Game", "https://1xbet.com/casino/games/provider/1xGames/crash")
        
        if st.button("Start Analysis"):
            with st.spinner("Setting up browser..."):
                monitor = CrashGameMonitor()
                if monitor.setup_driver():
                    monitor.start_monitoring()
                else:
                    st.error("Failed to initialize browser. Please try again or contact support.")
    
    with col2:
        st.header("Analysis")
        
        # Display analysis results
        if 'history' in st.session_state and len(st.session_state.history) > 0:
            df = pd.DataFrame({'multiplier': st.session_state.history})
            
            # Display stats
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.metric("Last Crash", f"{st.session_state.history[-1]:.2f}x")
                st.metric("Average Multiplier", f"{df['multiplier'].mean():.2f}x")
            with col_stats2:
                st.metric("Max Multiplier", f"{df['multiplier'].max():.2f}x")
                st.metric("Low Crash %", f"{(df['multiplier'] < 2).mean()*100:.1f}%")
            
            # Plot trend
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=df['multiplier'], mode='lines+markers', name='Crash Values'))
            fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="2x threshold")
            fig.update_layout(title="Crash History", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show last 10 crashes
            st.subheader("Last 10 Crashes")
            st.write(" → ".join([f"{x:.2f}x" for x in df['multiplier'].tail(10)]))
        else:
            st.info("Start the analysis to see crash game statistics")

if __name__ == "__main__":
    main()
