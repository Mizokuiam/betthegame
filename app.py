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

class CrashGameMonitor:
    def __init__(self):
        self.crash_history = []
        self.current_multiplier = None
        self.game_state = None
        self.driver = None
        self.wait = None
        self.data_file = Path("crash_history.json")
        self.balance = None
        self.logged_in = False
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
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
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
            
            # Test browser
            st.sidebar.text("Testing browser...")
            self.driver.get("https://1xbet.com/en/")
            time.sleep(2)
            
            return True
        except Exception as e:
            st.sidebar.error(f"Failed to setup browser: {str(e)}")
            if hasattr(e, '__traceback__'):
                st.sidebar.error(f"Traceback: {traceback.format_exc()}")
            return False

    def login(self, username, password):
        """Login to 1xBet"""
        try:
            st.sidebar.text("Attempting to log in...")
            
            # Navigate directly to login page
            self.driver.get("https://1xbet.com/en/login/")
            time.sleep(5)  # Wait longer for page load
            
            st.sidebar.text("Current URL: " + self.driver.current_url)
            
            # Debug page source
            page_source = self.driver.page_source
            st.sidebar.text("Page source length: " + str(len(page_source)))
            st.sidebar.text("Looking for iframes...")
            
            # Check for iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for idx, iframe in enumerate(iframes):
                try:
                    iframe_id = iframe.get_attribute("id")
                    iframe_name = iframe.get_attribute("name")
                    iframe_src = iframe.get_attribute("src")
                    st.sidebar.text(f"Found iframe {idx}: id={iframe_id}, name={iframe_name}, src={iframe_src}")
                    
                    # Switch to iframe and look for login form
                    self.driver.switch_to.frame(iframe)
                    
                    # Try to find login elements in iframe
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for input_elem in inputs:
                        input_type = input_elem.get_attribute("type")
                        input_name = input_elem.get_attribute("name")
                        input_id = input_elem.get_attribute("id")
                        st.sidebar.text(f"Input in iframe: type={input_type}, name={input_name}, id={input_id}")
                    
                    # Switch back to default content
                    self.driver.switch_to.default_content()
                except Exception as e:
                    st.sidebar.text(f"Error with iframe {idx}: {str(e)}")
                    self.driver.switch_to.default_content()
                    continue
            
            # Try multiple approaches to fill the form
            login_attempts = 0
            max_attempts = 3
            
            while login_attempts < max_attempts:
                try:
                    # First try: Check page state
                    st.sidebar.text(f"Attempt {login_attempts + 1}: Checking page state")
                    
                    # List all input elements
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    st.sidebar.text(f"Found {len(all_inputs)} input elements")
                    for input_elem in all_inputs:
                        try:
                            input_type = input_elem.get_attribute("type")
                            input_name = input_elem.get_attribute("name")
                            input_id = input_elem.get_attribute("id")
                            input_class = input_elem.get_attribute("class")
                            st.sidebar.text(f"Input: type={input_type}, name={input_name}, id={input_id}, class={input_class}")
                        except:
                            continue
                    
                    # List all buttons
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    st.sidebar.text(f"Found {len(all_buttons)} button elements")
                    for button in all_buttons:
                        try:
                            button_type = button.get_attribute("type")
                            button_class = button.get_attribute("class")
                            button_id = button.get_attribute("id")
                            st.sidebar.text(f"Button: type={button_type}, class={button_class}, id={button_id}")
                        except:
                            continue
                    
                    # Try to find login form
                    forms = self.driver.find_elements(By.TAG_NAME, "form")
                    st.sidebar.text(f"Found {len(forms)} form elements")
                    for form in forms:
                        try:
                            form_id = form.get_attribute("id")
                            form_class = form.get_attribute("class")
                            st.sidebar.text(f"Form: id={form_id}, class={form_class}")
                        except:
                            continue
                    
                    # Try JavaScript injection with more debugging
                    js_code = """
                        function getFormInfo() {
                            const forms = document.getElementsByTagName('form');
                            const inputs = document.getElementsByTagName('input');
                            const buttons = document.getElementsByTagName('button');
                            return {
                                forms: forms.length,
                                inputs: inputs.length,
                                buttons: buttons.length,
                                html: document.documentElement.outerHTML
                            };
                        }
                        return getFormInfo();
                    """
                    page_info = self.driver.execute_script(js_code)
                    st.sidebar.text(f"JS found: {page_info['forms']} forms, {page_info['inputs']} inputs, {page_info['buttons']} buttons")
                    
                    # If we found no form elements, try refreshing the page
                    if page_info['forms'] == 0 and page_info['inputs'] == 0:
                        st.sidebar.text("No form elements found, refreshing page...")
                        self.driver.refresh()
                        time.sleep(5)
                        login_attempts += 1
                        continue
                    
                    # First try: Direct JavaScript injection
                    st.sidebar.text("Attempt " + str(login_attempts + 1) + ": Using JavaScript")
                    js_code = f"""
                        function fillForm() {{
                            // Get all input fields
                            const inputs = document.querySelectorAll('input');
                            let loginField = null;
                            let passwordField = null;
                            
                            // Find login and password fields
                            for (const input of inputs) {{
                                const type = input.getAttribute('type');
                                const name = input.getAttribute('name');
                                const placeholder = (input.getAttribute('placeholder') || '').toLowerCase();
                                
                                if (type === 'text' || type === 'email' || 
                                    (placeholder && (placeholder.includes('id') || placeholder.includes('email')))) {{
                                    loginField = input;
                                }}
                                if (type === 'password') {{
                                    passwordField = input;
                                }}
                            }}
                            
                            if (loginField && passwordField) {{
                                // Fill login
                                loginField.value = '{username}';
                                loginField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                loginField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                // Fill password
                                passwordField.value = '{password}';
                                passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                // Find and click submit button
                                const buttons = document.querySelectorAll('button');
                                for (const button of buttons) {{
                                    if (button.type === 'submit' || 
                                        button.classList.contains('auth-button') ||
                                        button.classList.contains('login-button')) {{
                                        button.click();
                                        return true;
                                    }}
                                }}
                            }}
                            return false;
                        }}
                        return fillForm();
                    """
                    
                    form_filled = self.driver.execute_script(js_code)
                    if form_filled:
                        st.sidebar.text("JavaScript form fill successful")
                        time.sleep(3)
                        break
                    else:
                        st.sidebar.text("JavaScript form fill failed, trying Selenium")
                    
                    # Second try: Selenium with explicit waits
                    # Find username field
                    username_elements = self.driver.find_elements(By.TAG_NAME, "input")
                    username_filled = False
                    for elem in username_elements:
                        try:
                            elem_type = elem.get_attribute("type")
                            elem_placeholder = elem.get_attribute("placeholder")
                            st.sidebar.text(f"Found input: type={elem_type}, placeholder={elem_placeholder}")
                            if elem_type in ["text", "email"] or (elem_placeholder and ("id" in elem_placeholder.lower() or "email" in elem_placeholder.lower())):
                                elem.clear()
                                elem.send_keys(username)
                                username_filled = True
                                st.sidebar.text("Username filled")
                                break
                        except Exception as e:
                            st.sidebar.text(f"Error with input: {str(e)}")
                            continue
                    
                    if not username_filled:
                        st.sidebar.warning("Could not find username field")
                        login_attempts += 1
                        continue
                    
                    # Find password field
                    password_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    if password_elements:
                        password_elements[0].clear()
                        password_elements[0].send_keys(password)
                        st.sidebar.text("Password filled")
                    else:
                        st.sidebar.warning("Could not find password field")
                        login_attempts += 1
                        continue
                    
                    # Find submit button
                    submit_clicked = False
                    submit_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in submit_buttons:
                        try:
                            button_type = button.get_attribute("type")
                            button_class = button.get_attribute("class")
                            st.sidebar.text(f"Found button: type={button_type}, class={button_class}")
                            if button_type == "submit" or \
                               (button_class and ("auth-button" in button_class or "login-button" in button_class)):
                                button.click()
                                submit_clicked = True
                                st.sidebar.text("Submit button clicked")
                                break
                        except Exception as e:
                            st.sidebar.text(f"Error with button: {str(e)}")
                            continue
                    
                    if not submit_clicked:
                        st.sidebar.warning("Could not find submit button")
                        login_attempts += 1
                        continue
                    
                    break
                    
                except Exception as e:
                    login_attempts += 1
                    st.sidebar.warning(f"Login attempt {login_attempts} failed: {str(e)}")
                    time.sleep(2)
                    continue
            
            # Wait for login to complete
            time.sleep(5)
            
            # Get current URL for debugging
            st.sidebar.text("Post-login URL: " + self.driver.current_url)
            
            # Verify login success
            try:
                # Try multiple methods to verify login
                verification_methods = [
                    (By.CSS_SELECTOR, ".header-balance-sum"),
                    (By.CSS_SELECTOR, ".main-balance"),
                    (By.CSS_SELECTOR, ".balance-value"),
                    (By.XPATH, "//div[contains(@class, 'header-balance')]//span"),
                    (By.XPATH, "//div[contains(text(), 'MAD')]"),
                    (By.CSS_SELECTOR, "#balance"),
                ]
                
                for method_type, selector in verification_methods:
                    try:
                        st.sidebar.text(f"Trying to find balance with: {selector}")
                        balance_elem = self.driver.find_element(method_type, selector)
                        balance_text = balance_elem.text.strip()
                        st.sidebar.text(f"Found element text: {balance_text}")
                        
                        if 'MAD' in balance_text:
                            self.balance = float(balance_text.replace('MAD', '').strip())
                            st.sidebar.success(f"Logged in successfully! Balance: {self.balance} MAD")
                            self.logged_in = True
                            
                            # Navigate to crash game
                            self.driver.get("https://1xbet.com/en/allgamesentrance/crash")
                            time.sleep(2)
                            return True
                    except Exception as e:
                        st.sidebar.text(f"Verification method failed: {str(e)}")
                        continue
                
                # If we get here, try to check if we're on a logged-in page
                try:
                    profile_elements = self.driver.find_elements(By.CSS_SELECTOR, ".profile, .account, .user-info")
                    if profile_elements:
                        st.sidebar.success("Found profile element, assuming login successful")
                        self.logged_in = True
                        self.driver.get("https://1xbet.com/en/allgamesentrance/crash")
                        time.sleep(2)
                        return True
                except Exception as e:
                    st.sidebar.text(f"Profile check failed: {str(e)}")
                
                st.sidebar.error("Could not verify login success")
                return False
                
            except Exception as e:
                st.sidebar.error(f"Error verifying login: {str(e)}")
                return False
                
        except Exception as e:
            st.sidebar.error(f"Login failed: {str(e)}")
            if hasattr(e, '__traceback__'):
                st.sidebar.error(f"Traceback: {traceback.format_exc()}")
            return False

    def get_balance(self):
        """Get current balance"""
        try:
            balance_elem = self.driver.find_element(By.CSS_SELECTOR, ".header-balance-sum")
            self.balance = float(balance_elem.text.strip().replace('MAD', '').strip())
            return self.balance
        except Exception as e:
            st.sidebar.error(f"Error getting balance: {str(e)}")
            return None

    def calculate_bet_amount(self):
        """Calculate recommended bet amount based on balance"""
        if not self.balance:
            return 3  # Default minimum bet
        
        # Conservative betting strategy (1-3% of balance)
        base_bet = max(3, round(self.balance * 0.01, 2))  # Minimum 3 MAD
        return min(base_bet, self.balance * 0.03)  # Maximum 3% of balance

    def monitor_game_state(self):
        """Monitor current game state and multiplier using JavaScript execution"""
        try:
            if not self.driver:
                st.error("Browser not initialized!")
                return "error", None

            # Navigate to page if not already there
            current_url = self.driver.current_url
            if "1xbet.com" not in current_url:
                st.info("Navigating to 1xBet...")
                self.driver.get("https://1xbet.com/en/allgamesentrance/crash")
                time.sleep(3)  # Wait longer for page load

            # Debug info
            st.sidebar.text("Current URL: " + self.driver.current_url)
            
            # Inject JavaScript to bypass potential bot detection
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # Try to get game state using JavaScript
            try:
                game_state_js = """
                    let wrapper = document.querySelector('.crash-wrapper');
                    if (!wrapper) return 'unknown';
                    if (wrapper.classList.contains('preparing')) return 'preparing';
                    if (wrapper.classList.contains('flying')) return 'flying';
                    if (wrapper.classList.contains('crashed')) return 'crashed';
                    return document.querySelector('.game-state')?.textContent || 'unknown';
                """
                self.game_state = self.driver.execute_script(game_state_js)
                st.sidebar.text(f"Game state from JS: {self.game_state}")
            except Exception as e:
                st.sidebar.error(f"Error getting game state via JS: {str(e)}")
                self.game_state = "unknown"

            # Try to get multiplier using JavaScript
            try:
                multiplier_js = """
                    let multiplier = document.querySelector('.multiplier');
                    if (!multiplier) return null;
                    let value = multiplier.textContent.replace('×', '').trim();
                    return value ? parseFloat(value) : null;
                """
                self.current_multiplier = self.driver.execute_script(multiplier_js)
                st.sidebar.text(f"Multiplier from JS: {self.current_multiplier}")
            except Exception as e:
                st.sidebar.error(f"Error getting multiplier via JS: {str(e)}")
                self.current_multiplier = None

            # Try alternative method using network requests
            try:
                cookies = self.driver.get_cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://1xbet.com/en/allgamesentrance/crash'
                }
                
                st.sidebar.text("Attempting to get game state via API...")
                # Note: You might need to find the actual API endpoint
                response = self.driver.execute_script("""
                    return fetch('/crash/state').then(r => r.json());
                """)
                
                if response:
                    st.sidebar.text(f"API Response: {response}")
                    # Update state based on API response if available
                    if 'state' in response:
                        self.game_state = response['state']
                    if 'multiplier' in response:
                        self.current_multiplier = float(response['multiplier'])

            except Exception as e:
                st.sidebar.error(f"Error with API request: {str(e)}")

            # Record crash value
            if self.game_state == "crashed" and self.current_multiplier:
                self.crash_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'value': self.current_multiplier
                })
                self.save_history()

            # Take screenshot for debugging
            try:
                screenshot = self.driver.get_screenshot_as_base64()
                st.sidebar.image(screenshot, caption="Current page state", use_column_width=True)
            except Exception as e:
                st.sidebar.error(f"Failed to take screenshot: {str(e)}")

            return self.game_state, self.current_multiplier
        except Exception as e:
            st.error(f"Error monitoring game state: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                st.sidebar.error(f"Traceback: {traceback.format_exc()}")
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
        if len(recent_crashes) >= 3:
            if all(recent_crashes[i] <= recent_crashes[i+1] for i in range(len(recent_crashes)-2)):
                analysis['trend'] = 'increasing'
            elif all(recent_crashes[i] >= recent_crashes[i+1] for i in range(len(recent_crashes)-2)):
                analysis['trend'] = 'decreasing'

        # Calculate bet amount based on balance
        recommended_bet = self.calculate_bet_amount()

        # Generate recommendations
        if analysis['trend'] == 'decreasing':
            analysis['target_multiplier'] = max(1.3, min(1.5, analysis['min'] * 0.9))
            analysis['bet_amount'] = recommended_bet * 0.7  # More conservative
        elif analysis['trend'] == 'increasing':
            analysis['target_multiplier'] = max(1.5, min(2.0, analysis['average'] * 0.8))
            analysis['bet_amount'] = recommended_bet  # Standard bet
        else:
            analysis['target_multiplier'] = max(1.4, min(1.8, analysis['median'] * 0.85))
            analysis['bet_amount'] = recommended_bet * 0.85  # Moderate

        # Round bet amount to 2 decimal places
        analysis['bet_amount'] = round(analysis['bet_amount'], 2)
        
        # Add win probability estimate
        below_target = sum(1 for x in recent_crashes if x >= analysis['target_multiplier'])
        analysis['win_probability'] = f"{(below_target / len(recent_crashes)) * 100:.1f}%"

        return analysis

def render_sidebar():
    """Render sidebar with controls and info"""
    st.sidebar.title("⚙️ Controls")
    
    # Add monitoring controls
    if 'monitor' not in st.session_state:
        st.session_state.monitor = CrashGameMonitor()
        st.session_state.monitoring = False
        st.session_state.logged_in = False

    # Login section
    if not st.session_state.logged_in:
        st.sidebar.subheader("📝 Login")
        username = st.sidebar.text_input("Login ID", type="password")
        password = st.sidebar.text_input("Password", type="password")
        
        if st.sidebar.button("🔑 Login"):
            if st.session_state.monitor.setup_driver():
                if st.session_state.monitor.login(username, password):
                    st.session_state.logged_in = True
                    st.rerun()

    # Monitoring controls
    if st.session_state.logged_in:
        if not st.session_state.monitoring:
            if st.sidebar.button("▶️ Start Monitoring"):
                st.session_state.monitor.driver.get("https://1xbet.com/en/allgamesentrance/crash")
                st.session_state.monitoring = True
                st.rerun()
        else:
            if st.sidebar.button("⏹️ Stop Monitoring"):
                if st.session_state.monitor.driver:
                    st.session_state.monitor.driver.quit()
                st.session_state.monitoring = False
                st.rerun()

        # Show current balance
        if st.session_state.monitor.balance:
            st.sidebar.metric("💰 Balance", f"{st.session_state.monitor.balance} MAD")

    # Settings
    st.sidebar.subheader("⚙️ Settings")
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
        - Win Probability: {analysis['win_probability']}
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
        st.rerun()
    else:
        st.info("Click 'Start Monitoring' in the sidebar to begin analysis")

if __name__ == "__main__":
    main()
