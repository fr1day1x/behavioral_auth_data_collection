from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
from sklearn.covariance import LedoitWolf

app = FastAPI(title="BehaviorAuth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

class RawSessionData(BaseModel):
    reaction_times: dict
    itis: dict
    text_dwell_times: dict = None  # accommodate variations if needed
    dwell_times: dict
    x_offsets: list
    y_offsets: list
    total_errors: int

class AuthPayload(BaseModel):
    participant_id: str
    mode: str
    rounds: list[RawSessionData]

def extract_features(raw_data: RawSessionData):
    features = []
    
    # Dimensions 1-4: Reaction Times (4 features)
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        arr = raw_data.reaction_times.get(bucket, [])
        features.append((sum(arr)/len(arr) / 1000.0) if arr else 0.5)

    # Dimensions 5-8: Inter-Tap Intervals (4 features)
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        arr = raw_data.itis.get(bucket, [])
        features.append((sum(arr)/len(arr) / 2000.0) if arr else 0.5)

    # Cleaned Dimension 9: Unified Global Dwell Time (1 feature instead of 4)
    all_dwells = []
    for bucket in ["Adjacent", "Diagonal", "Medium", "Long"]:
        all_dwells.extend(raw_data.dwell_times.get(bucket, []))
    features.append((sum(all_dwells)/len(all_dwells) / 200.0) if all_dwells else 0.45)

    # Cleaned Dimensions 10-11: X-Axis Bias (2 features - Medians Dropped)
    x_arr = raw_data.x_offsets
    features.append((np.mean(x_arr) / 40.0) if x_arr else 0.0)
    features.append((np.std(x_arr) / 40.0) if x_arr else 0.0)

    # Cleaned Dimensions 12-13: Y-Axis Bias (2 features - Medians Dropped)
    y_arr = raw_data.y_offsets
    features.append((np.mean(y_arr) / 40.0) if y_arr else 0.0)
    features.append((np.std(y_arr) / 40.0) if y_arr else 0.0)

    # Cleaned Dimension 14: Session Errors (1 feature)
    features.append(raw_data.total_errors / 5.0)

    # Total features: 4 + 4 + 1 + 2 + 2 + 1 = 14 dimensions!
    return np.array(features)

def train_mahalanobis(data_vectors):
    data_matrix = np.array(data_vectors, dtype=float)
    
    # Compute regularized matrix via Ledoit-Wolf
    lw_estimator = LedoitWolf().fit(data_matrix)
    stable_cov = lw_estimator.covariance_
    
    inv_cov_matrix = np.linalg.pinv(stable_cov)
    mean_vector = np.mean(data_matrix, axis=0)
    
    return mean_vector, inv_cov_matrix

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.get("/check/{participant_id}")
async def check_user(participant_id: str):
    user_ref = db.collection("users").document(participant_id)
    return {"exists": user_ref.get().exists}

@app.post("/enroll")
async def enroll_user(payload: AuthPayload):
    user_ref = db.collection("users").document(payload.participant_id)
    
    if user_ref.get().exists:
        raise HTTPException(status_code=400, detail="User ID already exists in cloud database.")
    if len(payload.rounds) != 5:
        raise HTTPException(status_code=400, detail="Enrollment requires exactly 5 rounds.")

    vectors = [extract_features(r) for r in payload.rounds]
    template, inv_cov_matrix = train_mahalanobis(vectors)

    user_ref.set({
        "template": template.tolist(),
        "inv_cov": inv_cov_matrix.flatten().tolist()
    })

    return {"status": "success", "message": f"Successfully enrolled {payload.participant_id}."}

@app.post("/verify")
async def verify_user(payload: AuthPayload):
    user_ref = db.collection("users").document(payload.participant_id)
    doc = user_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found in cloud database.")
    if len(payload.rounds) != 1:
        raise HTTPException(status_code=400, detail="Verification requires exactly 1 round.")

    stored_data = doc.to_dict()
    template = np.array(stored_data["template"])
    
    # Cleaned vector length is 14 elements, making the matrix grid exactly 14x14
    inv_cov_matrix = np.array(stored_data["inv_cov"]).reshape(14, 14)

    live_vector = extract_features(payload.rounds[0])

    delta = live_vector - template
    distance = float(np.sqrt(np.dot(np.dot(delta, inv_cov_matrix), delta.T)))
    
    is_match = distance <= 4.0  # Tightened from 5.0 now that data is clean

    return {
        "status": "success", 
        "match": is_match, 
        "score": round(distance, 3)
    }