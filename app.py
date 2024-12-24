import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json
import os

class CrashGameAnalyzer:
    def __init__(self):
        self.history = []
        self.model = None
        self.X_scaler = MinMaxScaler()
        self.y_scaler = MinMaxScaler()
        self.load_history()

    def load_history(self):
        """Load crash history from file if it exists"""
        try:
            if os.path.exists('crash_history.json'):
                with open('crash_history.json', 'r') as f:
                    self.history = json.load(f)
                st.success(f"Loaded {len(self.history)} historical crash points")
        except Exception as e:
            st.error(f"Error loading history: {str(e)}")

    def save_history(self):
        """Save crash history to file"""
        try:
            with open('crash_history.json', 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            st.error(f"Error saving history: {str(e)}")

    def add_crash_point(self, value):
        """Add a new crash point to history"""
        try:
            value = float(value)
            if value > 1.0:
                self.history.append(value)
                self.save_history()
                return True
        except:
            return False
        return False

    def prepare_data(self, sequence_length=10):
        """Prepare data for ML model"""
        if len(self.history) < sequence_length + 1:
            return None, None

        X, y = [], []
        for i in range(len(self.history) - sequence_length):
            X.append(self.history[i:i + sequence_length])
            y.append(self.history[i + sequence_length])

        X = np.array(X)
        y = np.array(y)
        
        # Scale the data
        X_scaled = self.X_scaler.fit_transform(X)
        y_scaled = self.y_scaler.fit_transform(y.reshape(-1, 1)).ravel()
        
        return X_scaled, y_scaled

    def train_model(self):
        """Train the ML model on historical data"""
        X, y = self.prepare_data()
        if X is None or len(X) < 20:  # Need at least 20 sequences to train
            return False

        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Train model
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model.fit(X_train, y_train)

            # Calculate accuracy
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)

            st.info(f"Model trained successfully. Train score: {train_score:.2f}, Test score: {test_score:.2f}")
            return True
        except Exception as e:
            st.error(f"Error training model: {str(e)}")
            return False

    def predict_next_crash(self):
        """Predict the next crash point"""
        if self.model is None or len(self.history) < 10:
            return None

        try:
            # Prepare last 10 points for prediction
            last_sequence = np.array(self.history[-10:]).reshape(1, -1)
            last_sequence_scaled = self.X_scaler.transform(last_sequence)
            
            # Make prediction
            prediction_scaled = self.model.predict(last_sequence_scaled)
            prediction = self.y_scaler.inverse_transform(prediction_scaled.reshape(-1, 1))
            
            return float(prediction[0][0])
        except Exception as e:
            st.error(f"Error making prediction: {str(e)}")
            return None

    def get_betting_advice(self, prediction):
        """Generate betting advice based on prediction and patterns"""
        if prediction is None:
            return None

        advice = {
            'prediction': prediction,
            'confidence': 'low',
            'recommended_exit': 0,
            'strategy': ''
        }

        # Analyze recent volatility
        recent_points = self.history[-10:]
        volatility = np.std(recent_points)
        mean_value = np.mean(recent_points)
        
        # Adjust confidence based on volatility
        if volatility < 0.5:
            advice['confidence'] = 'high'
        elif volatility < 1.0:
            advice['confidence'] = 'medium'

        # Set recommended exit point
        if prediction > mean_value * 1.2:  # If prediction is significantly higher
            advice['recommended_exit'] = mean_value * 1.1
            advice['strategy'] = 'Aggressive'
        else:
            advice['recommended_exit'] = min(prediction * 0.9, mean_value)
            advice['strategy'] = 'Conservative'

        return advice

    def plot_history(self):
        """Plot crash history and predictions"""
        if len(self.history) < 2:
            return None

        df = pd.DataFrame({
            'Index': range(len(self.history)),
            'Crash Point': self.history
        })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Index'],
            y=df['Crash Point'],
            mode='lines+markers',
            name='Crash Points'
        ))

        # Add threshold line
        fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="2x threshold")

        fig.update_layout(
            title='Crash History',
            xaxis_title='Game Number',
            yaxis_title='Crash Point',
            hovermode='x'
        )

        return fig

def main():
    st.title('Crash Game AI Analyzer')
    
    # Initialize analyzer
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = CrashGameAnalyzer()
    
    analyzer = st.session_state.analyzer

    # Sidebar for adding new crash points
    with st.sidebar:
        st.header("Add Crash Points")
        new_point = st.text_input("Enter crash point (e.g., 2.5):")
        if st.button("Add Point"):
            if analyzer.add_crash_point(new_point):
                st.success(f"Added crash point: {new_point}")
            else:
                st.error("Invalid crash point. Must be a number greater than 1.0")

        st.markdown("---")
        if st.button("Train AI Model"):
            analyzer.train_model()

    # Main content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Last 10 Crashes")
        if len(analyzer.history) >= 10:
            last_10 = analyzer.history[-10:]
            st.write(" → ".join([f"{x:.2f}x" for x in last_10]))
        else:
            st.info("Need more crash points for analysis")

    with col2:
        st.subheader("Statistics")
        if len(analyzer.history) > 0:
            stats = {
                "Average": np.mean(analyzer.history),
                "Max": np.max(analyzer.history),
                "Min": np.min(analyzer.history),
                "Volatility": np.std(analyzer.history)
            }
            for key, value in stats.items():
                st.metric(key, f"{value:.2f}")

    # Plot history
    st.subheader("Crash History Analysis")
    fig = analyzer.plot_history()
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # Predictions and advice
    st.subheader("AI Predictions")
    if len(analyzer.history) >= 20:  # Need at least 20 points for meaningful prediction
        prediction = analyzer.predict_next_crash()
        if prediction:
            advice = analyzer.get_betting_advice(prediction)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Predicted Crash", f"{prediction:.2f}x")
            with col2:
                st.metric("Recommended Exit", f"{advice['recommended_exit']:.2f}x")
            with col3:
                st.metric("Confidence", advice['confidence'].upper())

            st.info(f"Strategy: {advice['strategy']}")
            
            if advice['confidence'] == 'high':
                st.success("✅ Good conditions for betting")
            elif advice['confidence'] == 'medium':
                st.warning("⚠️ Moderate risk")
            else:
                st.error("❌ High risk - Consider waiting")
    else:
        st.info("Need at least 20 crash points to make predictions")

if __name__ == "__main__":
    main()
