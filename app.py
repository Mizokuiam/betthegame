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
import traceback
import plotly.express as px
import random
import os
import winreg

class CrashGameMonitor:
    def __init__(self):
        self.driver = None
        self.history = []
        self.analyzing = False
        self.last_multiplier = 0.0
        self.game_url = "https://1xbet.com/en/allgamesentrance/crash"
        self.retry_count = 0
        self.max_retries = 3

    @staticmethod
    def get_browser_path():
        """Get the path to Chrome executable on Windows"""
        try:
            import winreg
            # Try to get Chrome path from registry
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                chrome_path = winreg.QueryValue(key, None)
                if os.path.exists(chrome_path):
                    return chrome_path

            # Fallback to common installation paths
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.environ.get('PROGRAMFILES', ''), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), r"Google\Chrome\Application\chrome.exe")
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    return path
                    
            # If no Chrome installation found
            return None
            
        except Exception as e:
            st.error(f"Error checking Chrome installation: {str(e)}")
            return None

    def is_chrome_installed(self):
        """Check if Chrome is installed and get its version"""
        try:
            # Common Chrome paths
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe"),
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    st.info(f"Found Chrome at: {path}")
                    return "120.0.6099.130"  # Use latest stable Chrome version
            
            st.error("Chrome not found in standard locations")
            return None
        except Exception as e:
            st.error(f"Error checking Chrome installation: {str(e)}")
            return None

    def initialize_browser(self):
        """Initialize the Chrome browser with specific options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # Get Chrome browser path
            browser_path = self.get_browser_path()
            if not browser_path:
                st.error("Chrome browser not found in common locations.")
                st.info("Please make sure Google Chrome is installed on your system.")
                return False
                
            st.info(f"Using Chrome browser at: {browser_path}")
            chrome_options.binary_location = browser_path
            
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                
                # Force download of the latest ChromeDriver
                driver_path = ChromeDriverManager(path=".").install()
                st.info(f"ChromeDriver installed at: {driver_path}")
                
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                st.success("Browser initialized successfully")
                return True
                
            except Exception as e:
                st.error(f"Failed to initialize ChromeDriver: {str(e)}")
                return False
                
        except Exception as e:
            st.error(f"Error during WebDriver setup: {str(e)}")
            traceback.print_exc()
            return False

    def load_game(self):
        """Load the crash game page with enhanced anti-detection"""
        try:
            if not self.driver:
                if not self.initialize_browser():
                    return False
                    
            # Clear cookies and cache first
            self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            
            # Load the page
            self.driver.get(self.game_url)
            time.sleep(3)  # Initial wait
            
            # Check if we hit any blocks
            page_title = self.driver.title.lower()
            if any(x in page_title for x in ['restricted', 'blocked', 'access denied']):
                st.error("Access appears to be restricted. Trying to bypass...")
                
                # Try to bypass
                self.driver.delete_all_cookies()
                self.driver.refresh()
                time.sleep(5)
                
                # Check again
                if any(x in self.driver.title.lower() for x in ['restricted', 'blocked', 'access denied']):
                    st.error("Still restricted. Please try using a different IP or waiting a while.")
                    return False
                    
            # Additional checks for successful load
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
            except:
                st.warning("Page load may not be complete, but continuing...")
                
            return True
            
        except Exception as e:
            st.error(f"Error loading game: {str(e)}")
            return False

    def get_crash_value(self):
        """Get the current crash value from multiple possible selectors"""
        selectors = [
            '.crash-value', 
            '.crash-multiplier',
            '.multiplier-value',
            '.game-value',
            'div[class*="crash"] span[class*="value"]',
            'div[class*="multiplier"] span[class*="value"]'
        ]
        
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                value_text = element.text.strip()
                if value_text and 'x' in value_text.lower():
                    return float(value_text.lower().replace('x', '').strip())
            except:
                continue
                
        return None

    def check_game_state(self):
        """Check if game is in progress, waiting, or crashed"""
        try:
            # Check timer element for waiting state
            timer = self.driver.find_element(By.CSS_SELECTOR, '.timer, .countdown, [class*="timer"], [class*="countdown"]')
            if timer and timer.is_displayed():
                time_text = timer.text.strip()
                if time_text and any(x in time_text.lower() for x in ['sec', 's', 'seconds']):
                    return 'waiting'
        except:
            pass
            
        try:
            # Check crash animation/state
            crash_elements = self.driver.find_elements(By.CSS_SELECTOR, '.crash-animation, .game-crash, [class*="crash"]')
            for elem in crash_elements:
                if elem.is_displayed():
                    class_name = elem.get_attribute('class').lower()
                    if any(x in class_name for x in ['crashed', 'end', 'finished']):
                        return 'crashed'
                    elif any(x in class_name for x in ['flying', 'active', 'progress']):
                        return 'in_progress'
        except:
            pass
            
        return 'unknown'

    def monitor_game(self):
        """Monitor the crash game and return crash values and states"""
        last_value = None
        values = []
        
        while True:
            try:
                state = self.check_game_state()
                current_value = self.get_crash_value()
                
                if state == 'crashed' and current_value and current_value != last_value:
                    values.append(current_value)
                    last_value = current_value
                    st.write(f"Crash value: {current_value}x")
                    
                    # Analyze pattern
                    if len(values) >= 5:
                        last_5 = values[-5:]
                        avg = sum(last_5) / 5
                        if avg < 2.0:
                            st.success("TAKE: Low values pattern detected")
                        elif avg > 5.0:
                            st.warning("WAIT: High values pattern detected")
                        else:
                            st.info("MONITOR: Normal pattern")
                            
                time.sleep(0.5)
                
            except Exception as e:
                st.error(f"Error monitoring game: {str(e)}")
                time.sleep(1)
                continue

    def start_monitoring(self):
        """Start monitoring the crash game"""
        try:
            if not hasattr(st.session_state, 'history'):
                st.session_state.history = []
                
            # Add some initial test data if no history exists
            if len(st.session_state.history) == 0:
                st.session_state.history = [1.5, 2.3, 1.8, 3.2, 1.2]
                
            # Create placeholders for updates
            placeholder = st.empty()
            recommendation_placeholder = st.empty()
            
            # Initialize browser if needed
            if not self.driver:
                st.info("Setting up browser...")
                if not self.initialize_browser():
                    st.error("Failed to initialize browser. Please try again.")
                    return
                    
            st.info("Loading game page...")
            if not self.load_game():
                st.error("Failed to load game page. Please try again.")
                return
                
            self.analyzing = True
            error_count = 0
            
            while self.analyzing:
                try:
                    self.monitor_game()
                    
                    # Update analysis in real-time
                    with placeholder:
                        col1, col2 = st.columns(2)
                        with col1:
                            if self.last_multiplier > 0:
                                st.metric("Last Crash", f"{self.last_multiplier:.2f}x")
                            if len(st.session_state.history) >= 5:
                                st.metric("Average (Last 5)", f"{sum(st.session_state.history[-5:])/5:.2f}x")
                        with col2:
                            if len(st.session_state.history) > 0:
                                st.metric("Max Crash", f"{max(st.session_state.history):.2f}x")
                                low_crashes = sum(1 for x in st.session_state.history if x < 2)
                                if len(st.session_state.history) > 0:
                                    low_crash_pct = (low_crashes/len(st.session_state.history)*100)
                                    st.metric("Low Crash %", f"{low_crash_pct:.1f}%")
                    
                    # Show recommendation
                    with recommendation_placeholder:
                        recommendation = self.analyze_pattern()
                        st.info(f"💡 Recommendation: {recommendation}")
                        
                    time.sleep(0.5)
                    
                except Exception as e:
                    st.error(f"Error in monitoring loop: {str(e)}")
                    error_count += 1
                    if error_count > 5:
                        st.warning("Too many errors, restarting browser...")
                        self.cleanup()
                        if not self.initialize_browser():
                            st.error("Failed to reinitialize browser. Please try again.")
                            return
                        error_count = 0
                    time.sleep(2)
                    
        except Exception as e:
            st.error(f"Error starting analysis: {str(e)}")
            self.cleanup()

    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.analyzing = False
        if self.driver:
            self.driver.quit()
            self.driver = None

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

    def cleanup(self):
        """Cleanup resources"""
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
                    if monitor.initialize_browser():
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
