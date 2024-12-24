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

class CrashGameMonitor:
    def __init__(self):
        self.crash_history = []
        self.current_multiplier = None
        self.game_state = None
        self.driver = None
        self.wait = None
        self.data_file = Path("crash_history.json")
        self.load_history()

    def load_history(self):
        """Load crash history from file if it exists"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.crash_history = data.get('history', [])
                    st.sidebar.success(f"Loaded {len(self.crash_history)} historical records")
            except Exception as e:
                st.sidebar.error(f"Error loading history: {e}")

    def save_history(self):
        """Save crash history to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump({'history': self.crash_history}, f)
        except Exception as e:
            st.sidebar.error(f"Error saving history: {e}")

    def setup_driver(self):
        """Initialize Chrome driver with headless mode for Streamlit Cloud"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            import platform

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Check if running on Linux (Debian)
            if platform.system() == 'Linux':
                chrome_options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
            else:
                # For local development
                try:
                    service = Service()
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    st.warning(f"Using ChromeDriverManager as fallback: {str(e)}")
                    service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            st.success("Browser initialized successfully!")
            return True
        except Exception as e:
            st.error(f"Failed to initialize browser: {str(e)}")
            return False

    def monitor_game_state(self):
        """Monitor current game state and multiplier"""
        try:
            # Check game state
            try:
                state_elem = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".crash-wrapper")))
                if "preparing" in state_elem.get_attribute("class"):
                    self.game_state = "preparing"
                elif "flying" in state_elem.get_attribute("class"):
                    self.game_state = "flying"
                else:
                    self.game_state = "crashed"
            except:
                self.game_state = "unknown"

            # Get current multiplier
            try:
                multiplier_elem = self.driver.find_element(By.CSS_SELECTOR, ".multiplier")
                multiplier_text = multiplier_elem.text.strip().replace('×', '')
                self.current_multiplier = float(multiplier_text)
            except:
                self.current_multiplier = None

            # Record crash value
            if self.game_state == "crashed" and self.current_multiplier:
                self.crash_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'value': self.current_multiplier
                })
                self.save_history()

            return self.game_state, self.current_multiplier
        except Exception as e:
            st.error(f"Error monitoring game state: {str(e)}")
            return "error", None

    def analyze_patterns(self):
        """Analyze crash patterns and generate recommendations"""
        if len(self.crash_history) < 10:
            return None

        recent_crashes = [crash['value'] for crash in self.crash_history[-10:]]
        
        analysis = {
            'average': np.mean(recent_crashes),
            'median': np.median(recent_crashes),
            'min': np.min(recent_crashes),
            'max': np.max(recent_crashes),
            'volatility': np.std(recent_crashes),
            'trend': 'neutral'
        }

        # Detect trend
        if all(recent_crashes[i] <= recent_crashes[i+1] for i in range(len(recent_crashes)-2)):
            analysis['trend'] = 'increasing'
        elif all(recent_crashes[i] >= recent_crashes[i+1] for i in range(len(recent_crashes)-2)):
            analysis['trend'] = 'decreasing'

        # Generate recommendations
        if analysis['trend'] == 'decreasing':
            analysis['target_multiplier'] = min(1.5, analysis['min'] * 0.9)
            analysis['bet_amount'] = 3  # Conservative
        elif analysis['trend'] == 'increasing':
            analysis['target_multiplier'] = min(2.0, analysis['average'] * 0.8)
            analysis['bet_amount'] = 10  # Aggressive
        else:
            analysis['target_multiplier'] = min(1.8, analysis['average'] * 0.7)
            analysis['bet_amount'] = 5  # Moderate

        return analysis

def render_sidebar():
    """Render sidebar with controls and info"""
    st.sidebar.title("⚙️ Controls")
    
    # Add monitoring controls
    if 'monitor' not in st.session_state:
        st.session_state.monitor = CrashGameMonitor()
        st.session_state.monitoring = False

    if not st.session_state.monitoring:
        if st.sidebar.button("▶️ Start Monitoring"):
            if st.session_state.monitor.setup_driver():
                st.session_state.monitor.driver.get("https://1xbet.com/en/allgamesentrance/crash")
                st.session_state.monitoring = True
                st.experimental_rerun()
    else:
        if st.sidebar.button("⏹️ Stop Monitoring"):
            if st.session_state.monitor.driver:
                st.session_state.monitor.driver.quit()
            st.session_state.monitoring = False
            st.experimental_rerun()

    # Add settings
    st.sidebar.subheader("Settings")
    st.session_state.update_interval = st.sidebar.slider(
        "Update Interval (seconds)",
        min_value=0.1,
        max_value=2.0,
        value=0.2,
        step=0.1
    )

def render_main_metrics(monitor):
    """Render main metrics section"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        game_state = monitor.game_state or "Not Monitoring"
        st.metric("Game State", game_state.upper())
    
    with col2:
        current_multi = f"{monitor.current_multiplier}x" if monitor.current_multiplier else "N/A"
        st.metric("Current Multiplier", current_multi)
    
    with col3:
        if monitor.crash_history:
            last_crash = f"{monitor.crash_history[-1]['value']}x"
            st.metric("Last Crash", last_crash)
        else:
            st.metric("Last Crash", "N/A")

def render_crash_chart(history):
    """Render crash history chart"""
    if not history:
        return

    values = [crash['value'] for crash in history]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values,
        mode='lines+markers',
        name='Crash Values',
        line=dict(color='#FF4B4B')
    ))
    
    fig.update_layout(
        title="Crash History",
        yaxis_title="Crash Multiplier",
        xaxis_title="Game Number",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_analysis(analysis):
    """Render analysis and recommendations section"""
    if not analysis:
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Statistics")
        stats_df = pd.DataFrame({
            'Metric': ['Average', 'Median', 'Min', 'Max', 'Volatility', 'Trend'],
            'Value': [
                f"{analysis['average']:.2f}x",
                f"{analysis['median']:.2f}x",
                f"{analysis['min']:.2f}x",
                f"{analysis['max']:.2f}x",
                f"{analysis['volatility']:.2f}",
                analysis['trend'].title()
            ]
        })
        st.dataframe(stats_df, hide_index=True)
    
    with col2:
        st.subheader("💡 Recommendations")
        st.info(f"""
        **Next Bet Recommendation:**
        - Target Multiplier: {analysis['target_multiplier']:.2f}x
        - Bet Amount: {analysis['bet_amount']} MAD
        - Strategy: {analysis['trend'].title()} trend detected
        """)

def main():
    st.set_page_config(
        page_title="1xBet Crash Analyzer",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 1xBet Crash Game Analyzer")
    
    # Render sidebar
    render_sidebar()
    
    if st.session_state.monitoring:
        # Update game state
        game_state, multiplier = st.session_state.monitor.monitor_game_state()
        
        # Render metrics
        render_main_metrics(st.session_state.monitor)
        
        # Render chart
        render_crash_chart(st.session_state.monitor.crash_history)
        
        # Render analysis if enough data
        if len(st.session_state.monitor.crash_history) >= 10:
            analysis = st.session_state.monitor.analyze_patterns()
            render_analysis(analysis)
        
        # Auto-refresh
        time.sleep(st.session_state.update_interval)
        st.experimental_rerun()
    else:
        st.info("Click 'Start Monitoring' in the sidebar to begin analysis")

if __name__ == "__main__":
    main()
