import cv2
from ultralytics import YOLO
import numpy as np
import os

class VehicleDetector:
    def __init__(self, model_path='yolov8n.pt'):
        """
        Initialize YOLOv8 for vehicle detection.
        """
        print(f"[Detector] Loading YOLOv8 model: {model_path}...")
        self.model = YOLO(model_path)
        
        # Classes for vehicles in COCO dataset: car(2), motorcycle(3), bus(5), truck(7)
        self.vehicle_classes = [2, 3, 5, 7]
        
        # Load Haar Cascade for Plate Detection as a fallback/refinement
        # Note: In a production environment, training a YOLO model specifically for plates is better.
        # We use Haar here to avoid forcing the user to download custom weights manually.
        try:
            haar_path = os.path.join(cv2.data.haarcascades, 'haarcascade_russian_plate_number.xml')
        except AttributeError:
            # Fallback for older opencv versions or weird installs
            haar_path = 'haarcascade_russian_plate_number.xml'
        
        # Fallback if standard path fails
        if not os.path.exists(haar_path):
            # Try to load from local directory if user supplied it
            haar_path = 'haarcascade_russian_plate_number.xml'
        
        self.plate_cascade = None
        if os.path.exists(haar_path):
             self.plate_cascade = cv2.CascadeClassifier(haar_path)
        else:
            print("[Warning] HAAR Cascade for plates not found. Will return full vehicle crop (lower accuracy).")

    def detect_vehicles(self, frame):
        """
        Detect vehicles in the frame.
        Returns list of (box, confidence, class_id)
        """
        results = self.model(frame, verbose=False)[0]
        detections = []
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls_id in self.vehicle_classes and conf > 0.5:
                # box.xyxy provides [x1, y1, x2, y2]
                detections.append((box.xyxy[0].cpu().numpy(), conf, cls_id))
        
        return detections

    def detect_plate(self, vehicle_image):
        """
        Refine detection to find the plate within a vehicle image.
        Returns: (plate_image, plate_box_relative_to_vehicle)
        """
        if self.plate_cascade is None:
            return vehicle_image, [0, 0, vehicle_image.shape[1], vehicle_image.shape[0]]

        gray = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2GRAY)
        # Tuned parameters: scaleFactor=1.05 (slower but more scales), minNeighbors=3 (less strict)
        plates = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))
        
        if len(plates) > 0:
            # Return the largest detected area
            plates = sorted(plates, key=lambda x: x[2] * x[3], reverse=True)
            (x, y, w, h) = plates[0]
            
            # Padding
            pad_w = int(w * 0.1)
            pad_h = int(h * 0.1)
            h_img, w_img = vehicle_image.shape[:2]
            
            x1 = max(0, x - pad_w)
            y1 = max(0, y - pad_h)
            x2 = min(w_img, x + w + pad_w)
            y2 = min(h_img, y + h + pad_h)
            
            return vehicle_image[y1:y2, x1:x2], [x1, y1, x2, y2]
        
        # Debug: if no plate found, maybe return None but print? 
        return None, None
