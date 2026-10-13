# ESP32 HX711 Load Cell Weighbridge Scale

**Firmware Version:** 1.0.0 (Template)  
**Target Hardware:** ESP32 Dev Board + HX711 24-bit ADC + Strain Gauge Load Cell (50kg - 1000kg)

---

## 1. Wiring Pinout

| ESP32 Pin | HX711 Pin | Notes |
|---|---|---|
| `5V` | `VCC` | Power Supply |
| `GND` | `GND` | Ground |
| `GPIO 19` | `DT` / `DOUT` | Data Output |
| `GPIO 18` | `SCK` | Clock Signal |

---

## 2. Arduino IDE Dependencies

1. `HX711` by Bogdan Necula (v0.7.5+)
2. `PubSubClient` by Nick O'Leary (v2.8+)
3. `ArduinoJson` by Benoît Blanchon (v6.21+)

---

## 3. MQTT Topic & Payload Format

- **Publish Topic:** `wastedash/devices/{DEVICE_ID}/telemetry`
- **Sample Payload:**
```json
{
  "message_id": "SCL-SCALE-PLANT-PERUNGUDI-01-20000",
  "device_id": "SCALE-PLANT-PERUNGUDI-01",
  "device_type": "plant_sensor",
  "weight_kg": 245.85,
  "sensor_status": "NORMAL",
  "battery_pct": 100.0,
  "is_simulated": false
}
```
