import os
import math
import numpy as np
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymongo
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Behavioral Biometric Authentication Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://koolp:adminadmin@cluster0.o5k4k.mongodb.net/test?retryWrites=true&w=majority")
client = None
db = None
collection = None

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["neuro_defense_db"]
    collection = db["telemetry_logs"]
    print("Connected to MongoDB cluster")
except Exception as e:
    print(f"MongoDB Connection Warning: {e}")

FEATURE_WEIGHTS = np.array([
    1.0, 1.0, 1.2, 1.2,          # Latency / ITI (Distance 0-3)
    0.8, 0.8, 1.0, 1.0,          # Latency / ITI (Distance 4-7)
    2.5, 2.0,                    # Dwell Duration, Dwell Variance (Motor Release)
    0.7, 0.7, 0.7, 0.7, 1.5,     # Accuracy X/Y Centroid, Dispersion, Miss Penalty
    2.2, 1.8,                    # Path Efficiency Mean & Jitter
    1.8, 2.6,                    # Mean Velocity, Peak Ballistic Velocity
    2.0, 3.2,                    # Acceleration, Neuromuscular Jerk Signature
    1.6, 2.0, 1.8,               # Cumulative Curvature, Overshoots, Velocity Skewness
    2.0, 2.0, 2.4, 1.8           # PIN Familiar, PIN Novel, Cognitive Ratio, Keypad Velocity
])

def mahalanobis_distance(u: np.ndarray, v: np.ndarray, weights: np.ndarray) -> float:
    diff = u - v
    return float(np.sqrt(np.sum(weights * (diff ** 2))))

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>App is running</h1>", status_code=200)

@app.get("/api/health")
async def health_check():
    return {"status": "operational", "port": os.getenv("PORT", "3000")}

@app.post("/api/telemetry")
async def log_telemetry(payload: Dict[str, Any]):
    try:
        if collection is not None:
            collection.insert_one(payload)
            return {"status": "SUCCESS", "message": "Telemetry logged."}
        return {"status": "SUCCESS", "message": "Telemetry received (offline mode)."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@app.post("/api/enroll")
async def enroll_user(payload: Dict[str, Any]):
    try:
        participant_id = payload.get("participant_id")
        vector = payload.get("vector")
        if not participant_id or not vector:
            raise HTTPException(status_code=400, detail="Missing participant_id or vector")
        
        if collection is not None:
            collection.update_one(
                {"participant_id": participant_id},
                {"$set": {
                    "participant_id": participant_id,
                    "baseline_vector": vector,
                    "type": "ENROLLMENT"
                }},
                upsert=True
            )
        return {"status": "SUCCESS", "message": f"User {participant_id} baseline enrolled."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verify")
async def verify_user(payload: Dict[str, Any]):
    try:
        participant_id = payload.get("participant_id")
        vector = payload.get("vector")
        if not participant_id or not vector:
            raise HTTPException(status_code=400, detail="Missing participant_id or vector")
        
        baseline = None
        if collection is not None:
            doc = collection.find_one({"participant_id": participant_id})
            if doc and "baseline_vector" in doc:
                baseline = doc["baseline_vector"]

        if not baseline:
            return JSONResponse(status_code=404, content={"status": "ERROR", "message": "No baseline enrollment found."})

        u = np.array(vector, dtype=float)
        v = np.array(baseline, dtype=float)
        
        dist = mahalanobis_distance(u, v, FEATURE_WEIGHTS[:len(u)])
        threshold = 35.0
        is_verified = dist <= threshold

        return {
            "status": "SUCCESS",
            "verified": bool(is_verified),
            "distance": round(dist, 4),
            "threshold": threshold,
            "confidence": round(max(0.0, min(100.0, 100.0 - (dist / threshold * 50.0))), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main_server:app", host="0.0.0.0", port=port, reload=False)
