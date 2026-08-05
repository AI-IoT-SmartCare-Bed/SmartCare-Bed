const int sensorPin = 17; //D8
int sensorState = 0;

void setup() {
  Serial.begin(115200); // ESP32의 기본 시리얼 통신 속도
  pinMode(sensorPin, INPUT);
}

void loop() {
  sensorState = digitalRead(sensorPin);

    Serial.println(sensorState);
    
    delay(500); 
}