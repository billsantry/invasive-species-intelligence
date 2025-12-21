import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os

# 1. Generate Synthetic Training Data
# In a real scenario, we would load CSVs from /data/
print("Generatring synthetic environmental data...")

# Features: 
# - water_temp_anomaly (degrees C above normal)
# - distance_to_source (km)
# - vessel_traffic_density (0-1 score)
# - dissolved_oxygen (mg/L)

n_samples = 1000
np.random.seed(42)

data = {
    'water_temp_anomaly': np.random.normal(1.0, 0.5, n_samples),
    'distance_to_source': np.random.exponential(50, n_samples),
    'vessel_traffic_density': np.random.beta(2, 5, n_samples),
    'dissolved_oxygen': np.random.normal(8, 1.5, n_samples)
}

df = pd.DataFrame(data)

# Target Variable: Invasion Risk (0-100)
# Formula: Higher temp + Closer distance + High traffic = Higher Risk
df['risk_score'] = (
    (df['water_temp_anomaly'] * 15) + 
    ((100 - df['distance_to_source']) * 0.4) + 
    (df['vessel_traffic_density'] * 30) +
    np.random.normal(0, 5, n_samples) # Add noise
)

# Normalize to 0-1
df['risk_score'] = (df['risk_score'] - df['risk_score'].min()) / (df['risk_score'].max() - df['risk_score'].min())

print(f"Dataset Shape: {df.shape}")

# 2. Train Model
X = df[['water_temp_anomaly', 'distance_to_source', 'vessel_traffic_density']]
y = df['risk_score']

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

print("Model Trained. R2 Score:", model.score(X,y))

# 3. Save Model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/invasive_risk_model_v1.joblib")
print("Model saved to backend/models/invasive_risk_model_v1.joblib")
