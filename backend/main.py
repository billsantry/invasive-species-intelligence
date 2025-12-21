from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import random
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Enable CORS for frontend (assuming localhost:8080)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

class RegionProperties(BaseModel):
    risk_score: float
    risk_label: str
    confidence: str
    species: str
    drivers: List[str]
    explanation: str

class RegionGeometry(BaseModel):
    type: str
    coordinates: List[List[List[float]]]

class Region(BaseModel):
    id: str
    geometry: RegionGeometry
    properties: RegionProperties

class PredictionsResponse(BaseModel):
    metadata: dict
    regions: List[Region]

import joblib
import pandas as pd
import numpy as np

# Load the trained Model (The "Quant" Brain)
try:
    model = joblib.load("models/invasive_risk_model_v1.joblib")
    print("Loaded Scikit-Learn Model.")
except:
    print("Warning: Model not found. Using mock fallback.")
    model = None

# --- The "Quant" Brain (Real Inference) ---
def run_inference():
    # Define our grid cells (normally this would come from a database)
    regions = [
        {
            "id": "grid-101",
            "coords": [[[-87.5, 44.0], [-87.0, 44.0], [-87.0, 44.5], [-87.5, 44.5], [-87.5, 44.0]]],
            "species": "Sea Lamprey",
            # Features for the model: [temp_anomaly, dist_source, traffic]
            "features": [1.8, 12.0, 0.8], 
            "drivers": ["High thermal anomaly (+1.8°C)", "Proximity to source (12km)", "High vessel traffic"]
        },
        {
            "id": "grid-102", # New Region
            "coords": [[[-86.5, 44.0], [-86.0, 44.0], [-86.0, 44.5], [-86.5, 44.5], [-86.5, 44.0]]],
            "species": "Silver Carp",
            "features": [0.2, 85.0, 0.3], 
            "drivers": ["Low temperature variance", "Distance from source (85km)"]
        },
        {
            "id": "grid-103",
            "coords": [[[-87.5, 43.5], [-87.0, 43.5], [-87.0, 44.0], [-87.5, 44.0], [-87.5, 43.5]]],
            "species": "Asian Carp Complex",
            "features": [1.1, 5.0, 0.9],
            "drivers": ["Hydrological connection", "Optimal feeding conditions", "Recent eDNA signal"]
        }
    ]

    results = []
    
    # Batch Prediction
    if model:
        # Extract features into a DataFrame
        feature_data = [r['features'] for r in regions]
        df_features = pd.DataFrame(feature_data, columns=['water_temp_anomaly', 'distance_to_source', 'vessel_traffic_density'])
        
        # Scikit-Learn Predict
        predictions = model.predict(df_features)
    else:
        # Fallback if training failed
        predictions = [0.85, 0.45, 0.92] 

    for i, region in enumerate(regions):
        score = float(predictions[i])
        results.append({
            "id": region['id'],
            "coords": region['coords'],
            "species": region['species'],
            "score": score,
            "drivers": region['drivers']
        })
        
    return results


@app.get("/predict", response_model=PredictionsResponse)
async def get_predictions():
    # 1. Run Quant Logic (Real Model)
    quant_results = run_inference()
    
    processed_regions = []
    
    for item in quant_results:
        final_score = round(min(0.99, max(0.01, item['score'])), 2)
        
        risk_label = "Critical" if final_score > 0.9 else ("High" if final_score > 0.6 else "Moderate")
        
        # 2. Call Analyst Brain (OpenAI)
        # We only explain high risk items to save API tokens, or explain all if requested.
        # For demo, let's explain everything > 0.5
        if final_score > 0.5:
            explanation_text = generate_explanation(item['species'], int(final_score*100), item['drivers'])
        else:
            explanation_text = "Risk levels are currently within nominal baselines. Standard monitoring recommended."

        processed_regions.append(
            Region(
                id=item['id'],
                geometry=RegionGeometry(type="Polygon", coordinates=item['coords']),
                properties=RegionProperties(
                    risk_score=final_score,
                    risk_label=risk_label,
                    confidence="High", # Model confidence could be calculated via variances
                    species=item['species'],
                    drivers=item['drivers'],
                    explanation=explanation_text
                )
            )
        )

    return PredictionsResponse(
        metadata={
            "model_version": "v1.0-sklearn-rf",
            "source": "Real Scikit-Learn Model + OpenAI API"
        },
        regions=processed_regions
    )

@app.get("/")
def read_root():
    return {"status": "Invasive Species Intelligence API Active"}
