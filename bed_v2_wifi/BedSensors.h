const int fsrPin = 4;
const int sensorPin = 17;

int fsrValue = 0;
int digitalState = 0;

void setupBedSensors() {
  analogReadResolution(12);
  pinMode(sensorPin, INPUT);
}

void updateBedSensors() {
  fsrValue = analogRead(fsrPin);
  digitalState = digitalRead(sensorPin);
}