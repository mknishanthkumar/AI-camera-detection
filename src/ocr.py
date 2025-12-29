import easyocr
import cv2
import numpy as np
import re

class OCRSystem:
    def __init__(self, languages=['en']):
        """
        Initialize the OCR system.
        """
        print("[OCR] Initializing EasyOCR... (this might take a while on first run)")
        self.reader = easyocr.Reader(languages) 
        print("[OCR] Initialization Complete.")

    def preprocess(self, image):
        """
        Apply preprocessing to improve OCR accuracy.
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Noise removal
        noise_removed = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Adaptive Thresholding to isolate characters
        # thresh = cv2.adaptiveThreshold(noise_removed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        #                                cv2.THRESH_BINARY, 11, 2)
        # Using simple thresholding sometimes works better for plates if high contrast
        
        return noise_removed

    def extract_text(self, plate_image):
        """
        Extract text from the plate image.
        Returns: (text, confidence)
        """
        if plate_image is None or plate_image.size == 0:
            return None, 0.0

        processed = self.preprocess(plate_image)
        
        # Read text
        # detail=0 returns just the list of text
        # detail=1 returns (bbox, text, prob)
        results = self.reader.readtext(processed, detail=1)
        
        if not results:
            return None, 0.0

        # Heuristic: Get this result with highest confidence and reasonable length
        best_text = ""
        best_conf = 0.0

        for (_, text, conf) in results:
            # Clean text: keep only alphanumeric
            clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
            
            # Basic validation for plate length (varies by country, assuming > 3)
            if len(clean_text) > 3 and conf > best_conf:
                best_text = clean_text
                best_conf = conf

        return best_text, best_conf
