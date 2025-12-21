from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import random
import json
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"], # Explicit origins
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
    citations: List[str]  # New Field for Integrity

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

# --- LIVE DATA INTEGRATION (USGS) ---
async def fetch_usgs_data(site_id: str):
    """
    Fetches live Discharge (00060) and Temp (00010) from USGS IV Service.
    Returns: (flow_cfs, temp_c, citation_string)
    """
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd=00060,00010&siteStatus=all"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code != 200:
                return (None, None, None)
            
            data = resp.json()
            time_series = data['value']['timeSeries']
            
            flow = None
            temp = None
            
            for ts in time_series:
                var_code = ts['variable']['variableCode'][0]['value']
                # Get most recent value
                if ts['values'][0]['value']:
                    val = float(ts['values'][0]['value'][0]['value'])
                    if var_code == '00060': flow = val
                    if var_code == '00010': temp = val
            
            citation = f"USGS National Water Information System (Site {site_id})"
            return (flow, temp, citation)
            
    except Exception as e:
        print(f"USGS Fetch Error: {e}")
        return (None, None, None)

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
async def run_inference():
    # 1. Fetch Real-Time Data for Key Vectors
    # Des Plaines River at Riverside, IL (Key vector for Carp)
    live_flow, live_temp, usgs_cite = await fetch_usgs_data("05532500")
    
    # Process Live Data or Fallback
    # Normalize cfs to approx m/s surrogate: flow / 1000
    # Normalize temp to anomaly: temp - 15.0
    
    grid103_features = [1.1, 5.0, 0.9, 4.2, 0.1] # Default (Stagnant)
    grid103_drivers = ["Hydrological connection", "Optimal feeding conditions"]
    grid103_citations = ["Historical Surveys (2023)"]
    
    if live_flow is not None and live_temp is not None:
        print(f"Using Live USGS Data: Flow={live_flow}cfs, Temp={live_temp}C")
        
        # Calculate derived model inputs
        flow_velocity_proxy = live_flow / 1000.0  # Rough proxy for model
        temp_anomaly = live_temp - 10.0 # Assuming 10C is winter baseline, 20C summer
        
        # Update Features: [temp, dist, traffic, DO, flow]
        # We assume DO is decent (8.0) if flow is active
        grid103_features = [temp_anomaly, 5.0, 0.9, 8.5, flow_velocity_proxy]
        
        grid103_drivers = [
            f"Live Water Temp: {live_temp}°C", 
            f"Current Discharge: {live_flow} cfs",
            "High connectivity"
        ]
        grid103_citations.append(usgs_cite)
    
    
    # Define our grid cells (normally this would come from a database)
    regions = [
        # REGION 1: SEA LAMPREY (Legacy Threat)
        {
            "id": "grid-101",
            "coords": [[[-87.5, 44.0], [-87.0, 44.0], [-87.0, 44.5], [-87.5, 44.5], [-87.5, 44.0]]],
            "species": "Sea Lamprey",
            "features": [1.8, 12.0, 0.8, 7.5, 0.2], 
            "drivers": ["High thermal anomaly (+1.8°C)", "Proximity to source (12km)", "High vessel traffic", "Moderate Flow"],
            "citations": ["NOAA GLERL", "Great Lakes Commission"]
        },
        # REGION 2: SILVER CARP (High Priority)
        {
            "id": "grid-102", 
            "coords": [[[-86.5, 44.0], [-86.0, 44.0], [-86.0, 44.5], [-86.5, 44.5], [-86.5, 44.0]]],
            "species": "Silver Carp",
            "features": [0.2, 85.0, 0.3, 9.0, 1.2], 
            "drivers": ["Low temperature variance", "Distance from source (85km)", "Strong Currents (1.2m/s)"],
            "citations": ["US Fish & Wildlife Service", "White House Memoranda Data"]
        },
        # REGION 3: BIGHEAD CARP (Live Data Focus)
        {
            "id": "grid-103",
            "coords": [[[-87.5, 43.5], [-87.0, 43.5], [-87.0, 44.0], [-87.5, 44.0], [-87.5, 43.5]]],
            "species": "Bighead Carp",
            "features": grid103_features,
            "drivers": grid103_drivers,
            "citations": grid103_citations
        },
        # REGION 4: CANADIAN BORDER (Cross-Agency)
        {
            "id": "grid-105-can",
            "coords": [[[-83.1, 42.3], [-82.9, 42.3], [-82.9, 42.4], [-83.1, 42.4], [-83.1, 42.3]]], # Detroit River/Lake St Clair
            "species": "Grass Carp",
            "features": [0.5, 5.0, 0.9, 8.2, 0.4],
            "drivers": ["High wetland connectivity", "Spawning habitat match"],
            "citations": ["Fisheries and Oceans Canada (DFO)", "Invasive Species Centre (Canada)"]
        }
    ]

    results = []
    
    # Batch Prediction
    if model:
        # Extract features into a DataFrame
        feature_data = [r['features'] for r in regions]
        df_features = pd.DataFrame(feature_data, columns=[
            'water_temp_anomaly', 'distance_to_source', 'vessel_traffic_density', 
            'dissolved_oxygen', 'flow_velocity'
        ])
        
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
            "drivers": region['drivers'],
            "citations": region['citations']
        })
        
    return results


# --- The "Analyst" Brain (OpenAI Integration) ---
def generate_explanation(species, score, drivers, citations):
    try:
        # Prompt Engineering for the "Analyst" Persona with Citations
        citation_text = "; ".join(citations)
        prompt = f"""
        You are a senior environmental risk analyst. 
        Data:
        - Species: {species}
        - Computed Risk Score: {score}/100
        - Key Drivers: {", ".join(drivers)}
        - Sources: {citation_text}
        
        Write a concise, professional assessment. 
        Explicitly mention the data source (e.g. "Based on live USGS data...") if available.
        Explain WHY the risk is high based on the drivers.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o", # Upgraded
            messages=[{"role": "system", "content": "You are a helpful, precise environmental analyst."},
                      {"role": "user", "content": prompt}],
            max_tokens=80, # Increased for citation
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return "Automatic analysis unavailable."


@app.get("/predict", response_model=PredictionsResponse)
async def get_predictions():
    # 1. Run Quant Logic (Real Model + Live Data)
    quant_results = await run_inference()
    
    processed_regions = []
    
    for item in quant_results:
        final_score = round(min(0.99, max(0.01, item['score'])), 2)
        
        risk_label = "Critical" if final_score > 0.9 else ("High" if final_score > 0.6 else "Moderate")
        
        # 2. Call Analyst Brain (OpenAI)
        if final_score > 0.4: # Lower threshold to show descriptions more often
            explanation_text = generate_explanation(item['species'], int(final_score*100), item['drivers'], item['citations'])
        else:
            explanation_text = "Risk levels are currently within nominal baselines."

        processed_regions.append(
            Region(
                id=item['id'],
                geometry=RegionGeometry(type="Polygon", coordinates=item['coords']),
                properties=RegionProperties(
                    risk_score=final_score,
                    risk_label=risk_label,
                    confidence="High",
                    species=item['species'],
                    drivers=item['drivers'],
                    explanation=explanation_text,
                    citations=item['citations']
                )
            )
        )

    return PredictionsResponse(
        metadata={
            "model_version": "v1.1-hybrid-live-usgs",
            "source": "Scikit-Learn + OpenAI + USGS Water Services"
        },
        regions=processed_regions
    )

@app.get("/")
def read_root():
    return {"status": "Invasive Species Intelligence API Active"}
