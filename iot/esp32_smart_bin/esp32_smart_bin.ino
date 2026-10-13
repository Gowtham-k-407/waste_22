/*
 * WasteDash / GCC Smart Waste Platform
 * Firmware: ESP32 Smart Bin Ultrasonic Level Monitor
 * Hardware: ESP32 NodeMCU + HC-SR04 Ultrasonic Sensor + DHT22 (Optional)
 * Protocol: MQTT over TLS (Port 8883) or Non-TLS (Port 1883)
 * Status: Starter Firmware Template (Modular Arduino / C++)
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ================= USER CONFIGURATION (ENV TEMPLATE) =================
const char* WIFI_SSID       = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";

const char* MQTT_BROKER     = "broker.wastedash.chennaiswm.gov.in"; // or your cloud MQTT host
const int   MQTT_PORT       = 8883; // 8883 for TLS, 1883 for plaintext
const char* MQTT_USER       = "device_user";
const char* MQTT_PASS       = "device_password";

const char* DEVICE_ID       = "BIN-ZN08-W102"; // Unique Device ID
const char* MQTT_TOPIC      = "wastedash/devices/BIN-ZN08-W102/telemetry";

// Hardware Pins (HC-SR04 Ultrasonic)
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const float BIN_DEPTH_CM = 100.0; // Total physical height of the bin in cm

// Reporting interval (milliseconds)
const unsigned long REPORT_INTERVAL_MS = 30000; // 30 seconds

// ================= GLOBALS =================
WiFiClientSecure espClient; // or WiFiClient for non-TLS port 1883
PubSubClient client(espClient);
unsigned long lastMsgTime = 0;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout (~5m max)
  if (duration == 0) return -1.0; // Sensor timeout or out of range
  return (duration * 0.0343) / 2.0;
}

void setupWifi() {
  delay(10);
  Serial.printf("[WiFi] Connecting to %s...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Connection timeout. Retrying in loop.");
  }
}

void reconnectMqtt() {
  while (!client.connected()) {
    Serial.print("[MQTT] Attempting connection... ");
    String clientId = "ESP32-SmartBin-" + String(DEVICE_ID);
    
    // In production, configure CA Certificate with espClient.setCACert(root_ca);
    espClient.setInsecure(); // Template fallback: accepts broker TLS cert

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
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  setupWifi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
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

    float distance = readDistanceCm();
    float fillPct = 0.0;
    if (distance >= 0 && distance <= BIN_DEPTH_CM) {
      fillPct = ((BIN_DEPTH_CM - distance) / BIN_DEPTH_CM) * 100.0;
    } else if (distance > BIN_DEPTH_CM) {
      fillPct = 0.0;
    }

    // Build JSON Payload
    StaticJsonDocument<256> doc;
    doc["message_id"]    = "BIN-" + String(DEVICE_ID) + "-" + String(now);
    doc["device_id"]     = DEVICE_ID;
    doc["device_type"]   = "smart_bin";
    doc["distance_cm"]   = round(distance * 10.0) / 10.0;
    doc["bin_fill_pct"]  = round(fillPct * 10.0) / 10.0;
    doc["sensor_status"] = (fillPct >= 85.0) ? "NEAR_CAPACITY_ALERT" : "NORMAL";
    doc["battery_pct"]   = 94.0; // Read from ADC divider if wired
    doc["is_simulated"]  = false;

    char buffer[256];
    serializeJson(doc, buffer);

    Serial.printf("[MQTT Publish] Topic: %s | Payload: %s\n", MQTT_TOPIC, buffer);
    client.publish(MQTT_TOPIC, buffer);
  }
}
