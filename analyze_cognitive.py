from pymongo import MongoClient
import json

# 1. Connect to your database
MONGO_URI = "mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)

# 2. Point to the correct database and collection from the screenshot
db = client['behavior_biometrics'] 
collection = db['raw_telemetry']

# 3. Fetch the test subject's document
subject_id = "P01_TEST" # Bumping to TEST3 for your next run
user_data = collection.find_one({"participant_id": subject_id})

if user_data and "cognitive_data" in user_data:
    cog_data = user_data["cognitive_data"]
    
    # 3. Extract and calculate averages
    fam_flights = cog_data["familiar"]["flight_times"]
    unfam_flights = cog_data["unfamiliar"]["flight_times"]
    
    fam_avg = sum(fam_flights) / len(fam_flights) if fam_flights else 0
    unfam_avg = sum(unfam_flights) / len(unfam_flights) if unfam_flights else 0
    
    # 4. Print the analytical comparison
    print(f"=== COGNITIVE LOAD ANALYSIS FOR: {subject_id} ===")
    print(f"Familiar PIN (Muscle Memory):")
    print(f"  -> Raw Flights (ms): {fam_flights}")
    print(f"  -> Average Flight:   {fam_avg:.2f} ms")
    print(f"\nUnfamiliar PIN (Cognitive Load):")
    print(f"  -> Raw Flights (ms): {unfam_flights}")
    print(f"  -> Average Flight:   {unfam_avg:.2f} ms")
    
    variance = unfam_avg - fam_avg
    print(f"\nCognitive Hesitation Variance: +{variance:.2f} ms")

else:
    print(f"No cognitive data found for {subject_id}.")