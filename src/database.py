import sqlite3
import os
import json
from datetime import datetime

class ANPRDatabase:
    def __init__(self, db_path='data/anpr.db'):
        """Initialize the database connection and create tables if they don't exist."""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables for the system."""
        # Table for authorized vehicles
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS authorized_vehicles (
                plate_number TEXT PRIMARY KEY,
                owner_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table for logging access (authorized only)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT,
                timestamp DATETIME,
                location TEXT,
                confidence REAL,
                image_path TEXT
            )
        ''')

        # Table for logging ALL detections (raw feed)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS all_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT,
                timestamp DATETIME,
                confidence REAL,
                is_authorized BOOLEAN
            )
        ''')
        self.conn.commit()

    def is_authorized(self, plate_number):
        """
        Check if a vehicle is authorized.
        Returns: (bool, owner_name)
        """
        # Normalize: remove spaces, uppercase
        clean_plate = plate_number.replace(' ', '').upper()
        
        self.cursor.execute('SELECT owner_name FROM authorized_vehicles WHERE plate_number = ?', (clean_plate,))
        result = self.cursor.fetchone()
        
        if result:
            return True, result[0]
        return False, None

    def log_entry(self, plate_number, location="Main Gate", confidence=0.0, image_path=None):
        """Log a vehicle entry (Authorized)."""
        clean_plate = plate_number.replace(' ', '').upper()
        timestamp = datetime.now()
        
        print(f"[DB] Logging Authorized Entry: {clean_plate} at {timestamp}")
        
        self.cursor.execute('''
            INSERT INTO access_logs (plate_number, timestamp, location, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (clean_plate, timestamp, location, confidence, image_path))
        self.conn.commit()

        # Log to human-readable JSON
        self._log_to_json(clean_plate, location, timestamp)

    def _log_to_json(self, plate_number, location, timestamp):
        """Helper to log entry to human-readable JSON file."""
        json_path = os.path.join(os.path.dirname(self.db_path), 'vehicles.db.json')
        
        data = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []

        # Find if vehicle exists
        vehicle_entry = next((item for item in data if item["numberPlate"] == plate_number), None)
        
        # Prepare location object
        lat = ""
        long = ""
        
        # Read GPS State (Hybrid Integration)
        # Requirement: Read from data/gps_state.json
        state_path = os.path.join(os.path.dirname(self.db_path), 'gps_state.json')
        if os.path.exists(state_path):
             try:
                 with open(state_path, 'r') as f:
                     state = json.load(f)
                     # Check freshness? For now, just use what's there as per simple requirement.
                     # Verify if it has data
                     if state.get("lat") and state.get("long"):
                         lat = state["lat"]
                         long = state["long"]
             except Exception as e:
                 print(f"[DB] Error reading GPS state: {e}")

        loc_entry = {
            "lat": str(lat),
            "long": str(long),
            "timestamp": str(timestamp)
        }

        if vehicle_entry:
            vehicle_entry["locations"].append(loc_entry)
        else:
            # Fetch owner name
            is_auth, owner_name = self.is_authorized(plate_number)
            new_entry = {
                "ownerName": owner_name if owner_name else "Unknown",
                "vehicleName": "", # Placeholder as requested
                "numberPlate": plate_number,
                "locations": [loc_entry]
            }
            data.append(new_entry)

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)


    def log_detection(self, plate_number, confidence=0.0, is_authorized=False):
        """Log ANY detected vehicle."""
        clean_plate = plate_number.replace(' ', '').upper()
        timestamp = datetime.now()
        
        # print(f"[DB] Logging Detection: {clean_plate}") # Optional verbose log
        
        self.cursor.execute('''
            INSERT INTO all_detections (plate_number, timestamp, confidence, is_authorized)
            VALUES (?, ?, ?, ?)
        ''', (clean_plate, timestamp, confidence, is_authorized))
        self.conn.commit()

    def add_authorized_vehicle(self, plate_number, owner_name):
        """Add a new authorised vehicle to the database."""
        clean_plate = plate_number.replace(' ', '').upper()
        try:
            self.cursor.execute('INSERT INTO authorized_vehicles (plate_number, owner_name) VALUES (?, ?)', 
                                (clean_plate, owner_name))
            self.conn.commit()
            print(f"[DB] Added vehicle {clean_plate} for {owner_name}")
            return True
        except sqlite3.IntegrityError:
            print(f"[DB] Vehicle {clean_plate} already exists.")
            return False

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    # Test the module
    db = ANPRDatabase('anpr_system/data/test.db')
    db.add_authorized_vehicle("ABC1234", "John Doe")
    is_auth, owner = db.is_authorized("ABC 1234")
    print(f"Is Authorized: {is_auth}, Owner: {owner}")
    db.log_entry("ABC1234")
    db.close()
