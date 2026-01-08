#include <math.h>

float height, left, right; 

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
			return 0;
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
			else
			{
				averageOf++;
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
	int pin;
  	float angle;
	void pushStart()
	{
		ledcWrite(channel, 255);
		delay(50);

		powerOff = false;
	}

public:
	float channel;
	Vibration(int motorPin, int motorAngle) : pin(motorPin), angle(motorAngle)
	{
        ledcSetup(channel, 5000, 8);
	}

	void begin(){
		pinMode(pin, OUTPUT);
        ledcAttachPin(pin, channel);
		powerOff = true;
	}

	void vibrate(float pwm)
	{	
      	if (pwm <= 0)
		{
			powerOff = true;
			digitalWrite(pin, LOW);
		}
		else if (powerOff)
		{
          	Serial.print("PWM: ");
     		Serial.println(pwm);	
			pushStart();
			ledcWrite(channel, int(pwm));
		}
		else
		{
          	Serial.print("PWM: ");
     		Serial.println(pwm);
			ledcWrite(channel, int(pwm));
		}	
	}

	void vibrate(float center, float side)
	{
		double numerator = 127.5 * side * center;
		double denominator = (center * center * cos(angle)*cos(angle)) + (side * side * sin(angle)*sin(angle));
		denominator = sqrt(denominator);

		if(denominator == 0){
			vibrate(255.0);

		}else{
			double result = 255 - (numerator/denominator);
			vibrate(result);
		}		
	}
};

Ultrasonic leftSensor(3,2);
Ultrasonic centerSensor(5,4);
Ultrasonic rightSensor(9,8);
Vibration leftMotor(6,PI);
Vibration centerMotor(10,PI/2);
Vibration rightMotor(11,0);


void setup(){
	Serial.begin(9600);
  	leftSensor.begin();
  	centerSensor.begin();
  	rightSensor.begin();
  
  	leftMotor.begin();
  	centerMotor.begin();
  	rightMotor.begin();
  
}

void loop(){
  	left = leftSensor.getDistanceAverage(5);
  	height = centerSensor.getDistanceAverage(5);
  	right = rightSensor.getDistanceAverage(5);
  
  	Serial.print("Distance: ");
  	Serial.print(left);
  	Serial.print(" ");
  	Serial.print(height);
  	Serial.print(" ");
  	Serial.println(right);
  	
  	leftMotor.vibrate(height, right);
  	centerMotor.vibrate(height, (right+left)/2);
  	rightMotor.vibrate(height, left);
  
  	delay(100);
}
