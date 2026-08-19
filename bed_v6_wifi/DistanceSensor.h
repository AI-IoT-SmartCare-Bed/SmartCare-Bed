const int trigPin = 13;
const int echoPin = 14;
#define SOUND_SPEED 0.034

float dist = 0;

void setupDistance() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void updateDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  dist = pulseIn(echoPin, HIGH) * SOUND_SPEED / 2;
}