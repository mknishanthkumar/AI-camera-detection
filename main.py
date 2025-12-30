import cv2
import time
from datetime import datetime
import subprocess
import webbrowser
import os
import json
import sys
from src.database import ANPRDatabase
from src.detector import VehicleDetector
from src.ocr import OCRSystem

def main():
    print("[Starting] Location Service...")
    
    # 0. Kill stale Node.js processes (Windows specific, simplifies re-runs)
    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # 1. Start Node.js Server
    # Using shell=True for windows to find node in path easily, or full path if needed.
    # We assume 'node' is in PATH.
    try:
        node_process = subprocess.Popen(["node", "location_server.js"], cwd=os.getcwd(), shell=True)
    except Exception as e:
        print(f"[Error] Failed to start Node.js server: {e}")
        return

    # 2. Open Browser
    print("[Action] Opening browser for location consent...")
    time.sleep(2) # Give server a moment
    webbrowser.open("http://localhost:3000")
    
    # 3. Wait for Location (or Denial)
    print("[Waiting] Please click 'Allow Location' in the browser...")
    gps_state_path = os.path.join("data", "gps_state.json")
    
    # Reset state file to ensure we wait for a fresh update? 
    # Or just check if it exists. Ideally we'd want a fresh signal.
    # Let's check for modification time or just existence of values.
    # For now, simplistic check: wait until file exists and timestamp is recent 
    # OR just wait for user to say "I did it" - but requirement says "Wait until user clicks".
    # Best way: Check if file modifies.
    
    initial_mtime = 0
    if os.path.exists(gps_state_path):
        initial_mtime = os.path.getmtime(gps_state_path)
        
    waiting = True
    while waiting:
        if os.path.exists(gps_state_path):
            current_mtime = os.path.getmtime(gps_state_path)
            if current_mtime > initial_mtime:
                # File updated!
                print("[Ready] Location signal received. Starting ANPR...")
                waiting = False
            else:
                time.sleep(1)
        else:
            time.sleep(1)

    print("[Starting] ANPR System Initializing...")
    
    # Initialize components
    db = ANPRDatabase()
    detector = VehicleDetector() # default yolov8n.pt
    ocr = OCRSystem()
    
    # Add dummy authorized vehicles for testing
    db.add_authorized_vehicle("KA01AB1234", "Admin User")
    db.add_authorized_vehicle("KA01AB5678", "other user")


    
    # Open Camera (0 for webcam, or RTSP url)
    # Using cv2.CAP_DSHOW on Windows can sometimes fix initialization issues
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("[Error] Could not open camera. Please check your webcam connection.")
        # Kill node before exit
        node_process.terminate()
        return

    print("[Ready] Press 'q' to exit. Starting main loop...")
    
    # Config
    frame_count = 0
    process_every_n_frames = 5 # Skip frames for performance
    last_log_time = {} # plate -> time
    LOG_COOLDOWN = 10 # seconds

    try:
        while True:
            # Debug: Print a dot every 60 frames to show life, or on first frame
            if frame_count == 0:
                print("[Debug] Attempting to read first frame...")

            ret, frame = cap.read()
            if not ret:
                print("[Error] Failed to grab frame. Camera stream ended or disconnected.")
                break
                
            if frame_count == 0:
                print("[Debug] First frame read successfully. Dimensions:", frame.shape)

            frame_count += 1
            display_frame = frame.copy()
            
            # Only process every Nth frame to save CPU/GPU if needed
            # But we want smooth tracking, so maybe just OCR less often? 
            # For simplicity in this logical loop, we run detection every frame but OCR only on good detections.
            
            # Performance check: only run detection logic if frame read is fine
            try:
                vehicles = detector.detect_vehicles(frame)
            except Exception as e:
                print(f"[Error] Detection failed: {e}")
                vehicles = []
            
            for (v_box, v_conf, v_cls) in vehicles:
                x1, y1, x2, y2 = map(int, v_box)
                
                # Draw Vehicle Box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display_frame, "Vehicle", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Crop Vehicle
                vehicle_img = frame[y1:y2, x1:x2]
                
                # Detect Plate within Vehicle
                plate_img, p_box = detector.detect_plate(vehicle_img)
                
                if plate_img is not None and p_box is not None:
                    px1, py1, px2, py2 = p_box
                    # Draw Plate Box (relative to frame)
                    abs_px1 = x1 + px1
                    abs_py1 = y1 + py1
                    abs_px2 = x1 + px2
                    abs_py2 = y1 + py2
                    
                    cv2.rectangle(display_frame, (abs_px1, abs_py1), (abs_px2, abs_py2), (0, 255, 0), 2)
                    
                    # Run OCR
                    # Only run OCR if plate resolution is decent
                    # Lowered thresholds for testing
                    if plate_img.shape[0] > 10 and plate_img.shape[1] > 30:
                        text, conf = ocr.extract_text(plate_img)
                        
                        # Lowered thresholds for testing
                        if text and conf > 0.3: # Lower confidence slightly
                            # Debug: Print what we see
                            # print(f"[OCR] Detected: '{text}' (Conf: {conf:.2f})")
                            
                            color = (0, 0, 255) # Red for unauthorized
                            status = "Access Denied"
                            
                            is_auth, owner = db.is_authorized(text)
                            
                            if is_auth:
                                color = (0, 255, 0) # Green for authorized
                                status = f"Access Granted ({owner})"
                                # print(f"[Success] Authorized vehicle verified: {text}")
                                
                                # Log to DB with cooldown
                                current_time = time.time()
                                if text not in last_log_time or (current_time - last_log_time[text] > LOG_COOLDOWN):
                                    db.log_entry(text, location="Main Gate", confidence=conf)
                                    last_log_time[text] = current_time
                                    
                                    # Output Format Requirement:
                                    # <Detected Plate>, <Owner Name>, <Vehicle Name>, <Latitude>, <Longitude>, <Timestamp>
                                    
                                    # Fetch current location state directly
                                    lat = ""
                                    long = ""
                                    try:
                                        with open(gps_state_path, 'r') as f:
                                            st = json.load(f)
                                            lat = st.get("lat", "")
                                            long = st.get("long", "")
                                    except:
                                        pass
                                    
                                    # Vehicle Name Lookup
                                    veh_name = "Unknown Vehicle"
                                    vehicles_db_path = os.path.join("data", "vehicles.db.json")
                                    if os.path.exists(vehicles_db_path):
                                        try:
                                            with open(vehicles_db_path, 'r') as vf:
                                                v_data = json.load(vf)
                                                # Find vehicle by plate
                                                # v_data is a list of objects
                                                for v_obj in v_data:
                                                    if v_obj.get("numberPlate") == text:
                                                        veh_name = v_obj.get("vehicleName", "Unknown Vehicle") or "Unknown Vehicle"
                                                        break
                                        except:
                                            pass
                                    
                                    # Construct Timestamp
                                    ts_str = datetime.now().isoformat()
                                    
                                    # Print SPECIAL OUTPUT
                                    print(f"{text}, {owner}, {veh_name}, {lat}, {long}, {ts_str}")

                            # else:
                                 # print(f"[Info] Vehicle '{text}' is NOT authorized.")

                            # Display Text
                            cv2.putText(display_frame, f"{text} [{conf:.2f}]", (abs_px1, abs_py1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                            cv2.putText(display_frame, status, (abs_px1, abs_py2 + 25), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                else:
                    # Debug: Draw yellow box if vehicle found but NO plate found
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(display_frame, "No Plate", (x1, y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Show Output
            cv2.imshow('ANPR System', display_frame)
            
            # Force focus on start (first few frames)
            if frame_count < 10:
                 try:
                     cv2.setWindowProperty('ANPR System', cv2.WND_PROP_TOPMOST, 1)
                     # cv2.setWindowProperty('ANPR System', cv2.WND_PROP_TOPMOST, 0) # Immediately disable always-on-top so user can alt-tab?
                     # Let's just set it once. 
                 except:
                     pass

            # Enable 'X' button close
            try:
                if cv2.getWindowProperty('ANPR System', cv2.WND_PROP_VISIBLE) < 1:
                    print("[Info] User closed window.")
                    break
            except:
                pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[Info] User requested exit.")
                break
    except KeyboardInterrupt:
        print("[Info] Interrupted.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()
        # Kill node
        # subprocess.Popen("taskkill /F /T /PID " + str(node_process.pid), shell=True) # Windows specific
        node_process.kill()

if __name__ == "__main__":
    main()
