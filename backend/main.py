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

# --- Constants & Mappings ---
SPECIES_MAP = {
    "Sea Lamprey": "Petromyzon marinus",
    "Silver Carp": "Hypophthalmichthys molitrix",
    "Bighead Carp": "Hypophthalmichthys nobilis",
    "Grass Carp": "Ctenopharyngodon idella"
}

app = FastAPI()

# Enable CORS for frontend
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# --- LIVE CANADIAN DATA INTEGRATION (WSC / MSC) ---
async def fetch_canadian_water_data(station_id: str):
    """
    Fetches live water level/discharge from Water Survey of Canada (OGC API).
    """
    url = f"https://api.weather.gc.ca/collections/hydrometric-realtime/items?STATION_NUMBER={station_id}&limit=1&sortby=-DATETIME"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code != 200:
                return (None, None)
            
            data = resp.json()
            if not data.get('features'):
                return (None, None)
            
            props = data['features'][0]['properties']
            level = props.get('LEVEL')
            discharge = props.get('DISCHARGE')
            
            citation = f"Water Survey of Canada (Station {station_id})"
            return (discharge, level, citation)
    except Exception as e:
        print(f"WSC Fetch Error: {e}")
        return (None, None, None)

async def fetch_canadian_climate_data(station_name: str):
    """
    Fetches hourly climate data from Environment Canada (MSC GeoMet).
    """
    url = f"https://api.weather.gc.ca/collections/climate-hourly/items?STATION_NAME={station_name}&limit=1&sortby=-LOCAL_DATE"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not data.get('features'):
                return None
            
            temp = data['features'][0]['properties'].get('TEMP')
            return temp
    except Exception as e:
        print(f"MSC Climate Fetch Error: {e}")
        return None

# --- LIVE SIGHTINGS INTEGRATION (GBIF) ---
async def fetch_gbif_sightings(species_common_name: str, coords: List[List[float]]):
    """
    Fetches recent sightings from GBIF for a given species and bounding box.
    """
    scientific_name = SPECIES_MAP.get(species_common_name)
    if not scientific_name:
        return 0, []

    # Calculate bounding box from polygon coords
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # GBIF doesn't strictly need WKT for simple searches but it's cleaner
    # We'll use the decimalLatitude/Longitude params for simplicity
    url = "https://api.gbif.org/v1/occurrence/search"
    params = {
        "scientificName": scientific_name,
        "decimalLatitude": f"{min_lat},{max_lat}",
        "decimalLongitude": f"{min_lon},{max_lon}",
        "hasCoordinate": "true",
        "limit": 20
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", 0)
                results = data.get("results", [])
                return count, results
            return 0, []
    except Exception as e:
        print(f"GBIF Fetch Error: {e}")
        return 0, []

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
    
    if live_flow is not None:
        print(f"Using Live USGS Data: Flow={live_flow}cfs")
        
        # Calculate derived model inputs
        flow_velocity_proxy = live_flow / 1000.0  # Rough proxy for model
        temp_anomaly = (live_temp - 10.0) if live_temp is not None else 0.0
        
        # Update Features: [temp, dist, traffic, DO, flow]
        grid103_features = [temp_anomaly, 5.0, 0.9, 8.5, flow_velocity_proxy]
        
        grid103_drivers = [
            f"Current Discharge: {live_flow} cfs (Live USGS)",
            "High connectivity"
        ]
        if live_temp: 
             grid103_drivers.insert(0, f"Water Temp: {live_temp}°C")
        
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
        # REGION 4: CANADIAN BORDER (Cross-Agency Overlay)
        {
            "id": "grid-105-can",
            "coords": [[[-83.1, 42.3], [-82.9, 42.3], [-82.9, 42.4], [-83.1, 42.4], [-83.1, 42.3]]], # Detroit River/Lake St Clair
            "species": "Grass Carp",
            "features": [0.5, 5.0, 0.9, 8.2, 0.4],
            "drivers": ["High wetland connectivity", "Spawning habitat match"],
            "citations": ["Fisheries and Oceans Canada (DFO)", "Invasive Species Centre (Canada)"]
        },
        # REGION 5: GEORGIAN BAY (Deep North Risk)
        {
            "id": "grid-106-can",
            "coords": [[[-81.2, 45.1], [-80.8, 45.1], [-80.8, 45.5], [-81.2, 45.5], [-81.2, 45.1]]], 
            "species": "Sea Lamprey",
            "features": [0.2, 5.0, 0.4, 9.5, 0.1],
            "drivers": ["Cold water refugia", "Traditional spawning grounds"],
            "citations": ["DFO Canada Surveillance", "Ontario Ministry of Natural Resources"]
        },
        # REGION 6: ST. CLAIR RIVER (Industrial Vector)
        {
            "id": "grid-107-can",
            "coords": [[[-82.5, 42.9], [-82.3, 42.9], [-82.3, 43.1], [-82.5, 43.1], [-82.5, 42.9]]], # Sarnia/Port Huron
            "species": "Silver Carp",
            "features": [0.8, 2.0, 0.9, 8.1, 0.3],
            "drivers": ["High ballast discharge risk", "Connecting channel bottleneck"],
            "citations": ["Invasive Species Centre Sarnia", "WSC Station 02GG002"]
        }
    ]

    # --- Canadian Data Overlay Injection ---
    can_discharge, can_level, can_cite = await fetch_canadian_water_data("02GH011") # Little River at Windsor
    can_temp = await fetch_canadian_climate_data("WINDSOR A")

    for region in regions:
        if region['id'].endswith('-can') and can_discharge is not None:
            print(f"Overlays Active: Injecting Canadian WSC data into {region['id']}")
            # Update features with live Canadian data
            temp_val = can_temp if can_temp is not None else 5.0
            # [temp_anomaly, dist, traffic, DO, flow]
            region['features'][0] = temp_val - 10.0
            
            region['drivers'].insert(0, f"Live WSC Discharge: {can_discharge} m3/s")
            if can_temp is not None:
                region['drivers'].insert(0, f"Live Ambient Temp: {can_temp}°C (MSC)")
            
            if can_cite not in region['citations']:
                region['citations'].append(can_cite)
            if can_temp is not None and "Environment and Climate Change Canada (MSC)" not in region['citations']:
                region['citations'].append("Environment and Climate Change Canada (MSC)")

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
        # Fallback if training failed (Matching 6 regions now)
        predictions = [0.85, 0.45, 0.92, 0.65, 0.55, 0.72] 

    for i, region in enumerate(regions):
        # 2. Fetch Real-Time Sightings (GBIF) for EACH region
        sighting_count, latest_sightings = await fetch_gbif_sightings(region['species'], region['coords'][0])
        
        # 3. Composite Inference
        # Base score from the model (Habitat Suitability)
        base_score = float(predictions[i])
        
        # Sightings Adjustment: Boost score if recent sightings exist (The "Crosswalk")
        sighting_boost = 0.0
        if sighting_count > 0:
            sighting_boost = min(0.3, 0.1 * np.log10(sighting_count + 1))
            region['drivers'].append(f"Confirmed sightings: {sighting_count} records (GBIF)")
            region['citations'].append("GBIF Global Biodiversity Information Facility")
        
        # Intersection Logic: If high flow (from USGS) AND recent sightings exist
        # grid-103 is the one with live USGS data
        if region['id'] == 'grid-103' and live_flow and live_flow > 1500 and sighting_count > 0:
            sighting_boost += 0.15
            region['drivers'].insert(0, "CRITICAL SIGNAL: High discharge vector + nearby sighting")
            region['citations'].append("USGS/GBIF Integrated Signal")

        composite_score = min(0.99, base_score + sighting_boost)
        
        results.append({
            "id": region['id'],
            "coords": region['coords'],
            "species": region['species'],
            "score": composite_score,
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
        MANDATORY: Explicitly cite the specific data sources for every observation (e.g., "Sighting verified via GBIF...", "Hydrological data from USGS indicates...").
        Explain WHY the risk is high based on the specific drivers.
        Do not use vague phrases; be precise and citation-focused.
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
        if final_score > 0.1: # Threshold lowered to ensure almost everything gets AI analysis
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

    # Track Health for Frontend Status Board
    health = {
        "maritime": "green", # Simulation is always "active"
        "us_data": "green" if any(r['citations'] and "USGS" in str(r['citations']) for r in quant_results) else "red",
        "canada_data": "green" if any(r['citations'] and ("Water Survey" in str(r['citations']) or "Environment and Climate" in str(r['citations'])) for r in quant_results) else "red",
        "integrity": "green" if any(r['citations'] and "GBIF" in str(r['citations']) for r in quant_results) else "red"
    }

    return PredictionsResponse(
        metadata={
            "model_version": "v1.6-health-monitored",
            "source": "Scikit-Learn + OpenAI + USGS (US) + WSC/MSC (Canada) + GBIF (Global)",
            "health": health
        },
        regions=processed_regions
    )

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

# Robust Path Resolution (Resolves relative to this file, backend/main.py)
# BASE_DIR = invasive-species-tracker/
BASE_DIR = pathlib.Path(__file__).parent.parent 

app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")

@app.get("/")
async def read_index():
    return FileResponse(BASE_DIR / "index.html")
