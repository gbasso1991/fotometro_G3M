#include <Arduino.h>

const int photoDiodePin = A0;

float I0 = 0;
float I = 0;

void setup() {
  Serial.begin(9600);

}

void loop() {
  if (Serial.available()) {
                            String comando = Serial.readStringUntil('\n');
                            comando.trim();

                                         if (comando.startsWith("calibrar")) {
                                                                              float suma = 0;
  
                                                                              for (int i = 0; i < 10; i++) {
                                                                                                            float mV = (analogRead(photoDiodePin) / 1023.0) * 5000;
                                                                                                            suma += mV;
                                                                                                            Serial.println("Procesando...");
                                                                                                            Serial.flush();
                                                                                                            delay(1000);
                                                                                                          }
     
                                                                              I0 = suma / 10;
                                                                              Serial.println(I0, 2);
                                                                              } 

                                          else if (comando.startsWith("medir")) {
                                                                                
                                                                                float suma = 0;
   
                                                                                for (int i = 0; i < 10; i++) {
                                                                                                              float mV = (analogRead(photoDiodePin) / 1023.0) * 5000;
                                                                                                              suma += mV;
                                                                                                              delay(1000);
                                                                                                              }
   
                                                                                I = suma / 10;
                                                                                
                                                                                Serial.print(I, 2);                                                                              
                                                                                
                                                                                  }

  }
}
