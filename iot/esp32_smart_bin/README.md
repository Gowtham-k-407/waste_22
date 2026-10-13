# ESP32 Smart Bin Ultrasonic Level Monitor

**Firmware Version:** 1.0.0 (Template)  
**Target Hardware:** ESP32 NodeMCU / ESP-WROOM-32 + HC-SR04 / JSN-SR04T Waterproof Ultrasonic Sensor

---

## 1. Wiring Pinout

| ESP32 Pin | HC-SR04 Pin | Description |
|---|---|---|
| `5V` / `VIN` | `VCC` | 5V Power Supply |
| `GND` | `GND` | Common Ground |
| `GPIO 5` | `TRIG` | Trigger pulse pin |
| `GPIO 18` | `ECHO` | Echo pulse pin (Use 1kΩ + 2kΩ voltage divider if 5V echo) |

---

## 2. Arduino IDE Dependencies

Install the following libraries via **Tools > Manage Libraries...**:
1. `PubSubClient` by Nick O'Leary (v2.8+)
2. `ArduinoJson` by Benoît Blanchon (v6.21+)

---

## 3. MQTT Topic & Payload Format

- **Publish Topic:** `wastedash/devices/{DEVICE_ID}/telemetry`
- **Sample Payload:**
```json
{
  "message_id": "BIN-BIN-ZN08-W102-125000",
  "device_id": "BIN-ZN08-W102",
  "device_type": "smart_bin",
  "distance_cm": 28.5,
  "bin_fill_pct": 71.5,
  "sensor_status": "NORMAL",
  "battery_pct": 94.0,
  "is_simulated": false
}
```

---

## 4. Flashing Instructions

1. Open `esp32_smart_bin.ino` in Arduino IDE or VS Code with PlatformIO.
2. Update `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_BROKER`, and `DEVICE_ID`.
3. Select Board: **ESP32 Dev Module**, Upload Speed: **921600**, Flash Frequency: **80MHz**.
4. Hold **BOOT** button on ESP32 during upload if required.
5. Open Serial Monitor at **115200 baud** to verify Wi-Fi and MQTT connection logs.
