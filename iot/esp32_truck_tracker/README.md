# ESP32 Smart Truck GPS Tracker

**Firmware Version:** 1.0.0 (Template)  
**Target Hardware:** ESP32 Dev Board + u-blox NEO-6M / NEO-8M GPS Module

---

## 1. Wiring Pinout

| ESP32 Pin | GPS Module Pin | Notes |
|---|---|---|
| `3V3` / `5V` | `VCC` | Connect according to GPS board voltage regulator |
| `GND` | `GND` | Common Ground |
| `GPIO 16` (`RX2`) | `TX` | Receives NMEA sentences from GPS module |
| `GPIO 17` (`TX2`) | `RX` | Optional configuration commands to GPS |

---

## 2. Arduino IDE Dependencies

1. `TinyGPSPlus` by Mikal Hart (v1.0.3+)
2. `PubSubClient` by Nick O'Leary (v2.8+)
3. `ArduinoJson` by Benoît Blanchon (v6.21+)

---

## 3. MQTT Topic & Payload Format

- **Publish Topic:** `wastedash/devices/{DEVICE_ID}/telemetry`
- **Sample Payload:**
```json
{
  "message_id": "TRK-TRUCK-GC01-TRACKER-15000",
  "device_id": "TRUCK-GC01-TRACKER",
  "device_type": "vehicle_tracker",
  "latitude": 13.0825,
  "longitude": 80.2110,
  "speed_kmh": 24.5,
  "heading_deg": 180.0,
  "battery_pct": 98.0,
  "sensor_status": "GPS_FIX_3D",
  "is_simulated": false
}
```

---

## 4. Flashing Instructions

1. Connect ESP32 to PC via Micro-USB.
2. Select Board: **ESP32 Dev Module**.
3. Compile and Flash. Ensure GPS antenna has a clear view of the sky for satellite lock.
