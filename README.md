<div align="center">

<img src="https://img.shields.io/badge/Platform-ESP32%20%2B%20Raspberry%20Pi-blue?style=for-the-badge&logo=espressif" />
<img src="https://img.shields.io/badge/Cloud-Microsoft%20Azure-0078D4?style=for-the-badge&logo=microsoftazure" />
<img src="https://img.shields.io/badge/AI-Computer%20Vision-green?style=for-the-badge&logo=opencv" />
<img src="https://img.shields.io/badge/Protocol-UDP%20%2B%20mDNS-orange?style=for-the-badge" />

<br/><br/>

```
 ██╗██████╗ ██╗███████╗
 ██║██╔══██╗██║██╔════╝
 ██║██████╔╝██║███████╗
 ██║██╔══██╗██║╚════██║
 ██║██║  ██║██║███████║
 ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
```
</div align="center">

# IRIS — Intelligent Real-time Indoor/outdoor Safety System

## The Problem We're Solving

Over **285 million people** worldwide live with visual impairment. Existing aids — white canes, guide dogs — are effective but limited: they can't detect obstacles at chest or head height, can't identify *what* an obstacle is, and provide no warning before physical contact.

**IRIS** changes that. It's a jacket that:
- **Feels** obstacles through vibration before the user reaches them
- **Sees** the environment through AI-powered camera analysis  
- **Scales** intensity — light buzz for far obstacles, urgent pulse for immediate danger

---

## Key Features

| Feature | Description |
|---|---|
| **Real-time Haptics** | 7 vibration motors give directional, proportional feedback |
| **3-Zone Ultrasonic** | Left, Center, Right sensors with 4-meter range |
| **Azure AI Vision** | Cloud-based scene understanding every 3 seconds |
| **Trigonometric Model** | Motor intensity computed via vector projection math |

---

## Architecture <a name="architecture"></a>

```
╔════════════════════════════════════════════════════════════════╗
║                        IRIS JACKET                             ║
║                                                                ║
║   ┌───────────────────────────────────────────────────────┐    ║
║   │                    ESP32                              │    ║
║   │                                                       │    ║
║   │  [HC-SR04 LEFT]──┐                                    │    ║
║   │  [HC-SR04 CENTER]┼──► Distance Readings               │    ║
║   │  [HC-SR04 RIGHT]─┘         │                          │    ║
║   │                            ▼                          │    ║
║   │               ┌─── Math Model ───┐                    │    ║
║   │               │  Vector          │                    │    ║
║   │               │  Projection      │                    │    ║
║   │               └──────┬───────────┘                    │    ║
║   │                      ▼                                │    ║
║   │         [7 × Vibration Motors via PWM]                │    ║
║   │                                                       │    ║
║   └───────────────────────▲───────────────────────────────┘    ║
║                           │ UDP Commands "V,idx,pwm,dur"       ║
║   ┌───────────────────────┴───────────────────────────────┐    ║
║   │                  Raspberry Pi                         │    ║
║   │                                                       │    ║
║   │   [Pi Camera] ──► capture_image() every 3s            │    ║
║   │                         |                             │    ║
║   │                         |                             │    ║
║   │                         │                             │    ║
║   └─────────────────────────┼─────────────────────────────┘    ║
╚═════════════════════════════╪══════════════════════════════════╝
                              │ HTTPS REST API
                              ▼
              ┌───────────────────────────────┐
              │       Microsoft Azure          │
              │                               │
              │  ┌─────────────────────────┐  │
              │  │  Computer Vision API    │  │
              │  │  • Object Detection     │  │
              │  │  • Scene Description    │  │
              │  └────────────┬────────────┘  │
              │               │               │
              │  ┌────────────▼────────────┐  │
              │  │   Risk Engine           │  │
              │  │  FAR / NEAR / CRITICAL  │  │
              │  └─────────────────────────┘  │
              └───────────────────────────────┘
                              │
                    UDP "V,5,255,500"
                              │
                    [URGENT Motor Buzzes]
```

---

## Hardware Components <a name="hardware"></a>

| # | Component | Qty | Role |
|---|---|---|---|
| 1 | **ESP32 Dev Board** | 1 | Main MCU — sensors, motors, Wi-Fi |
| 2 | **Raspberry Pi 4B / 3B+** | 1 | Edge compute — camera, cloud, speech |
| 3 | **HC-SR04 Ultrasonic Sensor** | 3 | Obstacle ranging: Left / Center / Right |
| 4 | **ERM Vibration Motor (3V)** | 7 | Haptic feedback zones |
| 5 | **NPN Transistor (2N2222)** | 7 | PWM motor switching |
| 6 | **1kΩ Resistor** | 7 | Transistor base current limiting |
| 7 | **1N4148 Fly-back Diode** | 7 | Back-EMF protection on motors |
| 8 | **Raspberry Pi Camera v2** | 1 | Scene capture for Azure AI |
| 9 | **Breadboard + Jumper Wires** | — | Prototyping |
| 10 | **Li-Po Battery / Power Bank** | 1 | Portable power |

---

## ⚡ Circuit & Pin Mapping

### Ultrasonic Sensors → ESP32

```
Sensor          TRIG Pin    ECHO Pin
─────────────────────────────────────
LEFT            GPIO 5      GPIO 18
CENTER          GPIO 15     GPIO 2
RIGHT           GPIO 13     GPIO 12
```

> ⚠️ HC-SR04 ECHO outputs **5V logic**. Always use a voltage divider
> (1kΩ + 2kΩ) on the ECHO line — ESP32 GPIO is only 3.3V tolerant.

### Vibration Motors → ESP32 (PWM via NPN Transistor)

```
Motor Zone       GPIO    PWM Channel   Angle (rad)
───────────────────────────────────────────────────
Left             GPIO 19     ch.0        π   (180°)
Center           GPIO 4      ch.1        π/2  (90°)
Right            GPIO 14     ch.2        0°   ( 0°)
AI Left          GPIO 33     ch.3        —
AI Right         GPIO 25     ch.4        —
AI Center/Urgent GPIO 26     ch.5        —
Urgent Alert     GPIO 17     ch.6        —
```

### Transistor Wiring (per motor)

```
ESP32 GPIO ──[1kΩ]───► NPN Base
                       Collector ──► Motor (–)
                       Motor (+) ──► 3.3V / 5V
                       Emitter  ───► GND
                       [1N4148 diode across motor, cathode to VCC]
```

---

## Mathematical Model — Directional Vibration <a name="math-model"></a>

This is the core innovation. Rather than simply turning motors on/off, IRIS uses **trigonometric vector projection** to compute *exactly* how much each motor should vibrate based on two distance inputs.

### The Formula

Each motor has a fixed angular orientation `θ` in the jacket's coordinate plane:

```
Left Motor   → θ = π     (180° — faces left)
Center Motor → θ = π/2   (90°  — faces forward)
Right Motor  → θ = 0     (0°   — faces right)
```

Given `center` distance and `side` distance (in meters), the PWM intensity for a motor at angle θ is:

```
                    255 × side × center
PWM = 255 - ────────────────────────────────────────────────
             √( center² · cos²θ  +  side² · sin²θ )
```

### Intuition

Think of it as an **ellipse** defined by the two distances. The motor's angle determines where on the ellipse we sample — giving it a natural directional sensitivity:

```
            FAR (low buzz)
               ↑
    ┌──────────┼──────────┐
    │         (C)         │  C = center distance
    │                     │
◄──(L)─────── · ─────────►  θ determines
    │                     │  which dimension
    └──────────┼──────────┘  dominates
               ↓
            VERY CLOSE (max buzz)
```

### Worked Examples

| Left dist | Center dist | Left Motor PWM | Center Motor PWM | Right Motor PWM |
|---|---|---|---|---|
| 3.0m | 3.0m | ~127 (mild) | ~127 (mild) | ~127 (mild) |
| 0.3m | 3.0m | **~245 (strong)** | ~145 (moderate) | ~10 (barely) |
| 3.0m | 0.3m | ~145 (moderate) | **~245 (strong)** | ~145 (moderate) |
| 0.2m | 0.2m | **255 (maximum)** | **255 (maximum)** | **255 (maximum)** |

### Kick-Start Mechanism

ERM vibration motors have **static friction** — they need more torque to start than to keep spinning. IRIS handles this automatically:

```
Motor was OFF + new PWM signal received?
    → Blast full 255 PWM for 50ms   (overcome static friction)
    → Then settle to target PWM     (proportional intensity)
```

This prevents the "motor that hums but doesn't spin" bug seen in many haptic projects.

---

## Azure AI Vision Pipeline

Every 3 seconds, the Raspberry Pi runs this pipeline:

### Step 1 — Capture
```python
camera.capture_file(f"capture_{timestamp}.jpg")   # 1280×720 JPEG
```

### Step 2 — Dual Azure API Call
```python
# Scene description
azure_client.describe_image_in_stream(img)
# → "a person standing near a flight of stairs"

# Object detection + face counting
azure_client.analyze_image_in_stream(img,
    features=[objects, faces])
# → bounding boxes with confidence scores
```
Objects below **50% confidence** are discarded to reduce false positives.

### Step 3 — Position Classification

The 1280px-wide frame is divided into 3 horizontal zones:

```
 ┌──────────────┬──────────────┬──────────────┐
 │              │              │              │
 │     LEFT     │    CENTER    │    RIGHT     │
 │   0 – 426px  │ 426 – 853px  │ 853 – 1280px │
 │              │              │              │
 └──────────────┴──────────────┴──────────────┘
   Motor 3 buzz    Motor 1 buzz    Motor 4 buzz
```

```python
center_x = rect.x + (rect.w / 2)   # bounding box center
zone = "LEFT" if center_x < 426 else "RIGHT" if center_x > 853 else "CENTER"
```

### Step 4 — Distance Classification

Object size in the frame estimates physical distance:

```python
area_ratio = (box_w × box_h) / (1280 × 720)

area_ratio > 0.25  →  VERY_CLOSE  →  PWM 255, 500ms + URGENT motor
area_ratio > 0.08  →  NEAR        →  PWM 200, 300ms
else               →  FAR         →  PWM 100, 200ms
```

### Step 5 — Urgency Check

```python
URGENT_OBSTACLES = ["car", "truck", "person", "stairs",
                    "hole", "wall", "pole", "dog", ...]

is_urgent = (name in URGENT_OBSTACLES) and (distance != "FAR")
# → triggers Motor 6 (URGENT) + interrupts current voice output
```

---

## Communication Protocol <a name="communication"></a>

### Device Discovery — mDNS

No hardcoded IPs. The Raspberry Pi finds the ESP32 automatically:

```python
ip = socket.gethostbyname("esp32.local")   # retries every 2s until found
```

The ESP32 advertises itself via **mDNS** as `esp32.local`, making the system plug-and-play on any network.

### UDP Command Format

```
"V,{motor_index},{intensity},{duration_ms}"

Examples:
  "V,3,255,500"   →  AI-Left motor, full power, 500ms
  "V,5,200,300"   →  Urgent motor, 200/255 power, 300ms
  "V,1,100,200"   →  Center motor, low power, 200ms
  "STOP"          →  All 7 motors off immediately
```

### Why UDP (not MQTT or HTTP)?

| Protocol | Latency | Overhead | Reliability |
|---|---|---|---|
| **UDP** ✅ | ~1ms | Zero | Fire-and-forget (fine for haptics) |
| MQTT | ~50ms | Medium | Guaranteed delivery |
| HTTP | ~100ms+ | High | Request/response overhead |

For haptic feedback, **speed beats reliability** — a missed vibration packet is imperceptible; a delayed one creates lag the user feels.

---

## 🚀 Setup & Installation <a name="setup"></a>

### Prerequisites

| Tool | Version |
|---|---|
| Arduino IDE | 2.x |
| Python | 3.8+ |
| ESP32 Board Package | Latest |
| Azure Subscription | Free tier works |

---

### ESP32 Firmware

**1. Install Arduino libraries:**
```
NewPing       →  Ultrasonic helper
WiFi          →  Built-in ESP32
ESPmDNS       →  Built-in ESP32
WiFiUdp       →  Built-in ESP32
```

**2. Add ESP32 board support:**
```
Arduino IDE → Preferences → Additional Board URLs:
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

**3. Update credentials in `main.ino`:**
```cpp
const char *WIFI_SSID     = "your_network";
const char *WIFI_PASSWORD = "your_password";
```

**4. Flash:**
```
Board: ESP32 Dev Module
Upload Speed: 115200
```

---

### Raspberry Pi Setup

**1. Install system dependencies:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install espeak python3-pip -y
```

**2. Install Python packages:**
```bash
pip3 install azure-cognitiveservices-vision-computervision \
             msrest picamera2 opencv-python
```

**3. Configure Azure keys in `vision.py`:**
```python
AZURE_ENDPOINT = "https://your-resource.cognitiveservices.azure.com/"
AZURE_KEY      = "your_api_key_here"
```

**4. Enable camera:**
```bash
sudo raspi-config → Interface Options → Camera → Enable
```

**5. Run:**
```bash
python3 vision.py
```

**6. Auto-start on boot:**
```bash
# Add to /etc/rc.local before exit 0
python3 /home/pi/IRIS-Jacket/vision.py &
```

---

### Azure Setup

```bash
# Create resource group
az group create --name IRIS --location eastus

# Create Computer Vision resource
az cognitiveservices account create \
  --name iris-vision \
  --resource-group IRIS \
  --kind ComputerVision \
  --sku S1 \
  --location eastus

# Get your key
az cognitiveservices account keys list \
  --name iris-vision \
  --resource-group IRIS
```

---

## 📁 Project Structure

```
IRIS-Jacket/
│
├── 📄 main.ino                  # ESP32 firmware (Arduino C++)
│   ├── class Ultrasonic          # HC-SR04 sensor abstraction
│   ├── class Vibration           # PWM motor + math model
│   ├── connectWiFi()             # mDNS + UDP setup
│   └── processCommand()          # UDP command parser
│
├── 📄 vision.py                 # Raspberry Pi main script (Python)
│   ├── init_*()                  # System initialization
│   ├── capture_image()           # Pi Camera capture
│   ├── analyze_image()           # Azure Vision API
│   ├── process_object()          # Position + distance logic
│   ├── send_haptic_feedback()    # UDP → ESP32
│   └── main_loop()               # 3-second cycle
│
├── 📷 circuit/
│   └── esp32_circuit.png         # Tinkercad wiring diagram
│
└── 📖 README.md
```

---

## 🔁 Complete System Flow

```
┌────────────────────────────────────────────────────────────┐
│  Every loop iteration (~375ms):                            │
│                                                            │
│  ESP32:                                                    │
│  sensors → getDistanceAverage(5) → math model → PWM motors │
│                                                            │
│  Every 3 seconds (parallel):                               │
│                                                            │
│  Pi Camera                                                 │
│     ↓ JPEG 1280×720                                        │
│  Azure Vision API                                          │
│     ↓ objects[] + faces[] + description                    │
│  process_object()                                          │
│     ↓ position (L/C/R) + distance (FAR/NEAR/CLOSE)         │
│     ├──► send_haptic_feedback()  ──► UDP ──► ESP32 motors  │
│     └──► generate_voice_output() ──► espeak TTS            │
└────────────────────────────────────────────────────────────┘
```

---

## 📄 License

```
MIT License — Free to use, modify, and distribute with attribution.
```
