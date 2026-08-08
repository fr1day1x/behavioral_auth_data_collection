from pymongo import MongoClient

# 1. Connect to your database
MONGO_URI = "mongodb+srv://kamaltalreja2007_db_user:1122334455667788@cluster0.pmgqtvt.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)

db = client["behavior_biometrics"]
collection = db["raw_telemetry"]

def wipe_legacy_data():
    print("==================================================")
    print(" ⚠️ WARNING: DATABASE PURGE INITIATED ⚠️")
    print("==================================================")
    print(f"Target Database: {db.name}")
    print(f"Target Collection: {collection.name}")
    print("This action will permanently delete ALL behavioral data.")
    
    # Safety lock
    confirmation = input("\nAre you sure you want to proceed? Type 'YES' to confirm: ")
    
    if confirmation == 'YES':
        # delete_many({}) with an empty query matches and deletes everything
        result = collection.delete_many({})
        print(f"\n✅ SUCCESS: {result.deleted_count} legacy profiles have been wiped.")
        print("Your database is now a clean slate for the final data collection phase!")
    else:
        print("\n❌ Operation cancelled. Your data is safe.")

if __name__ == "__main__":
    wipe_legacy_data()