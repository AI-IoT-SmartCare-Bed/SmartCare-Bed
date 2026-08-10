#include <ESP32Servo.h>

const int ledPin = 5;      
const int speakerPin = 22; 
const int servoPin = 19;   

Servo myServo; 

void setupActuators() {
  pinMode(ledPin, OUTPUT);
  pinMode(speakerPin, OUTPUT);
  
  myServo.attach(servoPin);
  myServo.write(0); 
}

void controlActuator(String message) {
  if (message == "1") {
    digitalWrite(ledPin, HIGH);     
    tone(speakerPin, 1000);         
    myServo.write(60);              
    Serial.println("-> [동작] LED 켜짐, 스피커 울림, 서보모터 60도");
  } 
  else if (message == "0") {
    digitalWrite(ledPin, LOW);      
    noTone(speakerPin);             
    myServo.write(0);               
    Serial.println("-> [동작] 모두 정지, 서보모터 0도");
  }
}