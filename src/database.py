import sqlite3
import os
from datetime import datetime

class ANPRDatabase:
    def __init__(self, db_path='data/anpr.db'):
        """Initialize the database connection and create tables if they don't exist."""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
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

        # Table for logging access
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
        """Log a vehicle entry."""
        clean_plate = plate_number.replace(' ', '').upper()
        timestamp = datetime.now()
        
        print(f"[DB] Logging entry for {clean_plate} at {timestamp}")
        
        self.cursor.execute('''
            INSERT INTO access_logs (plate_number, timestamp, location, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (clean_plate, timestamp, location, confidence, image_path))
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
