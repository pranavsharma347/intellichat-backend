# test_db.py
from database import engine

try:
    connection = engine.connect()
    print("✅ Database connection successful!")
    connection.close()
except Exception as e:
    print(f"❌ Connection fail hui: {e}")