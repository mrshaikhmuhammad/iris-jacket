#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESPmDNS.h>

class Ultrasonic
{
private:
    int triggerPin;
    int echoPin;

    void trigger()
    {
        // Reset Pin
        digitalWrite(triggerPin, LOW);
        delayMicroseconds(2);
        // Trigger Pin
        digitalWrite(triggerPin, HIGH);
        delayMicroseconds(10);
        digitalWrite(triggerPin, LOW);
    }

    float getDistanceOnce()
    {
        trigger();

        long duration = pulseInLong(echoPin, HIGH, 25000);
        if (duration == 0)
        {
            return 2;
        }
        else
        {
            float distance = duration / 5830.0;
            if (distance < 4 && distance > 0)
            {
                return distance;
            }
            else
            {
                return -1;
            }
        }
    }

public:
    Ultrasonic(int tPin, int ePin) : triggerPin(tPin), echoPin(ePin)
    {
    }

    void begin()
    {
        pinMode(triggerPin, OUTPUT);
        pinMode(echoPin, INPUT);
    }

    float getDistanceAverage(int averageOf)
    {
        float total = 0, individual = 0;

        for (int i = 0; i < averageOf; i++)
        {
            individual = getDistanceOnce();
            if (individual > 0)
            {
                total += individual;
            }
            delay(25);
        }
        return total / averageOf;
    }
};
class Vibration
{
private:
    bool powerOff;
    int pin, angle;
    void pushStart()
    {
        ledcWrite(channel, 255);
        delay(50);

        powerOff = false;
    }

public:
    float channel;
    Vibration(int motorPin, int motorAngle, int motorChannel) : pin(motorPin), angle(motorAngle), channel(motorChannel)
    {
    }

    void begin()
    {
        pinMode(pin, OUTPUT);
        ledcSetup(channel, 5000, 8);
        ledcAttachPin(pin, channel);
        powerOff = true;
    }

    void vibrate(float pwm)
    {
        if (pwm <= 0)
        {
            powerOff = true;
            ledcWrite(channel, 0);
        }
        else if (powerOff)
        {
            pushStart();
            ledcWrite(channel, (int)pwm);
        }
        else
        {
            ledcWrite(channel, (int)pwm);
        }
    }

    void vibrate(float center, float side)
    {
        double numerator = 255 * side * center;
        double denominator = (center * center * cos(angle) * cos(angle)) + (side * side * sin(angle) * sin(angle));
        denominator = sqrt(denominator);

        if (denominator == 0)
        {
            vibrate(255.0);
        }
        else
        {
            double result = 255 - (numerator / denominator);
            vibrate(result);
        }
    }
};

Ultrasonic sensors[3] = {
    Ultrasonic(5, 18), // leftSensor (trigger, echo)
    Ultrasonic(15, 2), // centerSensor (trigger, echo)
    Ultrasonic(13, 12) // rightSensor (trigger, echo)
};

Vibration motors[7] = {
    Vibration(19, PI, 0),    // leftMotor (pin, angle, channel)
    Vibration(4, PI / 2, 1), // centerMotor
    Vibration(14, 0, 2),     // rightMotor

    Vibration(33, 0, 3), // leftCameraMotor (pin, ____, channel) ---> angle does not matter here
    Vibration(25, 0, 4), // centerCameraMotor
    Vibration(26, 0, 5), // rightCameraMotor
    Vibration(17, 0, 6)  // urgentCameraMotor
};

float center, right, left;

const char *WIFI_SSID = "uno";
const char *WIFI_PASSWORD = "uno12345";
const int UDP_PORT = 4210;
const char *MDNS_HOSTNAME = "esp32";
char packetBuffer[256];
WiFiUDP udp;

void connectWiFi()
{
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("\n✓ WiFi connected!");
        Serial.print("  IP Address: ");
        Serial.println(WiFi.localIP());

        // Start mDNS
        if (MDNS.begin(MDNS_HOSTNAME))
        {
            Serial.print("✓ mDNS started: ");
            Serial.print(MDNS_HOSTNAME);
            Serial.println(".local");

            // Advertise UDP service
            MDNS.addService("iris", "udp", UDP_PORT);
        }
        else
        {
            Serial.println("✗ mDNS failed to start");
        }
    }
    else
    {
        Serial.println("\n✗ WiFi connection failed!");
        Serial.println("  Check SSID and password");
    }
}

void processCommand(String cmd)
{
    Serial.print("Received: ");
    Serial.println(cmd);

    if (cmd == "STOP")
    {
        for (int i = 0; i < 7; i++)
        {
            motors[i].vibrate(0);
        }
        Serial.println("  → All motors stopped");
        return;
    }

    else if (cmd.startsWith("V,"))
    {
        // Parse: V,motor_index,intensity,duration
        int firstComma = cmd.indexOf(',');
        int secondComma = cmd.indexOf(',', firstComma + 1);
        int thirdComma = cmd.indexOf(',', secondComma + 1);

        if (firstComma > 0 && secondComma > 0 && thirdComma > 0)
        {
            int motorIndex = cmd.substring(firstComma + 1, secondComma).toInt();
            int intensity = cmd.substring(secondComma + 1, thirdComma).toInt();
            int duration = cmd.substring(thirdComma + 1).toInt();

            if (motorIndex >= 0 && motorIndex < 7)
            {
                Serial.print("  → Motor ");
                Serial.print(motorIndex);
                Serial.print(" ON (intensity: ");
                Serial.print(intensity);
                Serial.print(", duration: ");
                Serial.print(duration);
                Serial.println("ms)");

                motors[motorIndex].vibrate(intensity);
                delay(duration);
                motors[motorIndex].vibrate(0);
            }
        }
        else
        {
            Serial.println("  ✗ Invalid V command format");
        }
    }
}

void setup()
{
    Serial.begin(9600);

    for (int i = 0; i < 3; i++)
    {
        sensors[i].begin();
    }
    for (int i = 0; i < 7; i++)
    {
        motors[i].begin();
    }

    connectWiFi();
    if (WiFi.status() == WL_CONNECTED)
    {
        udp.begin(UDP_PORT);
        Serial.print("✓ UDP listening on port ");
        Serial.println(UDP_PORT);
    }
}

void loop()
{
    left = sensors[0].getDistanceAverage(5);
    center = sensors[1].getDistanceAverage(5);
    right = sensors[2].getDistanceAverage(5);

    // Serial.print("Distance: ");
    // Serial.print(left);
    // Serial.print(" ");
    // Serial.print(center);
    // Serial.print(" ");
    // Serial.println(right);

    motors[0].vibrate(center, left);
    motors[1].vibrate(center, (left + right) / 2.0);
    motors[2].vibrate(center, right);

    if (WiFi.status() == WL_CONNECTED)
    {
        int packetSize = udp.parsePacket();
        if (packetSize)
        {
            int len = udp.read(packetBuffer, 256);
            if (len > 0)
            {
                packetBuffer[len] = '\0'; // Null terminate
                String command = String(packetBuffer);
                command.trim();
                processCommand(command);
            }
        }
    }
    else
    {
        connectWiFi();
        if (WiFi.status() == WL_CONNECTED)
        {
            udp.begin(UDP_PORT);
            Serial.print("✓ UDP listening on port ");
            Serial.println(UDP_PORT);
        }
    }
}
