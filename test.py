import cv2
import argparse
from src.detector import VehicleDetector
from src.ocr import OCRSystem

def test_image(image_path):
    print(f"Testing on image: {image_path}")
    
    detector = VehicleDetector()
    ocr = OCRSystem()
    
    frame = cv2.imread(image_path)
    if frame is None:
        print("Error: Could not read image.")
        return

    vehicles = detector.detect_vehicles(frame)
    print(f"Found {len(vehicles)} vehicles.")
    
    for i, (v_box, v_conf, v_cls) in enumerate(vehicles):
        x1, y1, x2, y2 = map(int, v_box)
        vehicle_img = frame[y1:y2, x1:x2]
        
        plate_img, p_box = detector.detect_plate(vehicle_img)
        
        if plate_img is not None:
            text, conf = ocr.extract_text(plate_img)
            print(f"Vehicle {i+1}: Plate Text: '{text}' (Conf: {conf:.2f})")
            
            # Show result
            cv2.imshow(f"Vehicle {i+1} Plate", plate_img)
        else:
            print(f"Vehicle {i+1}: No plate detected.")
            
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Path to image file")
    args = parser.parse_args()
    test_image(args.image)
