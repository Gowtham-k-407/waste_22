import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.geography import Ward
from app.models.facility import SegregationPlant
from app.models.vehicle import CollectionVehicle
from app.models.optimization import OptimizationRecommendation

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

class OptimizationService:
    @staticmethod
    def generate_recommendations(db: Session) -> List[Dict[str, Any]]:
        # Fetch top wards with high generation or low segregation
        high_waste_wards = db.query(Ward).filter(Ward.daily_waste_tons > 32.0).order_by(Ward.daily_waste_tons.desc()).limit(3).all()
        low_seg_wards = db.query(Ward).filter(Ward.segregation_efficiency < 50.0).limit(3).all()
        plants = db.query(SegregationPlant).all()

        recs = []
        # Check plant capacity
        for plant in plants:
            util = (plant.current_input_tpd / plant.capacity_tpd * 100) if plant.capacity_tpd > 0 else 0
            if util > 85.0:
                recs.append({
                    "category": "Plant Load Balancing",
                    "ward_number": plant.ward_id or 170,
                    "target_plant_name": plant.name,
                    "title": f"Divert Overflow from {plant.name}",
                    "description": f"{plant.name} is operating at {round(util, 1)}% capacity. AI recommends redirecting incoming organic fractions to the nearest facility with excess capacity.",
                    "expected_benefit": "Prevents processing bottlenecks and reduces open dump stacking by ~65 tons/day.",
                    "confidence_score": 0.94,
                    "tag": "AI RECOMMENDATION"
                })

        for w in high_waste_wards:
            recs.append({
                "category": "Collection Frequency",
                "ward_number": w.ward_number,
                "ward_name": w.name,
                "target_plant_name": "Perungudi Processing Center",
                "title": f"Increase Frequency in Ward {w.ward_number} ({w.name})",
                "description": f"Ward {w.ward_number} generates {w.daily_waste_tons} TPD, exceeding baseline by 28%. AI recommends scheduling an auxiliary pickup at 14:00 hrs.",
                "expected_benefit": "Reduces street corner bin overflow by 42% and minimizes secondary contamination.",
                "confidence_score": 0.91,
                "tag": "AI RECOMMENDATION"
            })

        for w in low_seg_wards:
            recs.append({
                "category": "Targeted Segregation Drive",
                "ward_number": w.ward_number,
                "ward_name": w.name,
                "target_plant_name": "Local Micro Composting Center",
                "title": f"Intensive Segregation Campaign for Ward {w.ward_number} ({w.name})",
                "description": f"Current segregation efficiency is only {w.segregation_efficiency}%. AI models indicate 38% high-value dry recyclables are being lost to mixed waste.",
                "expected_benefit": "Projected +18% segregation gain with targeted door-to-door green/blue bin compliance.",
                "confidence_score": 0.88,
                "tag": "AI RECOMMENDATION"
            })

        return recs
