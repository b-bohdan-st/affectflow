# AffectFlow

**Real-time Fatigue and Attention Analysis using Computer Vision**

A desktop application that analyzes user fatigue and attention level in real time using webcam video and facial landmark detection.

---

## About The Project

AffectFlow is a desktop application designed to monitor fatigue and attention levels using computer vision techniques.

The system analyzes facial features in real time and evaluates:

- Eye blinking patterns (EAR)
- Yawning detection (MAR)
- Gaze direction
- Head position

All processing is performed locally — no cloud services required.

---

## Architecture

### Electron Frontend

- Webcam capture  
- User interface  
- Charts visualization  
- Communication with backend  

### Python Analysis Module

- MediaPipe FaceMesh landmark detection  
- EAR calculation (Eye Aspect Ratio)  
- MAR calculation (Mouth Aspect Ratio)  
- Fatigue scoring algorithm  
- Attention estimation  

**Data flow:**  
Camera → Electron (JS) → Python analysis → Metrics → UI update

---

## Built With

- Electron  
- HTML / CSS  
- JavaScript  
- Chart.js  
- Python  
- MediaPipe  
- OpenCV  

---

## Features

- Real-time fatigue monitoring  
- Attention level estimation  
- Local processing (privacy friendly)  
- Blink detection algorithm  
- Yawn detection  
- Automatic break recommendation  
- Interactive statistics visualization  
- Multi-page desktop interface  

---

## Screenshots

### Home (Live Analysis)

![Home](https://i.ibb.co/qYnDb64J/Home.png)

### Statistics (Charts)

![Statistics](https://i.ibb.co/MkCGyV5D/Statistics.png)

---

## Getting Started

### Requirements

Make sure you have installed:

- **Node.js** (LTS version recommended)  
- **Python 3.10+** (recommended)

---

### Installation

1. Clone the repository:

```bash
git clone https://github.com/b-bohdan-st/affectflow.git
cd affectflow
```

2. Install Node.js dependencies:

```bash
npm install
```

3. Install Python dependencies:

```bash
pip install mediapipe==0.10.21 opencv-python numpy pygame pyqt6
```

4. Start the application:

```bash
npm start
```

---

## Usage

1. Launch the application  
2. Press **Start analysis**  
3. Real-time monitoring begins  
4. View statistics in the Statistics tab  

---

## Roadmap

- User profiles  
- Custom AI model training  
- Model sharing between users  
- Extended analytics system  
- Mobile companion  

---

## Practical Applications

- Education and learning focus monitoring  
- Workplace productivity  
- Digital wellbeing  
- Ergonomic analysis  

---

## Author

Bohdan Bondar

---

## License

Educational project.
