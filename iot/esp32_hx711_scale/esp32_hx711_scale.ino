/*
 * WasteDash / GCC Smart Waste Platform
 * Firmware: ESP32 Load Cell / Weighbridge Scale Interface
 * Hardware: ESP32 Dev Board + HX711 24-bit ADC + 50kg/100kg Load Cell
 * Protocol: MQTT over TLS (Port 8883) or Non-TLS (Port 1883)
 * Status: Starter Firmware Template (Modular Arduino / C++)
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "HX711.h"

// ================= USER CONFIGURATION =================
const char* WIFI_SSID       = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";

const char* MQTT_BROKER     = "broker.wastedash.chennaiswm.gov.in";
const int   MQTT_PORT       = 8883;
const char* MQTT_USER       = "scale_user";
const char* MQTT_PASS       = "scale_password";

const char* DEVICE_ID       = "SCALE-PLANT-PERUNGUDI-01";
const char* MQTT_TOPIC      = "wastedash/devices/SCALE-PLANT-PERUNGUDI-01/telemetry";

// HX711 Pins
const int LOADCELL_DOUT_PIN = 19;
const int LOADCELL_SCK_PIN  = 18;
const float CALIBRATION_FACTOR = -7050.0; // Tune according to known weight calibration

const unsigned long REPORT_INTERVAL_MS = 20000; // 20 seconds

// ================= GLOBALS =================
HX711 scale;
WiFiClientSecure espClient;
PubSubClient client(espClient);
unsigned long lastMsgTime = 0;

void setupWifi() {
  delay(10);
  Serial.printf("[WiFi] Connecting to %s...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
}

void reconnectMqtt() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting... ");
    String clientId = "ESP32-Scale-" + String(DEVICE_ID);
    espClient.setInsecure(); // Template fallback

    if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println("CONNECTED!");
    } else {
      Serial.printf("FAILED (rc=%d). Retrying in 5s...\n", client.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(CALIBRATION_FACTOR);
  scale.tare(); // Zero the scale on startup

  setupWifi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  Serial.println("[Scale Interface] Initialized and tared.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setupWifi();
  }
  if (!client.connected()) {
    reconnectMqtt();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsgTime > REPORT_INTERVAL_MS) {
    lastMsgTime = now;

    float weight_kg = 0.0;
    if (scale.is_ready()) {
      weight_kg = scale.get_units(5); // Average of 5 readings
      if (weight_kg < 0.0) weight_kg = 0.0;
    }

    StaticJsonDocument<256> doc;
    doc["message_id"]    = "SCL-" + String(DEVICE_ID) + "-" + String(now);
    doc["device_id"]     = DEVICE_ID;
    doc["device_type"]   = "plant_sensor";
    doc["weight_kg"]     = round(weight_kg * 100.0) / 100.0;
    doc["sensor_status"] = scale.is_ready() ? "NORMAL" : "SENSOR_ERROR";
    doc["battery_pct"]   = 100.0; // AC Mains Powered
    doc["is_simulated"]  = false;

    char buffer[256];
    serializeJson(doc, buffer);

    Serial.printf("[MQTT Publish] %s -> %s\n", MQTT_TOPIC, buffer);
    client.publish(MQTT_TOPIC, buffer);
  }
}
