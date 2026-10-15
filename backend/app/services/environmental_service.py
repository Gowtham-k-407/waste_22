import math
from typing import Dict, Any

# CPCB & IPCC Solid Waste Model Constants for India
# Organic waste dumping in open landfills produces ~0.08 tons CH4 per ton wet waste
# 1 ton CH4 = ~28 tons CO2-equivalent over 100-year GWP
# Recycling 1 ton Plastic avoids ~1.5 tons CO2e vs virgin polymer production
# Recycling 1 ton Paper avoids ~0.9 tons CO2e & saves ~17 trees
# Recycling 1 ton Metal avoids ~4.2 tons CO2e

class EnvironmentalService:
    @staticmethod
    def calculate_city_impact(total_waste_daily_tons: float, segregation_rate_pct: float) -> Dict[str, Any]:
        segregated_tons = total_waste_daily_tons * (segregation_rate_pct / 100.0)
        unsegregated_tons = total_waste_daily_tons - segregated_tons
        
        # Avoided CO2e from segregated waste diverting to bio-CNG, composting, recycling
        co2e_avoided_tons_daily = round(segregated_tons * 1.42, 1)
        co2e_avoided_annual_tons = round(co2e_avoided_tons_daily * 365, 0)
        
        # Methane emission risk from unsegregated organic waste dumped at Perungudi/Kodungaiyur
        methane_risk_tons_daily = round(unsegregated_tons * 0.52 * 0.075, 1)
        
        # Landfill volume burden saved (assuming compacted density 0.75 tons/m3)
        landfill_saved_m3_daily = round(segregated_tons / 0.75, 1)
        landfill_saved_m3_annual = round(landfill_saved_m3_daily * 365, 0)
        
        # Recyclable material leakage risk
        plastic_leakage_risk_score = round(max(10.0, min(95.0, 100.0 - (segregation_rate_pct * 1.1))), 1)

        # Trees equivalent saved
        trees_equivalent_annual = int(segregated_tons * 0.15 * 17 * 365)

        return {
            "co2e_avoided_daily_tons": co2e_avoided_tons_daily,
            "co2e_avoided_annual_tons": co2e_avoided_annual_tons,
            "methane_risk_daily_tons": methane_risk_tons_daily,
            "landfill_volume_saved_daily_m3": landfill_saved_m3_daily,
            "landfill_volume_saved_annual_m3": landfill_saved_m3_annual,
            "plastic_leakage_risk_score": plastic_leakage_risk_score,
            "trees_equivalent_saved_annual": trees_equivalent_annual,
            "calculation_methodology": "CPCB Solid Waste Management Rules 2016 & IPCC Waste Model Tier-1 Emission Factors for South Asia",
            "disclaimer": "These are estimated environmental indicators based on available waste data and defined calculation methodologies. Do not present estimated values as official pollution measurements unless they come from verified official sources."
        }
