# ANPR System

A real-time Automatic Number Plate Recognition system designed for edge deployment (gate execution).
Uses YOLOv8 for vehicle detection, OpenCV Haar Cascades for plate localization, and EasyOCR for character recognition.

## Features
- **Real-time Detection**: Processes video from webcam or IP camera.
- **Hybrid Pipeline**: 
    1. YOLOv8 detects vehicle.
    2. Haar Cascade refines plate location.
    3. EasyOCR reads text.
- **Database Integration**: SQLite database stores authorized vehicles and logs entries.
- **Modular Code**: Separate modules for DB, Detection, and OCR.

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Using a GPU (CUDA) is highly recommended for `ultralytics` and `easyocr`.*

2. **Project Structure**:
   - `main.py`: Main application loop.
   - `test.py`: Script to test on single images.
   - `src/`: Source modules.
   - `data/`: Database storage.

## Usage

### Run Real-Time System
```bash
python main.py
```
- Press `q` to exit.
- The system will auto-create `data/anpr.db`.

### Test on Image
```bash
python test.py path/to/car_image.jpg
```

## Configuration
- **Camera**: Edit `main.py` line `cap = cv2.VideoCapture(0)` to change to a file path or RTSP URL.
- **Authorized Vehicles**: Add them in `main.py` or modify the database directly.

## Deployment Notes
- **Lighting**: Ensure good lighting on the plates.
- **Camera Angle**: The system works best when vehicles are approaching head-on or at slight angles.
- **Performance**: On a CPU, frame rate might be low. Decrease resolution or skipping frames (in `main.py`) can help.
