#include <FastLED.h>

#define PIEZO_SENSOR_RIGHT_PIN A6
#define LED_STRIP_RIGHT_PIN 6

#define PIEZO_SENSOR_LEFT_PIN A2
#define LED_STRIP_LEFT_PIN 2

#define NUM_LEDS_RIGHT 60
#define NUM_LEDS_LEFT 60

#define PIEZO_THRESHOLD 600

#define BRIGHTNESS 150

CRGB ledRight[NUM_LEDS_RIGHT];
CRGB ledLeft[NUM_LEDS_LEFT];

int piezoValueRight = 0;
int piezoValueLeft = 0;

void setup() {

  FastLED.addLeds<WS2812, LED_STRIP_RIGHT_PIN, GRB>(ledRight, NUM_LEDS_RIGHT);
  FastLED.addLeds<WS2812, LED_STRIP_LEFT_PIN, GRB>(ledLeft, NUM_LEDS_LEFT);

  FastLED.setBrightness(BRIGHTNESS);

  if (!initLED()) {
    Error();
  }
}

void loop() {

  piezoValueRight = analogRead(PIEZO_SENSOR_RIGHT_PIN);
  piezoValueLeft = analogRead(PIEZO_SENSOR_LEFT_PIN);

  if (piezoValueRight > PIEZO_THRESHOLD) {

    toggleLED(20, NUM_LEDS_RIGHT, ledRight);
  }
  if (piezoValueLeft > PIEZO_THRESHOLD) {

    toggleLED(20, NUM_LEDS_LEFT, ledLeft);
  }
}

void toggleLED(int delay_ms, int len, CRGB led[]) {

  for (int i = 0; i < len; i++) {
    led[i] = CRGB::Green;
  }
  FastLED.show();

  delay(delay_ms);

  for (int i = 0; i < len; i++) {
    led[i] = CRGB::Black;
  }
  FastLED.show();
}


bool initLED() {

  for (int j = 0; j < 5; j++) {
    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Green;
    }

    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Blue;
    }
    FastLED.show();
    delay(50);

    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Black;
    }

    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Black;
    }
    delay(50);
  }

  return true;
}

void Error() {
  while (true) {

    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Red;
    }
    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Black;
    }

    FastLED.show();
    delay(250);

    for (int i = 0; i < NUM_LEDS_LEFT; i++) {
      ledLeft[i] = CRGB::Black;
    }
    for (int i = 0; i < NUM_LEDS_RIGHT; i++) {
      ledRight[i] = CRGB::Red;
    }

    delay(250);
  }
}
