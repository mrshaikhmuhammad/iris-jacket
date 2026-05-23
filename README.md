# IRIS Jacket — Intelligent Real-time Impedance Sensing

> **An AI-powered assistive wearable for visually impaired individuals**
> that combines ultrasonic proximity sensing, haptic vibration feedback, computer vision, and Azure cloud intelligence to provide real-time obstacle awareness.

---

## 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Hardware Components](#hardware-components)
4. [Circuit Design (ESP32)](#circuit-design-esp32)
5. [How It Works](#how-it-works)
6. [Mathematical Model — Distance to Vibration Mapping](#mathematical-model)
7. [Risk Level Classification](#risk-level-classification)
8. [Software Stack](#software-stack)
9. [ESP32 Firmware Setup](#esp32-firmware-setup)
10. [Raspberry Pi Setup](#raspberry-pi-setup)
11. [Azure Cloud Setup](#azure-cloud-setup)
12. [Communication Flow](#communication-flow)
13. [Vibration Pattern Reference](#vibration-pattern-reference)
14. [Project File Structure](#project-file-structure)
15. [How to Run the Project](#how-to-run-the-project)
16. [Troubleshooting](#troubleshooting)
17. [Future Improvements](#future-improvements)
18. [Contributors](#contributors)

---

## 📌 Project Overview

The **IRIS Jacket** is a smart assistive wearable designed to help visually impaired people navigate their surroundings safely and independently. The jacket integrates:

- **3× HC-SR04 Ultrasonic Sensors** to detect obstacles in left, center, and right directions
- **7× Vibration (ERM) Motors** embedded in the jacket to provide directional haptic feedback
- **Raspberry Pi Camera Module** for real-time visual scene capture
- **Microsoft Azure IoT & Vision Services** for AI-based scene understanding and risk assessment
- **ESP32 Microcontroller** as the primary embedded controller
- **Raspberry Pi** as the edge computing unit for camera and cloud communication

When an obstacle is detected, the closest ultrasonic sensor triggers the corresponding vibration motor(s) on the same side of the jacket. Simultaneously, the camera sends frames to Azure, which classifies the risk level and sends back a vibration pattern to ESP32 via UDP for pattern-based haptic feedback.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────┐
│                         IRIS JACKET              │
│                                                  │
│   ┌──────────────────────────────────────────┐   │
│   │              ESP32                       │   │
│   │  ┌──────────┐  ┌──────────────────────┐  │   │
│   │  │Ultrasonic│  │  7x Vibration Motors │  │   │
│   │  │Sensors   │  │  (Haptic Feedback)   │  │   │
│   │  │ L / C / R│  │  Left / Center /Right│  │   │
│   │  └────┬─────┘  └───────────┬──────────┘  │   │
│   │       │   Math Model       │             │   │
│   │       └───────────────────►│             │   │
│   └──────────────────────────────────────────┘   │
│                         │ Wi-Fi / Serial         │
│   ┌─────────────────────▼─────────────────────┐  │
│   │           Raspberry Pi                    │  │
│   │  ┌──────────────┐  ┌───────────────────┐  │  │
│   │  │Camera Module │  │  Azure IoT SDK    │  │  │
│   │  │(Image Capture│  │  (MQTT Publisher) │  │  │
│   │  └──────┬───────┘  └─────────┬─────────┘  │  │
│   └─────────┼────────────────────┼────────────┘  │
└─────────────┼────────────────────┼───────────────┘
              │                    │
              ▼                    ▼
     ┌───────────────────────────────────────┐
     │          Microsoft Azure              │
     │  ┌─────────────┐  ┌────────────────┐  │
     │  │ Azure Vision│  │ Azure IoT Hub  │  │
     │  │  (Scene AI) │  │ (MQTT Broker)  │  │
     │  └──────┬──────┘  └───────┬────────┘  │
     │         └────────┬────────┘           │
     │              ┌───▼────────────────┐   │
     │              │ Risk Level Engine  │   │
     │              │ (Pattern Decision) │   │
     │              └───────────────────-┘   │
     └───────────────────┬───────────────────┘
                         │ Signal back to ESP32
                         ▼
              [Pattern-Based Vibration]
```

---

## 🔧 Hardware Components

| Component | Quantity | Purpose |
|---|---|---|
| ESP32 Dev Board | 1 | Main microcontroller (ultrasonic + motors) |
| Raspberry Pi (3B+ or 4) | 1 | Camera control + cloud communication |
| HC-SR04 Ultrasonic Sensor | 3 | Obstacle detection: Left, Center, Right |
| ERM Vibration Motor (3V) | 7 | Directional haptic feedback to user |
| NPN Transistor (e.g. 2N2222) | 7 | Motor driver for each vibration motor |
| Breadboard | 1 | Prototyping and wiring |
| Raspberry Pi Camera Module v2 | 1 | Scene capture for Azure Vision |
| Power Bank / Li-Po Battery | 1 | Portable power supply |
| Jumper Wires | Multiple | Connections |
| 1kΩ Resistors | 7 | Base resistors for NPN transistors |
| Fly-back Diodes (1N4148) | 7 | Motor back-EMF protection |

---

## ⚡ Circuit Design (ESP32)

The circuit (shown above in the Tinkercad diagram) follows this wiring scheme:

### Ultrasonic Sensors (HC-SR04) → ESP32

| Sensor | TRIG Pin | ECHO Pin |
|--------|----------|----------|
| Left   | GPIO 12  | GPIO 13  |
| Center | GPIO 14  | GPIO 27  |
| Right  | GPIO 26  | GPIO 25  |

- **VCC** → 5V (from breadboard power rail)
- **GND** → Common GND

> ⚠️ HC-SR04 ECHO outputs 5V logic. Use a **voltage divider** (1kΩ + 2kΩ) or logic level shifter to bring it down to 3.3V safe for ESP32.

### Vibration Motors → ESP32 (via NPN Transistors)

Each motor is driven by an NPN transistor (BJT switch):

```
ESP32 GPIO ──[1kΩ]───► NPN Base
                       NPN Collector ──► Motor(–)
                       Motor(+) ───────► VCC (3.3V or 5V)
                       NPN Emitter ────► GND
                       [Diode across motor terminals for protection]
```

| Motor Zone | ESP32 GPIO |
|------------|------------|
| Far Left   | GPIO 4     |
| Left       | GPIO 5     |
| Center-Left| GPIO 18    |
| Center     | GPIO 19    |
| Center-Right| GPIO 21   |
| Right      | GPIO 22    |
| Far Right  | GPIO 23    |

### Power

- ESP32 powered via USB or Li-Po via VIN pin
- Raspberry Pi powered separately via USB-C

---

## ⚙️ How It Works

### Step-by-Step Flow

```
Step 1: ESP32 fires TRIG pulse on all 3 ultrasonic sensors
         ↓
Step 2: Measures ECHO pulse duration → converts to distance (cm)
         ↓
Step 3: Mathematical model maps distance → vibration intensity
         ↓
Step 4: Vibration motors on the detected side activate
         ↓
Step 5: Raspberry Pi captures camera frame simultaneously
         ↓
Step 6: Frame sent to Azure Computer Vision via REST API
         ↓
Step 7: Azure analyzes scene → classifies risk level (Low/Medium/High/Critical)
         ↓
Step 8: Azure IoT Hub sends MQTT message back to ESP32
         ↓
Step 9: ESP32 runs pattern-based vibration matching risk level
```

---

## 📐 Mathematical Model

The vibration intensity is not simply on/off — it is **inversely proportional** to distance, creating a smooth warning escalation as the user approaches an obstacle.

### Distance → Vibration Intensity Formula

```
Vibration Intensity (%) = clamp( (MAX_DIST - d) / (MAX_DIST - MIN_DIST) × 100, 0, 100 )
```

Where:
- `d` = measured distance in cm
- `MAX_DIST` = 200 cm (beyond this, no vibration)
- `MIN_DIST` = 10 cm (minimum safe threshold, full intensity)

### Worked Examples

| Distance (cm) | Intensity (%) | Motor Behavior |
|---------------|---------------|----------------|
| > 200         | 0%            | Silent          |
| 150           | 26%           | Light buzz      |
| 100           | 53%           | Moderate buzz   |
| 50            | 79%           | Strong buzz     |
| ≤ 10          | 100%          | Maximum buzz    |

### PWM Implementation on ESP32

```cpp
// Intensity to PWM duty cycle (0–255)
int pwmValue = map(intensity, 0, 100, 0, 255);
analogWrite(MOTOR_PIN, pwmValue);
```

### Directional Logic

The 7 motors are split across 3 zones to match the 3 sensors:

```
Sensor LEFT  → activates motors: [Far Left] + [Left]
Sensor CENTER → activates motors: [Center-Left] + [Center] + [Center-Right]
Sensor RIGHT → activates motors: [Right] + [Far Right]
```

If multiple sensors detect obstacles simultaneously, all corresponding motors activate with proportional intensity.

---

## 🚦 Risk Level Classification

After Azure processes the camera frame, it returns one of four risk levels:

| Risk Level | Trigger Condition | Vibration Pattern |
|------------|-------------------|-------------------|
| 🟢 LOW     | Open space, obstacle > 150cm | Slow single pulse every 2s |
| 🟡 MEDIUM  | Obstacle 80–150cm | Double pulse every 1s |
| 🔴 HIGH    | Obstacle 30–80cm  | Rapid continuous buzz |
| ⚫ CRITICAL | Obstacle < 30cm or moving toward user | SOS-style pattern (3 short, 3 long) |

### Pattern Encoding (ESP32)

```cpp
void runPattern(int riskLevel) {
  switch (riskLevel) {
    case LOW:      singlePulse(2000); break;
    case MEDIUM:   doublePulse(1000); break;
    case HIGH:     continuousBuzz();  break;
    case CRITICAL: sosPattern();      break;
  }
}
```

---

## 💻 Software Stack

| Layer | Technology |
|-------|------------|
| Embedded Firmware | Arduino C++ (ESP32) |
| Edge Computing | Python 3 (Raspberry Pi) |
| Camera | `picamera2` / OpenCV |
| Cloud Platform | Microsoft Azure |
| Vision AI | Azure Computer Vision API |
| IoT Messaging | Azure IoT Hub (MQTT) |
| Communication (Pi ↔ ESP32) | Serial UART or Wi-Fi HTTP |

---

## 🔌 ESP32 Firmware Setup

### Prerequisites

- Arduino IDE 2.x or VS Code + PlatformIO
- ESP32 board package installed in Arduino IDE
  - URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`

### Required Libraries

Install via Arduino Library Manager:

```
- NewPing          (Ultrasonic sensor helper)
- PubSubClient     (MQTT for Azure IoT Hub)
- WiFi             (Built-in ESP32)
- ArduinoJson      (Parse Azure messages)
```

### Flash the Firmware

1. Clone the repository:
   ```bash
   git clone https://github.com/mrshaikhmuhammad/IRIS-Jacket.git
   cd IRIS-Jacket
   ```

2. Open `main.ino` in Arduino IDE

3. Update credentials in `config.h`:
   ```cpp
   #define WIFI_SSID       "your_wifi_ssid"
   #define WIFI_PASSWORD   "your_wifi_password"
   #define AZURE_IOT_HOST  "your-hub.azure-devices.net"
   #define DEVICE_ID       "iris-jacket-esp32"
   #define DEVICE_KEY      "your_sas_token"
   ```

4. Select **Board:** `ESP32 Dev Module` → **Port:** your COM port

5. Click **Upload** ✅

---

## 🍓 Raspberry Pi Setup

### Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
pip3 install azure-iot-device azure-cognitiveservices-vision-computervision \
             picamera2 opencv-python requests
```

### Configure Azure Keys

Create a `.env` file in the project root:

```env
AZURE_VISION_KEY=your_computer_vision_key
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_IOT_CONNECTION_STRING=HostName=...;DeviceId=...;SharedAccessKey=...
```

### Run the Camera Script

```bash
cd IRIS-Jacket/raspberry_pi/
python3 camera_pipeline.py
```

This script:
1. Captures a frame every 500ms using the Pi Camera
2. Sends it to Azure Computer Vision
3. Receives scene description + object bounding boxes
4. Computes risk level
5. Publishes risk level to Azure IoT Hub
6. Azure IoT Hub forwards MQTT message to ESP32

### Auto-start on Boot

```bash
# Add to /etc/rc.local before exit 0
python3 /home/pi/IRIS-Jacket/raspberry_pi/camera_pipeline.py &
```

---

## ☁️ Azure Cloud Setup

### 1. Create Azure IoT Hub

```bash
az iot hub create --name iris-jacket-hub \
                  --resource-group IRISJacket \
                  --sku F1
```

### 2. Register Devices

```bash
# Register ESP32
az iot hub device-identity create \
  --hub-name iris-jacket-hub \
  --device-id iris-jacket-esp32

# Register Raspberry Pi
az iot hub device-identity create \
  --hub-name iris-jacket-hub \
  --device-id iris-jacket-rpi
```

### 3. Create Computer Vision Resource

```bash
az cognitiveservices account create \
  --name iris-vision \
  --resource-group IRISJacket \
  --kind ComputerVision \
  --sku S1 \
  --location eastus
```

### 4. Configure IoT Hub Message Routing

Set up a **cloud-to-device (C2D)** message route:
- Raspberry Pi publishes risk level → IoT Hub
- IoT Hub routes the message → ESP32 device twin / C2D message
- ESP32 subscribes and acts on the received pattern code

---

## 🔄 Communication Flow

```
[HC-SR04 Sensors]
       │ distance (cm)
       ▼
[ESP32 — main.ino]
  - Compute intensity via math model
  - Drive vibration motors via PWM
  - Listen for MQTT messages from Azure
       │ Serial/Wi-Fi
       ▼
[Raspberry Pi — camera_pipeline.py]
  - Capture camera frame
  - POST frame to Azure Vision API
  - Parse response: detect persons, vehicles, stairs
  - Determine risk level (LOW/MEDIUM/HIGH/CRITICAL)
  - Publish to Azure IoT Hub
       │ MQTT over TLS
       ▼
[Azure IoT Hub]
  - Routes C2D message to ESP32
       │ MQTT subscribe
       ▼
[ESP32]
  - Receives risk level integer
  - Runs corresponding vibration pattern
```

---

## 📳 Vibration Pattern Reference

```
LOW      ▐█░░░░░░░░▌ · · ▐█░░░░░░░░▌      (1 pulse every 2 sec)
MEDIUM   ▐██▌·▐██▌·····▐██▌·▐██▌         (2 pulses every 1 sec)
HIGH     ▐████████████████████████▌       (continuous rapid buzz)
CRITICAL ▐█▌▐█▌▐█▌───▐███▌▐███▌▐███▌─── (SOS: 3 short + 3 long)
```

---

## 📁 Project File Structure

```
IRIS-Jacket/
│
├── main.ino                    # ESP32 Arduino firmware
├── config.h                    # Wi-Fi + Azure credentials (not committed)
│
├── raspberry_pi/
│   ├── camera_pipeline.py      # Main Pi script (camera + Azure)
│   ├── azure_vision.py         # Azure Computer Vision helper
│   ├── iot_publisher.py        # Azure IoT Hub MQTT publisher
│   └── requirements.txt        # Python dependencies
│
├── azure/
│   ├── iot_hub_config.json     # IoT Hub device config
│   └── message_schema.json     # C2D message format
│
├── circuit/
│   └── esp32_circuit.png       # Tinkercad circuit diagram
│
├── docs/
│   └── architecture.png        # System architecture diagram
│
└── README.md
```

---

## ▶️ How to Run the Project

### Full System Startup Sequence

```
1. Power on the jacket (battery or USB)
2. ESP32 boots → connects to Wi-Fi → subscribes to MQTT topic
3. SSH into Raspberry Pi:
      ssh pi@<raspberrypi-ip>
      cd IRIS-Jacket/raspberry_pi
      python3 camera_pipeline.py
4. Walk with the jacket — ultrasonic sensors activate instantly
5. Camera pipeline runs in parallel, cloud risk analysis every ~1s
6. Vibration feedback is continuous and real-time
```

### Test Ultrasonic Only (No Cloud)

```cpp
// In main.ino, comment out:
// connectToAzure();
// listenMQTT();
// Ultrasonic + vibration will still work standalone
```

---

## 🛠️ Troubleshooting

| Problem | Likely Cause | Fix |
|---------|--------------|-----|
| No vibration at all | Motor wiring / transistor | Check NPN base resistor and GND |
| Wrong direction vibrating | GPIO pin mismatch | Verify pin mapping in `config.h` |
| ESP32 not connecting to Wi-Fi | Wrong credentials | Double-check SSID/password |
| Azure Vision returns 401 | Invalid API key | Regenerate key in Azure portal |
| MQTT not receiving messages | SAS token expired | Regenerate device SAS token |
| Camera not capturing | Pi Camera not enabled | Run `sudo raspi-config` → Interface → Camera |
| Ultrasonic always 0 cm | 5V→3.3V not handled | Add voltage divider on ECHO pin |

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).


> *"Technology should empower everyone — IRIS Jacket is a step toward a more inclusive world."*
