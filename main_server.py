from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from pymongo import MongoClient  # <-- Run 'pip install pymongo dnspython'
import os

app = FastAPI(title="BehaviorAuth Research Ingestion Server")

SHARED_RESEARCH_TOKEN = "your_shared_secret_research_key_here"

# Securely grab the connection string from the hosting environment
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is missing!")

client = MongoClient(MONGO_URI)
db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

class SessionPayload(BaseModel):
    participant_id: str
    timestamp: str
    sessions: List[Dict[str, Any]]

def verify_token(x_research_token: str = Header(...)):
    if x_research_token != SHARED_RESEARCH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized Research Token")
    return x_research_token

@app.post("/submit-session")
def submit_session(payload: SessionPayload, token: str = Depends(verify_token)):
    try:
        # Convert Pydantic model to dict and insert directly as a BSON document
        result = collection.insert_one(payload.dict())
        print(f"[SERVER SUCCESS] Logged telemetry document ID: {result.inserted_id}")
        return {"status": "success", "message": "Telemetry matrix committed to MongoDB Atlas."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Storage Failure: {str(e)}")