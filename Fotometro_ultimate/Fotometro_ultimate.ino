#include <Arduino.h>

const int photoDiodePin = A0;

float I = 0;

void setup() {
              Serial.begin(9600);
              }

void loop() {
            if (Serial.available()) {
                                      String comando = Serial.readStringUntil('\n');
                                      comando.trim();
                                                      if (comando.startsWith("medir")) {
                                                                                        float I = (analogRead(photoDiodePin) / 1023.0) * 5000;                                                                           
                                                                                        delay(100);                                                                                                       
                                                                                        Serial.println(I, 2);
                                                                                        } 
                                     }
              }
