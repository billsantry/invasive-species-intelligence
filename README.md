# Invasive Species Intelligence (v0.5)

**Status:** Beta (v0.5-glfc-integrated)  
**Live Demo:** Localhost only (Requires API Keys)  
**Author:** billsantry (Built with Google Antigravity)

![Status Nominal](https://img.shields.io/badge/Status-Nominal-success) ![AI Model](https://img.shields.io/badge/AI-Hybrid%20Architecture-blueviolet) ![GLFC](https://img.shields.io/badge/Data-GLFC%20Integrated-blue)

## 🌊 Mission
Protecting the Great Lakes from the economic and ecological threat of invasive carp and sea lamprey. This tool aggregates cross-border data (USGS/DFO) and GLFC infrastructure status, utilizing AI to predict migration fronts and identify high-risk breaches before they become irreversible.

It serves as a **Decision Support System** for environmental analysts, translating raw hydrological data into actionable, explained risk intelligence.

## 🧠 "Two-Brain" Architecture
This project uses a unique hybrid predictive engine to ensure stability and explainability:

1.  **The "Quant" Brain (Python/Scikit-Learn)**
    *   **Role:** Hard Math & Physics.
    *   **Function:** Ingests live environmental data (Flow Velocity, Temp) and **GLFC Infrastructure Status** (Barrier functionality) to calculate a raw Risk Score (0-100).
    *   **Source:** Live USGS/WSC/GBIF API inputs + GLFC Local Data.
2.  **The "Analyst" Brain (OpenAI GPT-4)**
    *   **Role:** Context & Explanation.
    *   **Function:** Takes the raw score and factor data to generate a professional, plain-language risk assessment.
    *   **Constraint:** Explicitly cited to prevent hallucination.

## 🚀 Key Features (v0.5)
*   **Intelligence Feed**: A prioritized, always-open feed of critical insights and "Signal" alerts, with hyperlinks to jump directly to high-risk grid cells.
*   **GLFC Infrastructure Integration**: Ingests and displays 7,900+ sea lamprey barriers, treatments, and trapping operations.
*   **Smart Risk Logic**: The AI model now accounts for barrier proximity and functional status (e.g., non-functional barriers increase local risk).
*   **Live Cross-Border Data**: Fuses USGS (US) and WSC (Canada) hydrological data for a complete Great Lakes view.
*   **Interactive Sidebar**: Stacked data layer controls with "Focus Mode" defaults.
*   **Glassmorphic UI**: Premium, dark-mode visualization optimized for situational awareness.

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.10+
*   OpenAI API Key (Start with `sk-...`)

### 1. Clone & Install
```bash
git clone https://github.com/billsantry/invasive-species-intelligence.git
cd invasive-species-intelligence

# Install Python Backend Dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Credentials
Create a `.env` file in the `backend/` directory:
```bash
# backend/.env
OPENAI_API_KEY=your_actual_api_key_here
```

### 3. Run the System
You need to run **two** terminals:

**Terminal A (The Brain/Backend):**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal B (The Body/Frontend):**
```bash
# Serves the map at http://localhost:8080
python3 -m http.server 8080
```

## ⚠️ Disclaimer
*Predictions are probabilistic and based on public, incomplete data. This tool is for decision support only, not regulatory enforcement.*
