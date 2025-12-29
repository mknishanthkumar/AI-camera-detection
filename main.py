import cv2
import time
from src.database import ANPRDatabase
from src.detector import VehicleDetector
from src.ocr import OCRSystem

def main():
    print("[Starting] ANPR System Initializing...")
    
    # Initialize components
    db = ANPRDatabase()
    detector = VehicleDetector() # default yolov8n.pt
    ocr = OCRSystem()
    
    # Add dummy authorized vehicles for testing
    db.add_authorized_vehicle("KA01AB1234", "Admin User")
    db.add_authorized_vehicle("B00S8005", "Test User")
    db.add_authorized_vehicle("DL01CD5678", "Test User")
    db.add_authorized_vehicle("MH20EE7602", "Test User")
    db.add_authorized_vehicle("MHZOEE760", "Test User")


    
    # Open Camera (0 for webcam, or RTSP url)
    # Using cv2.CAP_DSHOW on Windows can sometimes fix initialization issues
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("[Error] Could not open camera. Please check your webcam connection.")
        return

    print("[Ready] Press 'q' to exit. Starting main loop...")
    
    # Config
    frame_count = 0
    process_every_n_frames = 5 # Skip frames for performance
    last_log_time = {} # plate -> time
    LOG_COOLDOWN = 10 # seconds

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
                        print(f"[OCR] Detected: '{text}' (Conf: {conf:.2f})")
                        
                        color = (0, 0, 255) # Red for unauthorized
                        status = "Access Denied"
                        
                        is_auth, owner = db.is_authorized(text)
                        
                        if is_auth:
                            color = (0, 255, 0) # Green for authorized
                            status = f"Access Granted ({owner})"
                            print(f"[Success] Authorized vehicle verified: {text}")
                            
                            # Log to DB with cooldown
                            current_time = time.time()
                            if text not in last_log_time or (current_time - last_log_time[text] > LOG_COOLDOWN):
                                db.log_entry(text, location="Main Gate", confidence=conf)
                                last_log_time[text] = current_time
                                print(f"[DB] Logged entry for {text}")
                        else:
                             print(f"[Info] Vehicle '{text}' is NOT authorized.")

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
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[Info] User requested exit.")
            break
            
    cap.release()
    cv2.destroyAllWindows()
    db.close()

if __name__ == "__main__":
    main()
