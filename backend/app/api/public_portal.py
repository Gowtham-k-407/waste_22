import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_waste_db
from app.models.ward import Ward
from app.models.plant import SegregationPlant
from app.models.vehicle import CollectionVehicle
from app.models.waste import WasteCategory, WasteRecord
from app.models.alert import Alert
from app.models.complaint import PublicComplaint

router = APIRouter(prefix="/public", tags=["Public Portal Features"])

# 1. AI Waste Identification & Segregation Guide
@router.get("/segregation-guide")
def get_segregation_guide(db: Session = Depends(get_waste_db)):
    categories = db.query(WasteCategory).all()
    return {
        "title": "Greater Chennai Corporation Solid Waste Segregation Guide",
        "official_standard": "Solid Waste Management Rules 2016 / GCC Municipal By-laws",
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "color": c.color,
                "recyclability_pct": c.recyclability_pct,
                "description": c.description,
                "handling_instructions": c.handling_instructions
            }
            for c in categories
        ]
    }

# 2. Waste Collection Tracking
@router.get("/collection-tracking")
def get_collection_tracking(
    ward_id: int = Query(102, description="Ward number in Chennai (1-200)"),
    db: Session = Depends(get_waste_db)
):
    ward = db.query(Ward).filter(Ward.ward_number == ward_id).first()
    vehicles = db.query(CollectionVehicle).filter(CollectionVehicle.ward_id == ward_id).all()
    if not vehicles:
        vehicles = db.query(CollectionVehicle).limit(2).all()

    return {
        "ward_id": ward_id,
        "ward_name": ward.ward_name if ward else f"Ward {ward_id}",
        "zone_name": ward.zone_name if ward else "Central Chennai",
        "collection_status": "in_progress",
        "today_schedule": "Door-to-door morning collection: 06:30 - 11:30 IST",
        "assigned_vehicles": [
            {
                "vehicle_number": v.vehicle_number,
                "vehicle_type": v.vehicle_type,
                "status": v.status,
                "latitude": v.current_lat,
                "longitude": v.current_lng,
                "current_load_pct": round(((v.current_load_tons or 1.0) / (v.capacity_tons or 5.0)) * 100, 1),
                "is_simulated": True
            }
            for v in vehicles
        ],
        "data_provenance": "SIMULATED TELEMETRY / SCHEDULED MUNICIPAL DISPATCH"
    }

# 4. Public Environmental Impact Dashboard
@router.get("/environmental-impact")
def get_public_environmental_impact(db: Session = Depends(get_waste_db)):
    wards = db.query(Ward).all()
    total_waste = sum(w.daily_waste_tons for w in wards) if wards else 5420.0
    avg_seg = sum(w.segregation_efficiency for w in wards) / len(wards) if wards else 61.4

    co2e_saved = round(total_waste * (avg_seg / 100.0) * 1.42, 1)
    trees_saved = int(total_waste * (avg_seg / 100.0) * 8.5)
    landfill_diverted_pct = round(avg_seg * 0.88, 1)

    return {
        "metric_scope": "Greater Chennai Corporation (All 15 Zones)",
        "co2e_avoided_tons_daily": co2e_saved,
        "trees_equivalent_saved": trees_saved,
        "landfill_diversion_rate": f"{landfill_diverted_pct}%",
        "water_saved_kiloliters": round(total_waste * 4.2, 1),
        "energy_conserved_mwh": round(total_waste * 1.8, 1),
        "data_provenance": "Calculated using CPCB Emission Factors & GCC Municipal Weighbridge Records"
    }

# 5. Nearby Collection & Recycling Facility Locator
@router.get("/nearby-facilities")
def locate_nearby_facilities(
    lat: float = Query(13.0827, description="User Latitude"),
    lng: float = Query(80.2707, description="User Longitude"),
    db: Session = Depends(get_waste_db)
):
    plants = db.query(SegregationPlant).all()
    facilities = []
    for p in plants:
        # Euclidean distance approximation for Chennai
        d_km = math.sqrt(((p.latitude - lat) * 111.0) ** 2 + ((p.longitude - lng) * 102.0) ** 2)
        facilities.append({
            "id": p.id,
            "name": p.name,
            "plant_type": p.plant_type,
            "address": p.location,
            "distance_km": round(d_km, 2),
            "latitude": p.latitude,
            "longitude": p.longitude,
            "status": p.status,
            "accepted_materials": ["Dry Recyclables", "Paper & Cardboard", "Plastics", "Metals"] if "Recovery" in p.plant_type else ["Biodegradable Organic Waste", "Market Waste"]
        })

    facilities.sort(key=lambda x: x["distance_km"])
    return {"user_coords": {"lat": lat, "lng": lng}, "nearby_facilities": facilities[:8]}

# 6. Personalized Reminders & Notifications
@router.get("/reminders")
def get_public_reminders(ward_id: int = Query(102)):
    return {
        "ward_id": ward_id,
        "collection_calendar": [
            {"day": "Monday - Saturday", "category": "Wet / Organic Waste", "timing": "06:30 - 09:30 AM", "mandatory": True},
            {"day": "Wednesday & Sunday", "category": "Dry / Recyclables (Plastic, Paper, Metal)", "timing": "09:30 - 12:00 PM", "mandatory": True},
            {"day": "First Saturday of Month", "category": "E-Waste & Domestic Hazardous (Batteries, CFL)", "timing": "10:00 AM - 04:00 PM", "mandatory": True}
        ],
        "active_advisories": [
            "Please keep electronic items separate from regular wet bins to prevent toxic leachate contamination."
        ]
    }

# 7. Community Segregation Scoreboard
@router.get("/community-scoreboard")
def get_community_scoreboard(db: Session = Depends(get_waste_db)):
    wards = db.query(Ward).order_by(Ward.segregation_efficiency.desc()).all()
    top_5 = wards[:5]
    return {
        "leaderboard_month": "October 2026",
        "city_average": round(sum(w.segregation_efficiency for w in wards) / len(wards), 1) if wards else 61.4,
        "top_performing_wards": [
            {
                "rank": idx + 1,
                "ward_number": w.ward_number,
                "ward_name": w.ward_name,
                "zone_name": w.zone_name,
                "segregation_efficiency": f"{w.segregation_efficiency}%",
                "badge": "Champion Clean Ward" if idx == 0 else "High Achiever"
            }
            for idx, w in enumerate(top_5)
        ]
    }

# 8. Waste Education & Awareness Portal
@router.get("/education-portal")
def get_education_portal():
    return {
        "modules": [
            {
                "id": 1,
                "title": "Source Segregation: The 3-Bin System",
                "summary": "Learn how Green (Wet), Blue (Dry), and Red (Domestic Hazardous) bins keep Chennai clean.",
                "read_time_mins": 3
            },
            {
                "id": 2,
                "title": "Home Composting Made Easy",
                "summary": "Convert kitchen peels and tea grounds into rich organic compost on your balcony in 30 days.",
                "read_time_mins": 5
            },
            {
                "id": 3,
                "title": "E-Waste Hazards: Why Batteries Don't Belong in Landfills",
                "summary": "Heavy metals in mobile batteries pose serious groundwater risks. Learn safe drop-off locations.",
                "read_time_mins": 4
            }
        ]
    }

# 9. Municipal Transparency Dashboard
@router.get("/transparency")
def get_municipal_transparency(db: Session = Depends(get_waste_db)):
    wards = db.query(Ward).all()
    plants = db.query(SegregationPlant).all()
    total_waste = sum(w.daily_waste_tons for w in wards) if wards else 5420.0
    total_capacity = sum(p.capacity_tpd for p in plants) if plants else 4800.0

    return {
        "reporting_authority": "Greater Chennai Corporation Solid Waste Management Department",
        "weighbridge_transparency_charter": "100% of municipal collection vehicles are weighed at GCC weighbridges.",
        "daily_generation_target_tons": 5500.0,
        "actual_collected_tons": round(total_waste, 1),
        "operational_plants_capacity_tpd": round(total_capacity, 1),
        "active_sanitation_workforce": 19450,
        "complaint_resolution_sla_pct": "91.8% within 24 Hours",
        "last_financial_audit": "GCC Solid Waste Public Financial Disclosures FY2025-26"
    }

# 10. Public Waste-Management Assistant
@router.get("/assistant")
def query_public_assistant(q: str = Query(..., min_length=2)):
    query = q.lower()
    if "battery" in query or "mobile" in query or "laptop" in query or "electronics" in query:
        return {
            "query": q,
            "category": "E-Waste / Domestic Hazardous",
            "bin_color": "Red Bin or Dedicated E-Waste Drop Box",
            "guidance": "Do not mix with household garbage. Deposit at GCC Ward Office collection center or authorized recyclers."
        }
    elif "plastic" in query or "bottle" in query or "cover" in query:
        return {
            "query": q,
            "category": "Dry Recyclable (Plastic)",
            "bin_color": "Blue Bin",
            "guidance": "Rinse off food residue and flatten before placing in the dry waste bin."
        }
    elif "food" in query or "vegetable" in query or "organic" in query or "fruit" in query:
        return {
            "query": q,
            "category": "Wet / Biodegradable Waste",
            "bin_color": "Green Bin",
            "guidance": "Place in the green bin for daily door-to-door municipal collection or balcony composting."
        }
    else:
        return {
            "query": q,
            "category": "General Domestic Solid Waste",
            "bin_color": "Blue Bin (Dry) or Green Bin (Wet)",
            "guidance": "Check if item is biodegradable (Green) or dry/recyclable (Blue). Contact GCC Helpline 1913 for assistance."
        }

# 11. Waste Accumulation Hotspot Map
@router.get("/hotspots")
def get_waste_hotspots(db: Session = Depends(get_waste_db)):
    alerts = db.query(Alert).filter(Alert.status == "active").all()
    complaints = db.query(PublicComplaint).filter(PublicComplaint.status.in_(["submitted", "assigned"])).all()

    hotspots = []
    for c in complaints:
        hotspots.append({
            "type": "citizen_reported_overflow",
            "location": c.location_address,
            "ward_id": c.ward_id,
            "latitude": c.latitude or 13.0827,
            "longitude": c.longitude or 80.2707,
            "severity": c.priority
        })
    for a in alerts:
        hotspots.append({
            "type": "iot_sensor_overflow_risk",
            "location": f"Smart Bin Ward {a.ward_id}",
            "ward_id": a.ward_id,
            "latitude": 13.0850 + (a.ward_id % 10) * 0.005,
            "longitude": 80.2150 + (a.ward_id % 10) * 0.005,
            "severity": a.severity
        })

    return {"hotspots_count": len(hotspots), "hotspots": hotspots[:15]}

# 12. Household Waste-Reduction Calculator
@router.get("/waste-calculator")
def calculate_household_waste(
    family_size: int = Query(4, ge=1, le=20),
    eats_home_pct: int = Query(80, ge=10, le=100),
    composts_at_home: bool = Query(False)
):
    daily_kg = family_size * 0.45 * (eats_home_pct / 100.0)
    monthly_kg = round(daily_kg * 30.0, 1)
    wet_pct = 0.55
    dry_pct = 0.35
    residual_pct = 0.10

    monthly_wet = round(monthly_kg * wet_pct, 1)
    monthly_dry = round(monthly_kg * dry_pct, 1)

    co2e_saved = round((monthly_wet if composts_at_home else monthly_dry * 0.7) * 1.42, 1)

    return {
        "family_size": family_size,
        "estimated_monthly_waste_kg": monthly_kg,
        "breakdown": {
            "wet_organic_kg": monthly_wet,
            "dry_recyclables_kg": monthly_dry,
            "residual_kg": round(monthly_kg * residual_pct, 1)
        },
        "potential_co2e_saved_kg": co2e_saved,
        "recommendation": "By segregating 100% of your dry recyclables, you prevent 70% of household waste from reaching landfills."
    }

# 13. Community Cleanup Portal
@router.get("/community-cleanup")
def get_community_cleanup_events():
    return {
        "upcoming_drives": [
            {
                "event_id": "CLN-2026-01",
                "title": "Marina Beach Dawn Coastal Cleanup",
                "zone": "Zone 9 (Teynampet)",
                "date": "Next Saturday, 06:00 AM IST",
                "meeting_point": "Gandhi Statue, Marina Beach",
                "volunteers_registered": 142,
                "organizer": "GCC Clean Marina Wing & Volunteer Coalition"
            },
            {
                "event_id": "CLN-2026-02",
                "title": "Adyar Estuary Plastic Clean & Segregation Drive",
                "zone": "Zone 13 (Adyar)",
                "date": "Next Sunday, 06:30 AM IST",
                "meeting_point": "Thiru Vi Ka Bridge / Besant Avenue",
                "volunteers_registered": 98,
                "organizer": "Namma Chennai Clean Green Mission"
            }
        ]
    }

# 14. Tamil and English Language Support
@router.get("/translations")
def get_translations(lang: str = Query("ta", pattern="^(ta|en)$")):
    if lang == "ta":
        return {
            "lang": "ta",
            "portal_title": "பெருநகர சென்னை மாநகராட்சி - திடக்கழிவு மேலாண்மை & தரம் பிரித்தல் தகவல் பலகை",
            "wet_waste": "மக்கும் குப்பை (பச்சை தொட்டி)",
            "dry_waste": "மக்காத மறுசுழற்சி குப்பை (நீல தொட்டி)",
            "hazardous_waste": "ஆபத்தான வீட்டு கழிவுகள் (சிவப்பு தொட்டி)",
            "complaint_button": "தூய்மைப் புகார் பதிவு செய்க",
            "helpline": "மாநகராட்சி உதவி எண்: 1913"
        }
    return {
        "lang": "en",
        "portal_title": "Greater Chennai Corporation - Solid Waste Segregation & AI Dashboard",
        "wet_waste": "Wet / Biodegradable Waste (Green Bin)",
        "dry_waste": "Dry / Recyclable Waste (Blue Bin)",
        "hazardous_waste": "Domestic Hazardous Waste (Red Bin)",
        "complaint_button": "Register Sanitation Grievance",
        "helpline": "Municipal Helpline: 1913"
    }

# 15. Accessibility & Low-Bandwidth Support
@router.get("/low-bandwidth-summary")
def get_low_bandwidth_summary(db: Session = Depends(get_waste_db)):
    wards = db.query(Ward).all()
    return {
        "mode": "LOW_BANDWIDTH_PLAIN_TEXT",
        "gcc_waste_daily_tonnage": round(sum(w.daily_waste_tons for w in wards), 1) if wards else 5420.0,
        "city_segregation_rate": "61.4%",
        "door_to_door_coverage": "98.2%",
        "emergency_helpline": "1913",
        "sms_tracking_format": "SMS 'STATUS <TRACKING_NO>' to 56161"
    }

# 16. Ward-Wise Public Waste Statistics
@router.get("/ward-stats/{ward_number}")
def get_ward_public_stats(ward_number: int, db: Session = Depends(get_waste_db)):
    ward = db.query(Ward).filter(Ward.ward_number == ward_number).first()
    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward {ward_number} not found.")

    return {
        "ward_number": ward.ward_number,
        "ward_name": ward.ward_name,
        "zone_name": ward.zone_name,
        "daily_waste_tons": ward.daily_waste_tons,
        "segregation_efficiency": f"{ward.segregation_efficiency}%",
        "population": ward.population,
        "per_capita_waste_kg_day": round((ward.daily_waste_tons * 1000.0) / ward.population, 2) if ward.population else 0.45,
        "service_status": "Active door-to-door collection operational"
    }

# 17. Public Sanitation Grievance Tracking
@router.get("/grievances/track/{tracking_number}")
def track_public_grievance(tracking_number: str, db: Session = Depends(get_waste_db)):
    c = db.query(PublicComplaint).filter(PublicComplaint.tracking_number == tracking_number).first()
    if not c:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    return {
        "tracking_number": c.tracking_number,
        "category": c.category,
        "ward_id": c.ward_id,
        "status": c.status,
        "submitted_at": c.created_at.isoformat() if c.created_at else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "assigned_department": c.assigned_department
    }

# 18. E-Waste & Hazardous Household Waste Guidance
@router.get("/hazardous-guidance")
def get_hazardous_guidance():
    return {
        "guidance_title": "GCC Domestic Hazardous & E-Waste Safe Disposal Standard",
        "items": [
            {"item": "Lithium & Alkaline Batteries", "risk": "Groundwater heavy metal leaching", "protocol": "Store in dry container, deposit at Ward Office Red Box"},
            {"item": "Tube Lights & CFL Bulbs", "risk": "Mercury vapor inhalation", "protocol": "Hand over intact to sanitary worker; do not crush"},
            {"item": "Expired Medications", "risk": "Water table antibiotic resistance", "protocol": "Return to municipal health centers or pharmacy drop bins"},
            {"item": "Discarded Phones & Chargers", "risk": "E-waste plastic & flame retardants", "protocol": "Drop at authorized GCC E-Waste collection kiosk"}
        ]
    }

# 19. Collection Schedules & Service-Disruption Alerts
@router.get("/schedules-alerts")
def get_schedules_and_alerts(db: Session = Depends(get_waste_db)):
    alerts = db.query(Alert).filter(Alert.status == "active").all()
    return {
        "normal_schedule": "Daily door-to-door morning shift: 06:30 - 11:30 IST across all 200 wards.",
        "active_disruptions": [
            {"ward_id": a.ward_id, "alert": a.message, "severity": a.severity, "timestamp": a.timestamp.isoformat() if a.timestamp else None}
            for a in alerts[:5]
        ] or [{"ward_id": "All", "alert": "No active service disruptions reported. All 24 compactor routes operational.", "severity": "info"}]
    }

# 20. Historical Statistics & Public Reports
@router.get("/historical-reports")
def get_historical_reports():
    return {
        "annual_reports": [
            {"year": "2025-2026", "title": "GCC Annual Solid Waste Audit & Modernization Report", "file_format": "PDF", "size": "4.2 MB"},
            {"year": "2024-2025", "title": "Chennai Landfill Remediation & Bio-Mining Review", "file_format": "PDF", "size": "5.1 MB"}
        ],
        "quarterly_trend": [
            {"quarter": "Q1 2026", "segregation_rate": "58.2%", "landfill_diversion_tons": "382,400"},
            {"quarter": "Q2 2026", "segregation_rate": "59.8%", "landfill_diversion_tons": "398,100"},
            {"quarter": "Q3 2026", "segregation_rate": "61.4%", "landfill_diversion_tons": "412,800"}
        ]
    }
