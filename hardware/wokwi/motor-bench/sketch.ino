// Pukankov: Arduino Mega actuator wiring check.
// Simulation bench only: no dispensing logic or network integration.
#include <Servo.h>

const byte MOTOR_COUNT = 4;
const byte SERVO_PINS[MOTOR_COUNT] = {2, 3, 4, 5};
const byte STEP_PINS[MOTOR_COUNT] = {22, 24, 26, 28};
const byte DIR_PINS[MOTOR_COUNT] = {23, 25, 27, 29};
const byte ENABLE_PINS[MOTOR_COUNT] = {30, 31, 32, 33};
const unsigned int STEPS_PER_REVOLUTION = 200;
const unsigned int STEP_HIGH_US = 5;
const unsigned int STEP_LOW_US = 4995;

Servo servos[MOTOR_COUNT];

void rotateStepper(byte index, bool clockwise) {
  digitalWrite(DIR_PINS[index], clockwise ? HIGH : LOW);
  digitalWrite(ENABLE_PINS[index], LOW);  // A4988 enable is active LOW.
  delay(5);

  for (unsigned int step = 0; step < STEPS_PER_REVOLUTION; step++) {
    digitalWrite(STEP_PINS[index], HIGH);
    delayMicroseconds(STEP_HIGH_US);
    digitalWrite(STEP_PINS[index], LOW);
    delayMicroseconds(STEP_LOW_US);
  }

  digitalWrite(ENABLE_PINS[index], HIGH);
}

void setup() {
  Serial.begin(115200);

  for (byte i = 0; i < MOTOR_COUNT; i++) {
    // Set the output latch before OUTPUT to keep each driver disabled at setup.
    digitalWrite(ENABLE_PINS[i], HIGH);
    pinMode(ENABLE_PINS[i], OUTPUT);
    digitalWrite(STEP_PINS[i], LOW);
    pinMode(STEP_PINS[i], OUTPUT);
    digitalWrite(DIR_PINS[i], LOW);
    pinMode(DIR_PINS[i], OUTPUT);

    servos[i].write(90);
    servos[i].attach(SERVO_PINS[i]);
  }

  Serial.println(F("PUKANKOV MOTOR BENCH READY"));
  Serial.println(F("4 servos + 4 A4988 drivers; full-step mode."));
  delay(1000);
}

void loop() {
  for (byte i = 0; i < MOTOR_COUNT; i++) {
    Serial.print(F("Servo "));
    Serial.print(i + 1);
    Serial.println(F(": 0 -> 180 -> 90 degrees"));
    servos[i].write(0);
    delay(700);
    servos[i].write(180);
    delay(1000);
    servos[i].write(90);
    delay(700);
  }

  for (byte i = 0; i < MOTOR_COUNT; i++) {
    Serial.print(F("Stepper "));
    Serial.print(i + 1);
    Serial.println(F(": 200 steps clockwise"));
    rotateStepper(i, true);
    delay(500);
    Serial.println(F("200 steps counterclockwise"));
    rotateStepper(i, false);
    delay(500);
  }

  Serial.println(F("CYCLE COMPLETE"));
  delay(2000);
}
