from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.geography import Ward, Zone
from app.schemas.ward import WardSummary, WardDetail, WardRanking

router = APIRouter(prefix="/wards", tags=["Ward Analytics"])

@router.get("/", response_model=List[WardSummary])
def get_all_wards(
    zone_id: Optional[int] = None,
    sort_by: Optional[str] = Query("ward_number", pattern="^(ward_number|daily_waste_tons|segregation_efficiency|pollution_risk_score|recycling_potential)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Ward)
    if zone_id:
        query = query.filter(Ward.zone_id == zone_id)

    if sort_by == "daily_waste_tons":
        query = query.order_by(Ward.daily_waste_tons.desc())
    elif sort_by == "segregation_efficiency":
        query = query.order_by(Ward.segregation_efficiency.desc())
    elif sort_by == "pollution_risk_score":
        query = query.order_by(Ward.pollution_risk_score.desc())
    elif sort_by == "recycling_potential":
        query = query.order_by(Ward.recycling_potential.desc())
    else:
        query = query.order_by(Ward.ward_number.asc())

    wards = query.all()
    result = []
    for w in wards:
        result.append(WardSummary(
            id=w.id,
            ward_number=w.ward_number,
            name=w.name,
            zone_number=w.zone.zone_number if w.zone else 1,
            zone_name=w.zone.name if w.zone else "Zone",
            latitude=w.latitude,
            longitude=w.longitude,
            population=w.population,
            daily_waste_tons=w.daily_waste_tons,
            segregation_efficiency=w.segregation_efficiency,
            pollution_risk_score=w.pollution_risk_score,
            recycling_potential=w.recycling_potential,
            primary_waste_type=w.primary_waste_type,
            collection_frequency_per_day=w.collection_frequency_per_day
        ))
    return result

@router.get("/rankings", response_model=List[WardRanking])
def get_ward_rankings(db: Session = Depends(get_db)):
    rankings = []
    # 1. Highest Waste Generation
    top_gen = db.query(Ward).order_by(Ward.daily_waste_tons.desc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="highest_waste",
        title="Highest Waste Generation",
        description="Wards producing the largest daily tonnage of solid waste in Chennai.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"{w.daily_waste_tons} Tons/day", "score": w.daily_waste_tons} for w in top_gen]
    ))

    # 2. Highest Plastic Waste
    high_plastic = db.query(Ward).filter(Ward.primary_waste_type == "Plastic").order_by(Ward.daily_waste_tons.desc()).limit(5).all()
    if not high_plastic:
        high_plastic = db.query(Ward).order_by(Ward.daily_waste_tons.desc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="highest_plastic",
        title="Highest Plastic Waste",
        description="Wards generating severe concentrations of single-use and rigid plastic packaging.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"{round(w.daily_waste_tons * 0.22, 1)} Tons/day Plastic", "score": round(w.daily_waste_tons * 0.22, 1)} for w in high_plastic]
    ))

    # 3. Highest Organic Waste
    high_org = db.query(Ward).order_by(Ward.daily_waste_tons.desc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="highest_organic",
        title="Highest Organic Waste",
        description="Wards with peak biodegradable kitchen, floral, and horticultural waste output.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"{round(w.daily_waste_tons * 0.45, 1)} Tons/day Organic", "score": round(w.daily_waste_tons * 0.45, 1)} for w in high_org]
    ))

    # 4. Lowest Segregation Efficiency
    low_seg = db.query(Ward).order_by(Ward.segregation_efficiency.asc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="lowest_segregation",
        title="Lowest Segregation Efficiency",
        description="Critical attention required: Wards with highest mixed waste and poor bin compliance.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"{w.segregation_efficiency}% Segregated", "score": w.segregation_efficiency} for w in low_seg]
    ))

    # 5. Highest Pollution Risk
    high_poll = db.query(Ward).order_by(Ward.pollution_risk_score.desc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="highest_pollution_risk",
        title="Highest Pollution Risk",
        description="Vulnerable areas prone to open littering, drainage clogging, and uncollected piles.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"Risk Index {w.pollution_risk_score}/100", "score": w.pollution_risk_score} for w in high_poll]
    ))

    # 6. Highest Recycling Potential
    high_rec = db.query(Ward).order_by(Ward.recycling_potential.desc()).limit(5).all()
    rankings.append(WardRanking(
        ranking_type="highest_recycling_potential",
        title="Highest Recycling Potential",
        description="Prime candidate wards for dry-waste recovery expansion and scrap bank collection.",
        wards=[{"ward_number": w.ward_number, "name": w.name, "value": f"{w.recycling_potential}% Potential", "score": w.recycling_potential} for w in high_rec]
    ))

    return rankings

@router.get("/{ward_number}", response_model=WardDetail)
def get_ward_by_number(ward_number: int, db: Session = Depends(get_db)):
    w = db.query(Ward).filter(Ward.ward_number == ward_number).first()
    if not w:
        raise HTTPException(status_code=404, detail=f"Ward {ward_number} not found")

    # Breakdown for this ward
    daily = w.daily_waste_tons
    breakdown = [
        {"category": "Organic Waste", "tons": round(daily * 0.42, 1), "percentage": 42.0, "color": "#10B981"},
        {"category": "Food Waste", "tons": round(daily * 0.20, 1), "percentage": 20.0, "color": "#84CC16"},
        {"category": "Plastic", "tons": round(daily * 0.16, 1), "percentage": 16.0, "color": "#0EA5E9"},
        {"category": "Cardboard", "tons": round(daily * 0.08, 1), "percentage": 8.0, "color": "#D97706"},
        {"category": "Paper", "tons": round(daily * 0.06, 1), "percentage": 6.0, "color": "#F59E0B"},
        {"category": "Mixed / Other", "tons": round(daily * 0.08, 1), "percentage": 8.0, "color": "#64748B"}
    ]

    nearby_plants = [
        {"name": "Perungudi Processing Center", "distance_km": 8.4, "capacity_status": "83.8% Utilized"},
        {"name": "Chetpet Micro Composting Center", "distance_km": 3.1, "capacity_status": "84.0% Utilized"}
    ]

    recs = [
        f"Increase door-to-door collection frequency to {w.collection_frequency_per_day + 1} times/day during peak market hours.",
        "Direct commercial organic waste to local Micro-Composting Center (MCC).",
        "Conduct green-bin awareness drive to raise current segregation from " + str(w.segregation_efficiency) + "% towards city target 80%."
    ]

    return WardDetail(
        id=w.id,
        ward_number=w.ward_number,
        name=w.name,
        zone_number=w.zone.zone_number if w.zone else 1,
        zone_name=w.zone.name if w.zone else "Zone",
        latitude=w.latitude,
        longitude=w.longitude,
        population=w.population,
        daily_waste_tons=w.daily_waste_tons,
        segregation_efficiency=w.segregation_efficiency,
        pollution_risk_score=w.pollution_risk_score,
        recycling_potential=w.recycling_potential,
        primary_waste_type=w.primary_waste_type,
        collection_frequency_per_day=w.collection_frequency_per_day,
        category_breakdown=breakdown,
        nearby_plants=nearby_plants,
        active_alerts=[],
        ai_recommendations=recs
    )
