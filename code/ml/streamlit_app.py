import os
import json
import random
import numpy as np
import xgboost as xgb
import streamlit as st

# Configure the Streamlit page
st.set_page_config(
    page_title="Edge AI Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom minimal CSS for a cleaner look
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #3b82f6;
    }
    .warning-bar .stProgress > div > div > div > div {
        background-color: #f59e0b;
    }
    .danger-bar .stProgress > div > div > div > div {
        background-color: #ef4444;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }
    /* Hide the sidebar toggle */
    [data-testid="collapsedControl"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_models_and_stats():
    MODEL_DIR = os.path.join(os.path.dirname(__file__), 'model')
    HAZARDS = ['wildfire', 'flood', 'storm', 'air_quality']
    models = {}
    
    # Load normalization stats
    with open(os.path.join(MODEL_DIR, 'normalization.json'), 'r') as f:
        norm_stats = json.load(f)
        
    # Load XGBoost models
    for hazard in HAZARDS:
        model_path = os.path.join(MODEL_DIR, f'xgboost_{hazard}.json')
        if os.path.exists(model_path):
            bst = xgb.Booster()
            bst.load_model(model_path)
            models[hazard] = bst
            
    return models, norm_stats, HAZARDS

models, norm_stats, HAZARDS = load_models_and_stats()

# Production alert thresholds
THRESHOLDS = {
    'wildfire': 0.70,
    'flood': 0.70,
    'storm': 0.75,
    'air_quality': 0.65,
}

HAZARD_ICONS = {
    'wildfire': '🔥 Wildfire Risk',
    'flood': '🌊 Flash Flood',
    'storm': '⛈️ Severe Storm',
    'air_quality': '🌫️ Air Quality Alert'
}

# ----------------- INFERENCE LOGIC -----------------

def run_inference(inputs_dict):
    feature_names = norm_stats['feature_names']
    features = [float(inputs_dict.get(name, 0.0)) for name in feature_names]
    
    X = np.array([features], dtype=np.float32)
    mean = np.array(norm_stats['mean'], dtype=np.float32)
    std = np.array(norm_stats['std'], dtype=np.float32)
    
    std[std == 0] = 1.0
    X_norm = (X - mean) / std
    
    dmatrix = xgb.DMatrix(X_norm)
    
    results = {}
    for hazard in HAZARDS:
        if hazard in models:
            results[hazard] = float(models[hazard].predict(dmatrix)[0])
        else:
            results[hazard] = 0.0
            
    return results

# ----------------- UI -----------------

st.title("🌍 Edge AI Hazard Monitor")
st.markdown("Decentralized environmental node inference dashboard.")

# Tab setup
tab_live, tab_manual = st.tabs(["📡 Live Data Monitor", "🎛️ Manual Override"])

# Helper function to display prediction cards
def display_predictions(predictions):
    cols = st.columns(4)
    for i, hazard in enumerate(HAZARDS):
        prob = predictions[hazard]
        prob_pct = int(prob * 100)
        thresh = THRESHOLDS[hazard]
        
        if prob >= thresh:
            status = "CRITICAL"
            css_class = "danger-bar"
            delta_color = "inverse"
        elif prob >= thresh * 0.7:
            status = "WARNING"
            css_class = "warning-bar"
            delta_color = "off"
        else:
            status = "SAFE"
            css_class = ""
            delta_color = "normal"
        
        with cols[i]:
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            st.metric(
                label=HAZARD_ICONS[hazard],
                value=f"{prob_pct}%",
                delta=status,
                delta_color=delta_color
            )
            st.progress(prob)
            st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 1: LIVE DATA -----------------
with tab_live:
    st.subheader("Node Telemetry Stream")
    st.markdown("Simulate incoming sensor payload from a decentralized node.")
    
    if st.button("Fetch Latest Telemetry", type="primary"):
        # Generate realistic random data
        live_data = {
            'temp_current': round(random.uniform(15.0, 45.0), 1),
            'humidity_current': round(random.uniform(20.0, 95.0), 1),
            'pressure_current': round(random.uniform(980.0, 1020.0), 1),
            'wind_speed_current': round(random.uniform(0.0, 25.0), 1),
            'pm25_current': round(random.uniform(5.0, 300.0), 1),
            'co2_current': round(random.uniform(400.0, 1500.0), 1),
            'lightning_dist_current': round(random.uniform(0.0, 40.0), 1),
            'temp_humidity_ratio': round(random.uniform(0.2, 0.8), 2),
            'pressure_trend': round(random.uniform(-3.0, 3.0), 1),
            'heat_index': round(random.uniform(15.0, 50.0), 1),
            'dew_point': round(random.uniform(5.0, 25.0), 1),
            'fire_risk_index': round(random.uniform(0.0, 100.0), 1),
            'flood_risk_index': round(random.uniform(0.0, 100.0), 1),
            'lightning_threat': round(random.uniform(0.0, 100.0), 1)
        }
        st.session_state['live_data'] = live_data
    
    if 'live_data' not in st.session_state:
        st.info("Click 'Fetch Latest Telemetry' to simulate an incoming data packet.")
    else:
        # Run inference
        live_predictions = run_inference(st.session_state['live_data'])
        
        # Display Predictions
        st.markdown("### AI Inference (Live)")
        display_predictions(live_predictions)
        
        st.markdown("---")
        st.markdown("### Raw Sensor Payload")
        
        ld = st.session_state['live_data']
        mc1, mc2, mc3, mc4 = st.columns(4)
        
        with mc1:
            st.metric("Temperature", f"{ld['temp_current']} °C")
            st.metric("Pressure", f"{ld['pressure_current']} hPa")
            st.metric("PM2.5", f"{ld['pm25_current']} μg/m³")
        with mc2:
            st.metric("Humidity", f"{ld['humidity_current']} %")
            st.metric("Wind Speed", f"{ld['wind_speed_current']} m/s")
            st.metric("CO2", f"{ld['co2_current']} ppm")
        with mc3:
            st.metric("Fire Risk Index", f"{ld['fire_risk_index']}")
            st.metric("Heat Index", f"{ld['heat_index']} °C")
            st.metric("T/H Ratio", f"{ld['temp_humidity_ratio']}")
        with mc4:
            st.metric("Flood Risk Index", f"{ld['flood_risk_index']}")
            st.metric("Dew Point", f"{ld['dew_point']} °C")
            st.metric("Lightning Threat", f"{ld['lightning_threat']}")

# ----------------- TAB 2: MANUAL OVERRIDE -----------------
with tab_manual:
    st.subheader("Manual Inference Injection")
    st.markdown("Override sensor values to test specific hazard conditions.")
    
    manual_inputs = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("🌡️ Core Meteorological", expanded=True):
            manual_inputs['temp_current'] = st.slider('Temperature (°C)', -10.0, 50.0, 25.0)
            manual_inputs['humidity_current'] = st.slider('Humidity (%)', 0.0, 100.0, 60.0)
            manual_inputs['pressure_current'] = st.slider('Pressure (hPa)', 900.0, 1100.0, 1013.0)
            manual_inputs['wind_speed_current'] = st.slider('Wind Speed (m/s)', 0.0, 50.0, 5.0)
            manual_inputs['pressure_trend'] = st.slider('Pressure Trend', -5.0, 5.0, 0.0)

        with st.expander("🌫️ Air Quality", expanded=True):
            manual_inputs['pm25_current'] = st.slider('PM2.5 (μg/m³)', 0.0, 500.0, 15.0)
            manual_inputs['co2_current'] = st.slider('CO2 (ppm)', 400.0, 5000.0, 450.0)
            
    with col2:
        with st.expander("⚠️ Hazard & Derived Indicators", expanded=True):
            manual_inputs['lightning_dist_current'] = st.slider('Lightning Dist (km)', 0.0, 40.0, 40.0)
            manual_inputs['temp_humidity_ratio'] = st.slider('T/H Ratio', 0.0, 2.0, 0.4)
            manual_inputs['heat_index'] = st.slider('Heat Index (°C)', -10.0, 60.0, 26.0)
            manual_inputs['dew_point'] = st.slider('Dew Point (°C)', -20.0, 30.0, 15.0)
            manual_inputs['fire_risk_index'] = st.slider('Fire Risk', 0.0, 100.0, 20.0)
            manual_inputs['flood_risk_index'] = st.slider('Flood Risk', 0.0, 100.0, 10.0)
            manual_inputs['lightning_threat'] = st.slider('Lightning Threat', 0.0, 100.0, 5.0)

    # Run manual inference immediately as sliders change
    manual_predictions = run_inference(manual_inputs)
    
    st.markdown("### AI Inference (Manual Override)")
    display_predictions(manual_predictions)
