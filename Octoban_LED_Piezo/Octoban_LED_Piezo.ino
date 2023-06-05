#include <FastLED.h>

#define PIEZO_SENSOR_RIGHT_PIN A6
#define PIEZO_SENSOR_LEFT_PIN A4
#define LED_SINGLE_PIN 3
#define LED_STRIP_RIGHT_PIN 6
#define LED_STRIP_LEFT_PIN 8
#define PIEZO_THRESHOLD 600
#define NUM_LEDS 60

CRGB ledRight[NUM_LEDS];
CRGB ledLeft[NUM_LEDS];

int piezoValueRight = 0;
int piezoValueLeft = 0;

void setup() {

  Serial.begin(9600);
  pinMode(LED_SINGLE_PIN, OUTPUT);

  FastLED.addLeds<WS2812, LED_STRIP_RIGHT_PIN, GRB>(ledRight, NUM_LEDS);

  FastLED.addLeds<WS2812, LED_STRIP_LEFT_PIN, GRB>(ledLeft, NUM_LEDS);

  

  for (int i = 0; i < NUM_LEDS; i++) {
    ledRight[i] = CRGB::Black;
    ledLeft[i] = CRGB::Black;
  }
  FastLED.show();
}

void loop() {
  for(int j = 0; j<255;j++){
for (int i = 0; i < NUM_LEDS; i++) {
    ledRight[i] = CRGB::Green;
    ledLeft[i] = CRGB::Green;
  }

  FastLED.show();
  
    FastLED.setBrightness(j);
    delay(100);
  }


  piezoValueRight = analogRead(PIEZO_SENSOR_RIGHT_PIN);
  piezoValueLeft = analogRead(PIEZO_SENSOR_LEFT_PIN);

  if (piezoValueRight > PIEZO_THRESHOLD) {

    toggleLEDRight(20);

    Serial.println("Right!");
    Serial.println(piezoValueRight, DEC);
  }
  if (piezoValueLeft > PIEZO_THRESHOLD){

    toggleLEDLeft(20);

    Serial.println("Left!");
    Serial.println(piezoValueLeft, DEC);
  }

}

void toggleLEDLeft(int delay_ms) {

  for (int i = 0; i < NUM_LEDS; i++) {
    ledLeft[i] = CRGB::White;
  }
  FastLED.show();
  digitalWrite(LED_SINGLE_PIN, HIGH);

  delay(delay_ms);

  for (int i = 0; i < NUM_LEDS; i++) {
    ledLeft[i] = CRGB::Black;
  }
  FastLED.show();
  digitalWrite(LED_SINGLE_PIN, LOW);
}

void toggleLEDRight(int delay_ms) {

  for (int i = 0; i < NUM_LEDS; i++) {
    ledRight[i] = CRGB::Green;
  }
  FastLED.show();
  digitalWrite(LED_SINGLE_PIN, HIGH);

  delay(delay_ms);

  for (int i = 0; i < NUM_LEDS; i++) {
    ledRight[i] = CRGB::Black;
  }
  FastLED.show();
  digitalWrite(LED_SINGLE_PIN, LOW);
}
