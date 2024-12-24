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
        self.game_url = "https://1xbet.com/en/allgamesentrance/crash"
        
    def setup_driver(self):
        """Setup and return a configured Chrome driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--start-maximized')
            
            # Add more realistic user agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Add additional preferences to avoid detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver with enhanced capabilities
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Execute CDP commands to modify navigator.webdriver flag
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Add stealth JS
            stealth_js = """
            // Overwrite the languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es'],
            });
            
            // Overwrite plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            """
            driver.execute_script(stealth_js)
            
            return driver
            
        except Exception as e:
            st.error(f"Error setting up browser: {str(e)}")
            return None

    def load_game(self):
        """Load the crash game page with enhanced anti-detection"""
        try:
            if not self.driver:
                self.driver = self.setup_driver()
                if not self.driver:
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
        if not self.driver:
            st.error("Browser not initialized. Please try again.")
            return

        try:
            st.info("Loading game page...")
            if not self.load_game():
                return
            
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
                    self.monitor_game()
                    
                    # Update analysis in real-time
                    with placeholder:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Last Crash", f"{self.last_multiplier:.2f}x")
                            st.metric("Average (Last 5)", f"{sum(st.session_state.history[-5:])/5:.2f}x")
                        with col2:
                            st.metric("Max Crash", f"{max(st.session_state.history):.2f}x")
                            st.metric("Low Crash %", f"{(sum(1 for x in st.session_state.history if x < 2)/len(st.session_state.history)*100):.1f}%")
                    
                    # Show recommendation
                    with recommendation_placeholder:
                        recommendation = self.analyze_pattern()
                        st.info(f"💡 Recommendation: {recommendation}")
                        
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
