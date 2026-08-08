from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from pymongo import MongoClient

from dotenv import load_dotenv
load_dotenv() # This reads the .env file and loads MONGO_URI into the environment


from pydantic import BaseModel
from typing import List, Dict, Any


import os

app = FastAPI(title="Data Harvesting Engine Server")

SHARED_RESEARCH_TOKEN = "your_shared_secret_research_key_here"

# Securely grab the connection string from the hosting environment
MONGO_URI = "mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

class SessionPayload(BaseModel):
    participant_id: str
    mode: str
    rounds: List[Dict[str, Any]]
    cognitive_data: dict = None  # ADD IT HERE INSTEAD

# --- Frontend Serving Route ---
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serves the index.html file to users visiting the site root."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Frontend index.html asset missing from server root.")

# --- Pre-flight Check Route ---
@app.get("/check/{participant_id}")
def check_participant(participant_id: str):
    """Checks if an ID is already taken before starting data harvesting."""
    try:
        existing = collection.find_one({"participant_id": participant_id.upper()})
        return {"exists": True if existing else False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database lookup exception: {str(e)}")

# --- Data Harvesting Ingestion Routes ---
@app.post("/enroll")
def enroll_session(payload: SessionPayload):
    """Ingests multi-round dataset strings for target profile enrollment."""
    try:
        document = payload.dict()
        document["participant_id"] = document["participant_id"].upper()
        result = collection.insert_one(document)
        print(f"[SERVER SUCCESS] Logged Enrollment ID: {result.inserted_id}")
        return {"status": "success", "message": "Biometric harvesting profile committed to database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Storage Failure: {str(e)}")

@app.post("/verify")
def verify_session(payload: SessionPayload):
    """Ingests data to verify against existing telemetry matrix profiles."""
    try:
        # Check if the participant exists at all
        existing = collection.find_one({"participant_id": payload.participant_id.upper()})
        if not existing:
            raise HTTPException(status_code=404, detail="User profile not found.")
            
        document = payload.dict()
        document["participant_id"] = document["participant_id"].upper()
        collection.insert_one(document) # Commit verification attempt data
        
        # Returns a mock matching validation back to the game overlay
        return {
            "status": "success",
            "match": True,
            "score": 0.95
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Verification pipeline failure: {str(e)}")