# SlackOff Detector

SlackOff Detector is a Python-based focus monitoring system that uses computer vision to detect common signs of distraction or reduced attention during a work or study session.

The application monitors webcam input for events such as:

- Phone usage
- Prolonged eye closure
- Looking away from the screen

Individual detection modules report their observations to a central controller. The controller evaluates the combined state of the user and triggers a reaction when distraction is confirmed.

> This repository currently contains the local desktop version of SlackOff Detector. It does not yet include AWS, Fire TV, Vega OS, or cloud deployment features.

---

## Project Status

SlackOff Detector is currently under active development.

### Currently implemented

- Phone detection using YOLO and OpenCV
- Eye-closure monitoring
- Looking-away monitoring
- Central controller for combining detector states
- Queue-based communication between modules
- Configurable distraction confirmation logic
- Reaction window with visual and audio feedback

###**Technology Stack**
Python for application logic
OpenCV for webcam access and image processing
Ultralytics YOLO for phone detection
NumPy for numerical and frame operations
Pygame for reaction visuals and audio
Python queue for communication between modules
Python threading for running components concurrently
Python time for state duration and confirmation timing

The exact dependencies may change as development continues.

**Requirements
**
Before running SlackOff Detector, make sure the system has:

Python 3.10 or newer
A working webcam
A supported operating system
Permission for Python to access the webcam
A YOLO model file
Audio output for reaction sounds

A virtual environment is strongly recommended.
### Planned improvements

- Graphical session dashboard
- Focus scoring
- Event history and session statistics
- Improved detector calibration
- User-configurable thresholds
- Background application support
- Better reaction controls
- Privacy settings
- Automated tests
- Application packaging

---



**Disclaimer**

SlackOff Detector is an experimental software project. Detection results may be inaccurate, incomplete, or affected by environmental conditions.

The project is not intended for medical diagnosis, safety-critical monitoring, academic discipline, employment evaluation, or covert surveillance
