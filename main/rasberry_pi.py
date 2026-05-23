#!/usr/bin/env python3
"""
IRIS - Intelligent Real-time Indoor/outdoor Safety System
Navigation assistance for deaf-blind persons
Raspberry Pi + Azure AI + ESP32 Vibration Feedback (UDP)
"""

import os
import sys
import time
import threading
import socket
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Azure imports
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

# ============================================
# "CONFIGURATION"
# ============================================

# Azure credentials
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY      = os.getenv("AZURE_KEY")

# ESP32 WiFi UDP settings (using mDNS hostname)
ESP32_HOSTNAME = "esp32.local"  # mDNS hostname - no need to know IP!

# Camera settings
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720
CAPTURE_FOLDER = "/home/iris/Desktop/Vision/captures"
MAX_IMAGES_TO_KEEP = 5

# Timing
CAPTURE_INTERVAL = 3

# Vibration motor mapping for AI commands
# Motors 0, 1, 2 are controlled by ultrasonic sensors on ESP32
# Motors 3, 4, 5 are controlled by AI/UDP commands from Pi
# Exception: AI also sends to motor 1 (CENTER) for center obstacles
MOTOR_MAP = {
    "AI_LEFT": 3,      # AI-detected obstacle on left
    "AI_RIGHT": 4,     # AI-detected obstacle on right
    "AI_CENTER": 1,    # AI-detected obstacle in center (shared with ultrasonic)
    "URGENT": 5        # Urgent/dangerous obstacle
}

# Urgent obstacles
URGET_OBSTACLES = [
    "car", "vehicle", "truck", "bus", "motorcycle", "bicycle", "bike",
    "person","animal", "dog", "stairs", "hole", "wall", "pole", "door", "tree"]

# ============================================
# GLOBAL OBJECTS
# ============================================

speech_lock = threading.Lock()
udp_socket = None
esp32_ip = None  # Will be resolved via mDNS
camera = None
azure_client = None
is_running = True
current_speech_process = None
ESP32_UDP_PORT = 4210   # UDP port for ESP32 communication

# ============================================
# INITIALIZATION
# ============================================

def find_esp32():
    """Loops forever until it finds the ESP32 via mDNS."""
    global esp32_ip
    print(f"🔍 Looking for {ESP32_HOSTNAME}...")
    while True:
        try:
            ip = socket.gethostbyname(ESP32_HOSTNAME)
            print(f"✅ Found ESP32 at: {ip}")
            esp32_ip = ip
            return ip
        except socket.gaierror:
            print("❌ ESP32 not found yet. Retrying in 2s...")
            time.sleep(2)


def init_azure():
    global azure_client
    try:
        credentials = CognitiveServicesCredentials(AZURE_KEY)
        azure_client = ComputerVisionClient(AZURE_ENDPOINT, credentials)
        print("✅ Azure AI connected")
        return True
    except Exception as e:
        print(f"❌ Azure connection failed: {e}")
        return False

def init_speech():
    """Check if espeak is available."""
    try:
        result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Speech engine (espeak) available")
            return True
        else:
            print("⚠️  espeak not found. Install with: sudo apt install espeak")
            return False
    except Exception as e:
        print(f"❌ Speech check failed: {e}")
        return False

def init_camera():
    global camera
    try:
        from picamera2 import Picamera2
        camera = Picamera2()
        config = camera.create_still_configuration(
            main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT), "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        time.sleep(1)
        print("✅ Camera initialized")
        return True
    except Exception as e:
        print(f"❌ Camera failed: {e}")
        return False


def init_udp():
    """Initialize UDP socket for ESP32 communication."""
    global udp_socket
    try:
        # First find ESP32 via mDNS
        find_esp32()
        
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"✅ UDP socket ready (Target: {esp32_ip}:{ESP32_UDP_PORT})")
        return True
    except Exception as e:
        print(f"⚠️  UDP socket failed: {e}")
        print("   (Continuing without haptic feedback)")
        return False


def init_folders():
    os.makedirs(CAPTURE_FOLDER, exist_ok=True)
    print(f"✅ Capture folder: {CAPTURE_FOLDER}")


# ============================================
# ESP32 UDP COMMUNICATION
# ============================================

def send_vibration(motor_index, intensity, duration_ms=200):
    """Send vibration command to ESP32 via UDP."""
    if udp_socket is None or esp32_ip is None:
        return
    try:
        command = f"V,{motor_index},{intensity},{duration_ms}"
        udp_socket.sendto(command.encode(), (esp32_ip, ESP32_UDP_PORT))
    except Exception as e:
        print(f"⚠️  UDP send failed: {e}")


def send_obstacle_vibration(position, distance):
    """Send vibration based on obstacle position and distance.
    
    AI motors only (ultrasonic handles real-time feedback):
    - Motor 3 (AI_LEFT): Objects detected on the left
    - Motor 4 (AI_RIGHT): Objects detected on the right
    - Motor 5 (URGENT): Dangerous objects that are close
    """
    # Determine intensity and duration based on distance
    if distance == "VERY_CLOSE":
        intensity = 255
        duration = 500
        # Always trigger URGENT motor for very close objects
        send_vibration(MOTOR_MAP["URGENT"], intensity, duration)
    elif distance == "NEAR":
        intensity = 200
        duration = 300
    else:
        intensity = 100
        duration = 200

    # Send to appropriate directional motor
    if position == "LEFT":
        send_vibration(MOTOR_MAP["AI_LEFT"], intensity, duration)
    elif position == "RIGHT":
        send_vibration(MOTOR_MAP["AI_RIGHT"], intensity, duration)
    else:
        # CENTER position - send to ultrasonic center motor
        send_vibration(MOTOR_MAP["AI_CENTER"], intensity, duration)


def stop_all_vibrations():
    """Stop all vibration motors."""
    if udp_socket is None or esp32_ip is None:
        return
    try:
        udp_socket.sendto(b"STOP", (esp32_ip, ESP32_UDP_PORT))
    except:
        pass


# ============================================
# SPEECH OUTPUT (using espeak)
# ============================================

def speak(text, urgent=False):
    """Speak text using espeak. If urgent, interrupts current speech."""
    global current_speech_process
    
    if not text:
        return
    
    print(f"🔊 {text}")
    
    with speech_lock:
        try:
            # Kill current speech if urgent
            if urgent and current_speech_process:
                current_speech_process.terminate()
                current_speech_process = None
            
            # Wait for current speech to finish (if not urgent)
            if current_speech_process:
                current_speech_process.wait()
            
            # Speak using espeak
            current_speech_process = subprocess.Popen(
                ['espeak', '-s', '160', text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            current_speech_process.wait()
            
        except Exception as e:
            print(f"⚠️  Speech error: {e}")


# ============================================
# IMAGE CAPTURE
# ============================================

def capture_image():
    """Capture image from camera."""
    if camera is None:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(CAPTURE_FOLDER, f"capture_{timestamp}.jpg")
    try:
        camera.capture_file(image_path)
        cleanup_old_images()
        return image_path
    except Exception as e:
        print(f"❌ Capture failed: {e}")
        return None


def cleanup_old_images():
    """Keep only the last MAX_IMAGES_TO_KEEP images."""
    try:
        files = sorted([
            f for f in os.listdir(CAPTURE_FOLDER)
            if f.startswith("capture_") and f.endswith(".jpg")
        ])
        while len(files) > MAX_IMAGES_TO_KEEP:
            os.remove(os.path.join(CAPTURE_FOLDER, files.pop(0)))
    except:
        pass


# ============================================
# IMAGE ANALYSIS
# ============================================

def analyze_image(image_path):
    """Analyze image with Azure AI."""
    if not os.path.exists(image_path):
        return None

    results = {
        "description": "",
        "obstacles": [],
        "people_count": 0,
        "urgent": False
    }

    try:
        with open(image_path, "rb") as image_stream:
            desc_result = azure_client.describe_image_in_stream(
                image_stream, max_candidates=1
            )
            if desc_result.captions:
                results["description"] = desc_result.captions[0].text

            image_stream.seek(0)

            features = [VisualFeatureTypes.objects, VisualFeatureTypes.faces]
            analysis = azure_client.analyze_image_in_stream(
                image_stream, visual_features=features
            )

            if analysis.objects:
                for obj in analysis.objects:
                    if obj.confidence < 0.5:
                        continue
                    obstacle = process_object(obj)
                    results["obstacles"].append(obstacle)
                    if obstacle["is_urgent"]:
                        results["urgent"] = True

            if analysis.faces:
                results["people_count"] = len(analysis.faces)

        return results

    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return None


def process_object(obj):
    """Process detected object and determine position/distance."""
    rect = obj.rectangle
    name = obj.object_property.lower()

    center_x = rect.x + (rect.w / 2) # finding the center point of the box
    if center_x < IMAGE_WIDTH * 0.33:
        position = "LEFT"
    elif center_x > IMAGE_WIDTH * 0.66:
        position = "RIGHT"
    else:
        position = "CENTER"

    area_ratio = (rect.w * rect.h) / (IMAGE_WIDTH * IMAGE_HEIGHT)
    if area_ratio > 0.25:
        distance = "VERY_CLOSE"
    elif area_ratio > 0.08:
        distance = "NEAR"
    else:
        distance = "FAR"

    is_urgent = name in URGENT_OBSTACLES and distance in ["VERY_CLOSE", "NEAR"]

    return {
        "name": name,
        "position": position,
        "distance": distance,
        "is_urgent": is_urgent,
        "confidence": obj.confidence
    }


# ============================================
# NAVIGATION OUTPUT
# ============================================

def generate_voice_output(results):
    """Generate concise voice output from analysis results."""
    if not results:
        return None, False

    messages = []
    is_urgent = results["urgent"]

    urgent_obstacles = [o for o in results["obstacles"] if o["is_urgent"]]
    if urgent_obstacles:
        for obs in urgent_obstacles[:2]:
            msg = f"Warning! {obs['name']} {obs['position'].lower()}"
            if obs["distance"] == "VERY_CLOSE":
                msg += ", very close!"
            messages.append(msg)

    near_obstacles = [o for o in results["obstacles"]
                      if not o["is_urgent"] and o["distance"] in ["NEAR", "VERY_CLOSE"]]
    if near_obstacles:
        for obs in near_obstacles[:2]:
            messages.append(f"{obs['name']} on {obs['position'].lower()}")

    if results["people_count"] > 0:
        if results["people_count"] == 1:
            messages.append("One person nearby")
        else:
            messages.append(f"{results['people_count']} people nearby")

    if not messages and results["description"]:
        desc = results["description"]
        if len(desc) > 50:
            desc = desc[:50].rsplit(' ', 1)[0]
        messages.append(desc)

    if not results["obstacles"]:
        messages.append("Path clear")

    return ". ".join(messages), is_urgent


def send_haptic_feedback(results):
    """Send vibration signals based on analysis results."""
    if not results or udp_socket is None:
        return
    for obs in results["obstacles"]:
        send_obstacle_vibration(obs["position"], obs["distance"])
        time.sleep(0.05)


# ============================================
# MAIN LOOP
# ============================================

def main_loop():
    """Main navigation loop - runs continuously."""
    global is_running

    print("\n" + "="*50)
    print("  👁️  IRIS NAVIGATION SYSTEM ACTIVE")
    print("="*50 + "\n")

    speak("Navigation system activated")

    while is_running:
        try:
            cycle_start = time.time()

            print(f"\n📷 [{datetime.now().strftime('%H:%M:%S')}] Capturing...")
            image_path = capture_image()

            if image_path:
                print("🔍 Analyzing...")
                results = analyze_image(image_path)

                if results:
                    desc_preview = results['description'][:60] if results['description'] else "No description"
                    print(f"   Scene: {desc_preview}...")
                    print(f"   Obstacles: {len(results['obstacles'])} | People: {results['people_count']} | Urgent: {results['urgent']}")

                    # Send haptic feedback (in background)
                    threading.Thread(
                        target=send_haptic_feedback,
                        args=(results,),
                        daemon=True
                    ).start()

                    # Generate and speak output
                    voice_text, is_urgent = generate_voice_output(results)
                    if voice_text:
                        speak(voice_text, urgent=is_urgent)

            # Wait for next cycle
            elapsed = time.time() - cycle_start
            sleep_time = max(0, CAPTURE_INTERVAL - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            is_running = False
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(1)

    shutdown()


def shutdown():
    """Clean shutdown of all systems."""
    global is_running
    is_running = False

    print("\n🛑 Shutting down...")
    speak("System shutting down")
    stop_all_vibrations()

    if camera:
        try:
            camera.stop()
        except:
            pass
        print("   Camera stopped")

    if udp_socket:
        try:
            udp_socket.close()
        except:
            pass
        print("   UDP socket closed")

    print("   Goodbye!\n")


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  👁️  IRIS - Navigation for Deaf-Blind")
    print("  🔧 Starting up...")
    print("="*50 + "\n")

    init_folders()

    if not init_azure():
        print("❌ Cannot start: Azure connection failed")
        sys.exit(1)

    if not init_camera():
        print("❌ Cannot start: Camera not available")
        sys.exit(1)

    init_speech()
    init_udp()

    print("\n✅ System ready!\n")

    try:
        main_loop()
    except KeyboardInterrupt:
        shutdown()
