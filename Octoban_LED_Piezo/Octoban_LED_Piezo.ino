#include <FastLED.h>

#define PIEZO_SENSOR_RIGHT_PIN A6
#define LED_STRIP_RIGHT_PIN 6

#define PIEZO_SENSOR_LEFT_PIN A4
#define LED_STRIP_LEFT_PIN 8

#define NUM_LEDS_RIGHT 60
#define NUM_LEDS_LEFT 60

#define PIEZO_THRESHOLD 600


CRGB ledRight[NUM_LEDS_RIGHT];
CRGB ledLeft[NUM_LEDS_LEFT];

int piezoValueRight = 0;
int piezoValueLeft = 0;

void setup() {

  FastLED.addLeds<WS2812, LED_STRIP_RIGHT_PIN, GRB>(ledRight, NUM_LEDS_RIGHT);
  FastLED.addLeds<WS2812, LED_STRIP_LEFT_PIN, GRB>(ledLeft, NUM_LEDS_LEFT);

  FastLED.setBrightness(150);


  if(!initLED()){
    return;
  }
}

void loop() {

  piezoValueRight = analogRead(PIEZO_SENSOR_RIGHT_PIN);
  piezoValueLeft = analogRead(PIEZO_SENSOR_LEFT_PIN);

  if (piezoValueRight > PIEZO_THRESHOLD) {

    toggleLED(20, NUM_LEDS_RIGHT, ledRight);

    Serial.println("Right!");
    Serial.println(piezoValueRight, DEC);
  }
  if (piezoValueLeft > PIEZO_THRESHOLD) {

    toggleLED(20, NUM_LEDS_LEFT, ledLeft);

    Serial.println("Left!");
    Serial.println(piezoValueLeft, DEC);
  }
}

void toggleLED(int delay_ms, int len, CRGB led[]) {

  for (int i = 0; i < len; i++) {
    ledLeft[i] = CRGB::Green;
  }
  FastLED.show();
  

  delay(delay_ms);

  for (int i = 0; i < len; i++) {
    ledLeft[i] = CRGB::Black;
  }
  FastLED.show();

}


bool initLED() {

  for (int j = 0; j < 5; j++) {
    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Green;
    }

    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Green;
    }
    FastLED.show();
    delay(10);

    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Black;
    }

    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Black;
    }
    delay(10);
  }
  return true;
}
