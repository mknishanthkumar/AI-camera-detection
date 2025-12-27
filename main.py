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
    db.add_authorized_vehicle("MH12DE4567", "Test User")
    
    # Open Camera (0 for webcam, or RTSP url)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("[Error] Could not open camera.")
        return

    print("[Ready] Press 'q' to exit.")
    
    # Config
    frame_count = 0
    process_every_n_frames = 5 # Skip frames for performance
    last_log_time = {} # plate -> time
    LOG_COOLDOWN = 10 # seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        display_frame = frame.copy()
        
        # Only process every Nth frame to save CPU/GPU if needed
        # But we want smooth tracking, so maybe just OCR less often? 
        # For simplicity in this logical loop, we run detection every frame but OCR only on good detections.
        
        vehicles = detector.detect_vehicles(frame)
        
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
                if plate_img.shape[0] > 20 and plate_img.shape[1] > 60:
                    text, conf = ocr.extract_text(plate_img)
                    
                    if text and conf > 0.4:
                        color = (0, 0, 255) # Red for unauthorized
                        status = "Access Denied"
                        
                        is_auth, owner = db.is_authorized(text)
                        if is_auth:
                            color = (0, 255, 0) # Green for authorized
                            status = f"Access Granted ({owner})"
                            
                            # Log to DB with cooldown
                            current_time = time.time()
                            if text not in last_log_time or (current_time - last_log_time[text] > LOG_COOLDOWN):
                                db.log_entry(text, confidence=conf)
                                last_log_time[text] = current_time
                        
                        # Display Text
                        cv2.putText(display_frame, f"{text} [{conf:.2f}]", (abs_px1, abs_py1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                        cv2.putText(display_frame, status, (abs_px1, abs_py2 + 25), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Show Output
        cv2.imshow('ANPR System', display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    db.close()

if __name__ == "__main__":
    main()
