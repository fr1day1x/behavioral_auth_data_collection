import os
import math
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

# In-memory fast cache of user profiles
user_profiles: Dict[str, Dict[str, Any]] = {}
mongo_client: Optional[pymongo.MongoClient] = None
mongo_db = None
last_sync_timestamp = 0

def get_mongo_uri() -> str:
    return os.getenv(
        "MONGO_URI",
        "mongodb+srv://koolp:adminadmin@cluster0.o5k4k.mongodb.net/test?retryWrites=true&w=majority"
    ).strip()

def mean(arr: List[float]) -> float:
    if not arr:
        return 0.0
    return float(np.mean(arr))

def std(arr: List[float]) -> float:
    if len(arr) <= 1:
        return 0.0
    return float(np.std(arr, ddof=1))

def normalize_doc(doc: Dict[str, Any], source_col: str) -> Optional[Dict[str, Any]]:
    p_id = (
        doc.get("participant_id")
        or doc.get("participantId")
        or doc.get("operative_id")
        or doc.get("username")
        or doc.get("name")
        or doc.get("id")
    )
    if not p_id:
        return None

    p_id = str(p_id).strip().toUpperCase() if hasattr(str(p_id), "toUpperCase") else str(p_id).strip().upper()

    template = doc.get("template") or doc.get("baseline_vector") or doc.get("vector") or doc.get("features")
    variances = doc.get("variances")

    if not template and doc.get("rounds"):
        rounds = doc.get("rounds", [])
        if rounds:
            vectors = [extract_features(r, doc.get("cognitive_data")) for r in rounds]
            t, v = build_biometric_template(vectors)
            template = t
            variances = v

    if not template or not isinstance(template, list) or len(template) == 0:
        return None

    return {
        "participant_id": p_id,
        "enrolled_at": str(doc.get("enrolled_at") or doc.get("timestamp") or doc.get("created_at") or datetime.utcnow().isoformat()),
        "template": [float(x) for x in template],
        "variances": [float(x) for x in variances] if variances and isinstance(variances, list) else [0.05] * len(template),
        "rounds_count": doc.get("rounds_count") or (len(doc.get("rounds")) if doc.get("rounds") else 1),
        "source": source_col,
    }

def extract_features(round_data: Dict[str, Any], cognitive: Optional[Dict[str, Any]] = None) -> List[float]:
    f: List[float] = []

    # [0..3] Latency (Reaction Times across distance buckets)
    rts = round_data.get("reaction_times", {})
    f.append(mean(rts.get("Adjacent", [])) / 600.0 if rts.get("Adjacent") else 0.40)
    f.append(mean(rts.get("Diagonal", [])) / 750.0 if rts.get("Diagonal") else 0.45)
    f.append(mean(rts.get("Medium", [])) / 900.0 if rts.get("Medium") else 0.50)
    f.append(mean(rts.get("Long", [])) / 1100.0 if rts.get("Long") else 0.60)

    # [4..7] ITIs (Inter-target intervals)
    itis = round_data.get("itis", {})
    f.append(mean(itis.get("Adjacent", [])) / 600.0 if itis.get("Adjacent") else 0.40)
    f.append(mean(itis.get("Diagonal", [])) / 750.0 if itis.get("Diagonal") else 0.45)
    f.append(mean(itis.get("Medium", [])) / 900.0 if itis.get("Medium") else 0.50)
    f.append(mean(itis.get("Long", [])) / 1100.0 if itis.get("Long") else 0.60)

    # [8..9] Click Dwell Duration & Dwell Variance
    dwells = round_data.get("dwell_times", {})
    all_dwells: List[float] = []
    for k in ["Adjacent", "Diagonal", "Medium", "Long", "First"]:
        all_dwells.extend(dwells.get(k, []))
    f.append(mean(all_dwells) / 150.0 if all_dwells else 0.45)
    f.append(std(all_dwells) / 30.0 if len(all_dwells) > 1 else 0.15)

    # [10..13] Spatial Centroid Offsets & Variances
    x_off = round_data.get("x_offsets", [])
    y_off = round_data.get("y_offsets", [])
    f.append((mean(x_off) + 20.0) / 40.0 if x_off else 0.50)
    f.append(std(x_off) / 10.0 if len(x_off) > 1 else 0.20)
    f.append((mean(y_off) + 20.0) / 40.0 if y_off else 0.50)
    f.append(std(y_off) / 10.0 if len(y_off) > 1 else 0.20)

    # [14] Target Miss / Error rate
    errs = float(round_data.get("total_errors", 0))
    f.append(min(1.0, errs / 10.0))

    # [15] Mean Path Efficiency
    path_eff = round_data.get("path_efficiencies", [])
    f.append(mean(path_eff) if path_eff else 0.85)

    # [16] Path Efficiency Jitter
    f.append(std(path_eff) if len(path_eff) > 1 else 0.08)

    # [17] Mean Kinematic Velocity
    mean_vel = round_data.get("mean_velocities", [])
    f.append(mean(mean_vel) / 1.8 if mean_vel else 0.50)

    # [18] Peak Kinematic Velocity
    peak_vel = round_data.get("peak_velocities", [])
    f.append(mean(peak_vel) / 3.5 if peak_vel else 0.55)

    # [19] Mean Acceleration
    mean_acc = round_data.get("mean_accelerations", [])
    f.append(mean(mean_acc) / 0.04 if mean_acc else 0.35)

    # [20] Mean Neuromuscular Jerk Signature
    mean_jerk = round_data.get("mean_jerks", [])
    f.append(mean(mean_jerk) / 0.005 if mean_jerk else 0.30)

    # [21] Cumulative Curvature
    ang_chg = round_data.get("angular_changes", [])
    f.append(mean(ang_chg) / 3.14 if ang_chg else 0.40)

    # [22] Overshoot & Micro-correction frequency
    overshoots = round_data.get("overshoot_counts", [])
    f.append(mean(overshoots) / 2.0 if overshoots else 0.10)

    # [23] Velocity Profile Skewness
    t_peak_ratios = round_data.get("time_to_peak_vel_ratios", [])
    f.append(mean(t_peak_ratios) if t_peak_ratios else 0.38)

    # [24..27] Cognitive PIN minigame dynamics
    if cognitive:
        fam_flights = cognitive.get("familiar", {}).get("flight_times", [])
        unfam_flights = cognitive.get("unfamiliar", {}).get("flight_times", [])
        f.append(mean(fam_flights) / 600.0 if fam_flights else 0.35)
        f.append(mean(unfam_flights) / 900.0 if unfam_flights else 0.55)

        fam_m = mean(fam_flights) if fam_flights else 200.0
        unfam_m = mean(unfam_flights) if unfam_flights else 400.0
        f.append(fam_m / unfam_m if unfam_m > 0 else 0.50)

        fam_vel = cognitive.get("familiar", {}).get("mean_velocities", [])
        f.append(mean(fam_vel) / 1.5 if fam_vel else 0.45)
    else:
        f.extend([0.35, 0.55, 0.50, 0.45])

    return f

def build_biometric_template(vectors: List[List[float]]) -> (List[float], List[float]):
    num_dims = len(vectors[0]) if vectors else 28
    template: List[float] = []
    variances: List[float] = []
    epsilon = 0.008

    for d in range(num_dims):
        vals = [v[d] for v in vectors if d < len(v) and not math.isnan(v[d])]
        if not vals:
            vals = [0.5]
        m = mean(vals)
        s = std(vals)
        template.append(round(m, 4))
        variances.append(round(max(0.003, (s ** 2) + epsilon), 5))

    return template, variances

FEATURE_WEIGHTS = np.array([
    1.4, 1.4, 1.4, 1.4, # Reaction times
    1.2, 1.2, 1.2, 1.2, # ITIs
    2.0, 1.8,           # Dwell Duration & Variance
    1.3, 1.5, 1.3, 1.5, # Spatial accuracy offsets & variances
    1.1,                # Error rate
    1.7, 1.5,           # Path efficiency & jitter
    2.2, 2.0,           # Velocities (mean & peak)
    2.2, 2.2,           # Acceleration & Neuromuscular Jerk
    1.8,                # Curvature
    1.6,                # Overshoots
    1.7,                # Time-to-peak ratio
    1.6, 1.6, 1.8, 1.5  # Cognitive flight & ratio
])

def compute_biometric_distance(live_vector: List[float], template: List[float], variances: List[float]) -> (float, Dict[str, Any]):
    n = min(len(live_vector), len(template), len(variances), len(FEATURE_WEIGHTS))
    weighted_sum_sq = 0.0
    total_weight = 0.0
    dim_scores = []

    for d in range(n):
        diff = live_vector[d] - template[d]
        var = max(0.002, variances[d])
        w = FEATURE_WEIGHTS[d]
        dist_sq = (diff ** 2) / var
        weighted_sum_sq += w * dist_sq
        total_weight += w
        dim_scores.append(round(math.sqrt(dist_sq), 2))

    norm_dist = math.sqrt(weighted_sum_sq / total_weight) * 3.5
    return round(norm_dist, 2), {"dim_scores": dim_scores}

def sync_from_mongodb(force: bool = False) -> Dict[str, Any]:
    global mongo_client, mongo_db, last_sync_timestamp, user_profiles
    uri = get_mongo_uri()

    if not uri:
        return {
            "configured": False,
            "connected": False,
            "db_name": "None",
            "collections": [],
            "active_collection": "None",
            "total_operatives_in_db": len(user_profiles),
            "connection_uri_type": "None",
        }

    now = datetime.utcnow().timestamp() * 1000
    if not force and len(user_profiles) > 0 and (now - last_sync_timestamp < 30000):
        return {
            "configured": True,
            "connected": True,
            "db_name": mongo_db.name if mongo_db is not None else "MongoDB",
            "collections": ["operatives"],
            "active_collection": "operatives",
            "total_operatives_in_db": len(user_profiles),
            "connection_uri_type": "MongoDB Atlas",
        }

    all_scanned = []
    total_loaded = 0

    try:
        if mongo_client is None:
            mongo_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        
        # Test server connection
        mongo_client.admin.command('ping')
        # Safely assign database without throwing ConfigurationError
        mongo_db = mongo_client["neuro_defense_db"]
        primary_db_name = mongo_db.name
        dbs_to_scan = [primary_db_name]

        try:
            db_list = mongo_client.list_database_names()
            user_dbs = [d for d in db_list if d not in ["admin", "local", "config"]]
            if user_dbs:
                dbs_to_scan = user_dbs
                if primary_db_name not in user_dbs:
                    mongo_db = mongo_client[user_dbs[0]]
                    primary_db_name = user_dbs[0]
            if primary_db_name not in dbs_to_scan:
                dbs_to_scan.insert(0, primary_db_name)
        except Exception:
            pass

        active_col = "operatives"
        for db_name in dbs_to_scan:
            try:
                curr_db = mongo_client[db_name]
                col_names = curr_db.list_collection_names()
                for c_name in col_names:
                    all_scanned.append(f"{db_name}.{c_name}")
                    docs = list(curr_db[c_name].find().limit(500))
                    for doc in docs:
                        prof = normalize_doc(doc, f"{db_name}.{c_name}")
                        if prof:
                            user_profiles[prof["participant_id"]] = prof
                            total_loaded += 1
                            active_col = f"{db_name}.{c_name}"
            except Exception as edb:
                print(f"[MONGODB] Scan error {db_name}: {edb}")

        last_sync_timestamp = now
        return {
            "configured": True,
            "connected": True,
            "db_name": primary_db_name,
            "collections": all_scanned,
            "active_collection": active_col,
            "total_operatives_in_db": len(user_profiles),
            "connection_uri_type": "MongoDB Atlas",
        }
    except Exception as e:
        print(f"[MONGODB CONNECT ERROR] {e}")
        return {
            "configured": True,
            "connected": False,
            "db_name": "Error",
            "collections": [],
            "active_collection": "None",
            "error": str(e),
            "total_operatives_in_db": len(user_profiles),
            "connection_uri_type": "MongoDB Atlas",
        }

# Initial background sync
try:
    sync_from_mongodb(True)
except Exception as e:
    print(f"Startup MongoDB sync notice: {e}")

# --- API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>App is running</h1>", status_code=200)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/status")
async def get_status():
    diag = sync_from_mongodb(False)
    return {
        **diag,
        "total_operatives": len(user_profiles),
        "operatives_sample": list(user_profiles.keys())[:10],
    }

@app.post("/api/refresh")
async def refresh_db():
    diag = sync_from_mongodb(True)
    return {
        **diag,
        "total_operatives": len(user_profiles),
        "operatives": list(user_profiles.keys()),
    }

@app.get("/check/{participant_id}")
async def check_participant(participant_id: str):
    p_id = participant_id.strip().upper()
    if len(user_profiles) == 0:
        sync_from_mongodb(True)

    profile = user_profiles.get(p_id)
    if profile:
        return {
            "exists": True,
            "participant_id": profile["participant_id"],
            "enrolled_at": profile["enrolled_at"],
            "rounds_count": profile["rounds_count"],
            "source": profile.get("source", "MongoDB"),
        }
    return {"exists": False, "participant_id": p_id}

@app.get("/api/operatives")
async def list_operatives():
    diag = sync_from_mongodb(False)
    operatives = [
        {
            "participant_id": u["participant_id"],
            "enrolled_at": u["enrolled_at"],
            "rounds_count": u.get("rounds_count", 1),
            "template_dim": len(u.get("template", [])),
            "source": u.get("source", "MongoDB"),
        }
        for u in user_profiles.values()
    ]
    return {
        "operatives": operatives,
        "total": len(operatives),
        "db_source": f"MongoDB ({diag['db_name']})" if diag.get("connected") else ("MongoDB (Connecting...)" if diag.get("configured") else "No Database Configured"),
        "diagnostics": diag,
    }

@app.delete("/api/operatives/{participant_id}")
async def delete_operative(participant_id: str):
    p_id = participant_id.strip().upper()
    if p_id in user_profiles:
        del user_profiles[p_id]

    if mongo_db is not None:
        try:
            mongo_db["operatives"].delete_one({"participant_id": p_id})
        except Exception:
            pass

    return {"success": True, "message": f"Operative {p_id} removed."}

@app.post("/enroll")
async def enroll_protocol(payload: Dict[str, Any]):
    p_id = payload.get("participant_id")
    rounds = payload.get("rounds", [])
    if not p_id or not rounds:
        raise HTTPException(status_code=400, detail="Valid participant_id and session rounds required.")

    p_id = str(p_id).strip().upper()
    cognitive_data = payload.get("cognitive_data")

    vectors = [extract_features(r, cognitive_data) for r in rounds]
    template, variances = build_biometric_template(vectors)

    profile = {
        "participant_id": p_id,
        "enrolled_at": datetime.utcnow().isoformat(),
        "template": template,
        "variances": variances,
        "rounds_count": len(rounds),
        "source": "MongoDB (operatives)",
    }
    user_profiles[p_id] = profile

    saved_to_mongo = False
    if mongo_db is not None:
        try:
            mongo_db["operatives"].update_one(
                {"participant_id": p_id},
                {"$set": {
                    "participant_id": p_id,
                    "enrolled_at": profile["enrolled_at"],
                    "template": template,
                    "variances": variances,
                    "rounds_count": len(rounds),
                    "raw_rounds": rounds,
                    "cognitive_data": cognitive_data,
                    "updated_at": datetime.utcnow().isoformat()
                }},
                upsert=True
            )
            saved_to_mongo = True
        except Exception as e:
            print(f"MongoDB write error: {e}")

    return {
        "success": True,
        "participant_id": p_id,
        "template_dimensions": len(template),
        "saved_to_mongo": saved_to_mongo,
        "message": f"Operative {p_id} baseline profile generated and calibrated."
    }

@app.post("/verify")
async def verify_protocol(payload: Dict[str, Any]):
    p_id = payload.get("participant_id")
    rounds = payload.get("rounds", [])
    if not p_id or not rounds:
        raise HTTPException(status_code=400, detail="Valid participant_id and verification round required.")

    p_id = str(p_id).strip().upper()
    if len(user_profiles) == 0:
        sync_from_mongodb(True)

    profile = user_profiles.get(p_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No baseline biometric profile found for Operative {p_id}. Please Enroll first.")

    cognitive_data = payload.get("cognitive_data")
    live_vector = extract_features(rounds[0], cognitive_data)

    distance, details = compute_biometric_distance(live_vector, profile["template"], profile["variances"])
    threshold = 3.2
    is_match = distance <= threshold

    confidence = round(max(0.0, min(100.0, 100.0 - (distance / threshold * 50.0))), 1)

    # Log verification attempt to MongoDB
    if mongo_db is not None:
        try:
            mongo_db["verification_logs"].insert_one({
                "participant_id": p_id,
                "timestamp": datetime.utcnow().isoformat(),
                "distance": distance,
                "threshold": threshold,
                "match": is_match,
                "confidence": f"{confidence}%",
                "live_vector": live_vector
            })
        except Exception:
            pass

    return {
        "match": is_match,
        "score": distance,
        "threshold": threshold,
        "confidence": f"{confidence}%",
        "participant_id": p_id,
        "details": details
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main_server:app", host="0.0.0.0", port=port, reload=False)
