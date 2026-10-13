/*
 * WasteDash / GCC Smart Waste Platform
 * Firmware: ESP32 Smart Garbage Truck GPS Telemetry Tracker
 * Hardware: ESP32 Dev Board + NEO-6M / NEO-8M GPS Module (UART)
 * Protocol: MQTT over TLS (Port 8883) or Non-TLS (Port 1883)
 * Status: Starter Firmware Template (Modular Arduino / C++)
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TinyGPSPlus.h>

// ================= USER CONFIGURATION =================
const char* WIFI_SSID       = "YOUR_WIFI_OR_HOTSPOT_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";

const char* MQTT_BROKER     = "broker.wastedash.chennaiswm.gov.in";
const int   MQTT_PORT       = 8883;
const char* MQTT_USER       = "truck_user";
const char* MQTT_PASS       = "truck_password";

const char* DEVICE_ID       = "TRUCK-GC01-TRACKER";
const char* MQTT_TOPIC      = "wastedash/devices/TRUCK-GC01-TRACKER/telemetry";

// Hardware UART Pins for GPS (NEO-6M)
const int GPS_RX_PIN = 16; // Connects to GPS TX
const int GPS_TX_PIN = 17; // Connects to GPS RX
const uint32_t GPS_BAUD = 9600;

// Reporting interval
const unsigned long REPORT_INTERVAL_MS = 15000; // 15 seconds

// ================= GLOBALS =================
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

WiFiClientSecure espClient;
PubSubClient client(espClient);
unsigned long lastMsgTime = 0;

void setupWifi() {
  delay(10);
  Serial.printf("[WiFi] Connecting to %s...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
  }
}

void reconnectMqtt() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting... ");
    String clientId = "ESP32-Truck-" + String(DEVICE_ID);
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
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  setupWifi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  Serial.println("[GPS Tracker] Initialized.");
}

void loop() {
  // Feed GPS serial stream
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

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

    double lat = 13.0825; // Fallback Anna Nagar baseline if fix not acquired yet
    double lng = 80.2110;
    float speed_kmh = 0.0;
    float heading = 0.0;

    if (gps.location.isValid()) {
      lat = gps.location.lat();
      lng = gps.location.lng();
      speed_kmh = gps.speed.kmph();
      heading = gps.course.deg();
    }

    StaticJsonDocument<256> doc;
    doc["message_id"]    = "TRK-" + String(DEVICE_ID) + "-" + String(now);
    doc["device_id"]     = DEVICE_ID;
    doc["device_type"]   = "vehicle_tracker";
    doc["latitude"]      = lat;
    doc["longitude"]     = lng;
    doc["speed_kmh"]     = speed_kmh;
    doc["heading_deg"]   = heading;
    doc["battery_pct"]   = 98.0;
    doc["sensor_status"] = gps.location.isValid() ? "GPS_FIX_3D" : "GPS_SEARCHING";
    doc["is_simulated"]  = false;

    char buffer[256];
    serializeJson(doc, buffer);

    Serial.printf("[MQTT Publish] %s -> %s\n", MQTT_TOPIC, buffer);
    client.publish(MQTT_TOPIC, buffer);
  }
}
