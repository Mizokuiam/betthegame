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
            chrome_options.add_argument('--headless=new')
            
            # Add stealth settings
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
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

    def get_crash_value(self):
        """Get the current crash value from the game"""
        try:
            # Try multiple possible selectors
            selectors = [
                ".crash-value",
                ".multiplier",
                ".current-multiplier",
                "[data-role='multiplier']",
                ".crash-multiplier",
                "#crash-value",
                ".game-multiplier"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for elem in elements:
                            try:
                                value_text = elem.text.strip()
                                if 'x' in value_text.lower():
                                    return float(value_text.lower().replace('x', '').strip())
                            except:
                                continue
                except:
                    continue
                    
            # If we couldn't find the value, let's get the page source for debugging
            st.warning("Could not find crash value. Checking page source...")
            page_source = self.driver.page_source
            if "multiplier" in page_source.lower():
                st.info("Found 'multiplier' in page source. Selector might need updating.")
            
            return None
            
        except Exception as e:
            st.error(f"Error getting crash value: {str(e)}")
            return None

    def analyze_pattern(self):
        """Analyze crash pattern and provide recommendation"""
        if len(self.history) < 5:
            return "Need more data for analysis"
            
        last_5 = self.history[-5:]
        avg_5 = sum(last_5) / 5
        
        if avg_5 < 1.8:
            return "TAKE: High chance of bigger crash (2x+)"
        elif all(x < 2 for x in last_5):
            return "TAKE: Due for a high crash"
        elif all(x > 2 for x in last_5):
            return "WAIT: High crash streak, likely to break"
        else:
            return "MONITOR: No clear pattern"

    def start_monitoring(self):
        """Start monitoring the crash game"""
        if not self.driver:
            st.error("Browser not initialized. Please try again.")
            return

        try:
            st.info("Loading game page...")
            self.driver.get("https://1xbet.com/en/allgamesentrance/crash")
            
            # Wait for page to load
            time.sleep(5)
            
            st.info("Checking page title...")
            st.write(f"Page Title: {self.driver.title}")
            
            # Log if we're on the right page
            if "crash" in self.driver.current_url.lower():
                st.success("Successfully loaded the crash game page")
            else:
                st.warning(f"Current URL: {self.driver.current_url}")
            
            self.analyzing = True
            
            if 'history' not in st.session_state:
                st.session_state.history = []
                
            placeholder = st.empty()
            recommendation_placeholder = st.empty()
            
            # Add initial test data
            if not st.session_state.history:
                st.session_state.history = [1.5, 2.3, 1.8, 3.2, 1.2]
                st.info("Added initial test data")
            
            error_count = 0
            while self.analyzing:
                try:
                    current_value = self.get_crash_value()
                    if current_value:
                        error_count = 0  # Reset error count on success
                        if current_value != self.last_multiplier:
                            self.last_multiplier = current_value
                            st.session_state.history.append(current_value)
                            
                            # Update analysis in real-time
                            with placeholder:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Last Crash", f"{current_value:.2f}x")
                                    st.metric("Average (Last 5)", f"{sum(st.session_state.history[-5:])/5:.2f}x")
                                with col2:
                                    st.metric("Max Crash", f"{max(st.session_state.history):.2f}x")
                                    st.metric("Low Crash %", f"{(sum(1 for x in st.session_state.history if x < 2)/len(st.session_state.history)*100):.1f}%")
                            
                            # Show recommendation
                            with recommendation_placeholder:
                                recommendation = self.analyze_pattern()
                                st.info(f"💡 Recommendation: {recommendation}")
                    else:
                        error_count += 1
                        if error_count >= 5:  # After 5 consecutive errors
                            st.warning("Having trouble getting crash values. Refreshing page...")
                            self.driver.refresh()
                            time.sleep(5)
                            error_count = 0
                            
                except Exception as e:
                    st.error(f"Error in monitoring loop: {str(e)}")
                    time.sleep(2)
                
                time.sleep(1)
                
        except Exception as e:
            st.error(f"Error accessing the game: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None

    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.analyzing = False
        if self.driver:
            self.driver.quit()
            self.driver = None

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
        
        st.link_button("Open 1xBet Crash Game", "https://1xbet.com/en/allgamesentrance/crash")
        
        if 'monitor' not in st.session_state:
            st.session_state.monitor = None
            
        if st.button("Start Analysis"):
            if st.session_state.monitor is None:
                with st.spinner("Setting up browser..."):
                    monitor = CrashGameMonitor()
                    if monitor.setup_driver():
                        st.session_state.monitor = monitor
                        monitor.start_monitoring()
                    else:
                        st.error("Failed to initialize browser. Please try again.")
                        
        if st.button("Stop Analysis", disabled=st.session_state.monitor is None):
            if st.session_state.monitor:
                st.session_state.monitor.stop_monitoring()
                st.session_state.monitor = None
                st.success("Analysis stopped")
    
    with col2:
        st.header("Analysis")
        
        # Display analysis results
        if 'history' in st.session_state and len(st.session_state.history) > 0:
            df = pd.DataFrame({'multiplier': st.session_state.history})
            
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
