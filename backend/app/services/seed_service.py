import os
import json
import sqlite3
import random
import uuid
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.security import hash_password
from app.core.database import (
    user_engine, staff_engine, waste_engine,
    UserSessionLocal, StaffSessionLocal, WasteSessionLocal,
    UserBase, StaffBase, WasteBase
)
from app.core.rbac import MUNICIPAL_STAFF_ROLES
from app.models.user import User, PasswordResetToken, AuthAuditLog
from app.models.staff import StaffProfile, StaffDutyAssignment, StaffAuditLog
from app.models.geography import Zone, Ward
from app.models.waste import WasteCategory, WasteRecord
from app.models.facility import SegregationPlant
from app.models.vehicle import CollectionVehicle
from app.models.detection import AIDetection
from app.models.contribution import ImageContribution
from app.models.upload import Upload, DatasetImage
from app.models.ai_model import AIModelVersion, TrainingJob
from app.models.dataset import DatasetSource, DatasetImport
from app.models.optimization import EnvironmentalMetric, OperationalAlert, OptimizationRecommendation
from app.models.iot import IoTDevice, DeviceTelemetry
from app.models.complaint import (
    PublicComplaint, ComplaintFollowUp, Notification,
    WeighbridgeRecord, SimulationRun, AIInferenceAudit
)

logger = logging.getLogger("wastedash.seed")

CHENNAI_ZONES = [
    (1, "Thiruvottiyur", "Tollgate, Thiruvottiyur High Road"),
    (2, "Manali", "Manali Express Road"),
    (3, "Madhavaram", "Madhavaram High Road"),
    (4, "Tondiarpet", "Old Washermanpet"),
    (5, "Royapuram", "MC Road, Royapuram"),
    (6, "Thiru-Vi-Ka Nagar", "Strahans Road, Otteri"),
    (7, "Ambattur", "CTH Road, Ambattur"),
    (8, "Anna Nagar", "2nd Avenue, Anna Nagar"),
    (9, "Teynampet", "Mount Road, Teynampet"),
    (10, "Kodambakkam", "Arcot Road, Kodambakkam"),
    (11, "Valasaravakkam", "Arcot Road, Valasaravakkam"),
    (12, "Alandur", "GST Road, Alandur"),
    (13, "Adyar", "LB Road, Adyar"),
    (14, "Perungudi", "OMR, Perungudi"),
    (15, "Sholinganallur", "ECR/OMR Junction, Sholinganallur")
]

WASTE_CATEGORIES_DATA = [
    ("Organic Waste", "#10B981", 95.0, "Biodegradable plant matter, leaves, tree trimmings and garden cuttings suitable for aerated composting.", "Route to nearest Micro-Composting Center (MCC)."),
    ("Food Waste", "#84CC16", 92.0, "Kitchen wet waste, vegetable peels, plate scraps and restaurant organic leftovers.", "Transport to Bio-CNG / Anaerobic Digestion facilities."),
    ("Plastic", "#0EA5E9", 85.0, "Rigid HDPE/PP containers, LDPE packaging films, and PET beverage containers.", "Sort at Material Recovery Facility (MRF) and bale for mechanical recyclers."),
    ("Paper", "#F59E0B", 90.0, "Newspapers, corrugated boxes, office stationery, books and leaflets.", "Keep clean and dry; send to paper pulping recycling mills."),
    ("Cardboard", "#D97706", 92.0, "Brown Kraft cartons, shipping packaging boxes, and grayboard boxes.", "Flatten and bundle for industrial corrugated recycling plants."),
    ("Glass", "#06B6D4", 100.0, "Transparent and amber glass bottles, jars, and unbroken glassware.", "Segregate by color and transfer to cullet melting glass furnaces."),
    ("Metal", "#6366F1", 98.0, "Aluminum cans, tin containers, iron scrap, and aerosol canisters.", "Magnetic separation followed by scrap foundry remelting."),
    ("Textile Waste", "#EC4899", 65.0, "Discarded apparel, tailoring fabric trimmings, jute and synthetic bags.", "Direct to secondary shredding, insulation, or upcycling centers."),
    ("Electronic Waste", "#8B5CF6", 80.0, "Old cell phones, lithium-ion cells, PCB boards, cords, and small appliances.", "Strictly divert to authorized CPCB registered e-waste recyclers."),
    ("Hazardous Waste", "#EF4444", 15.0, "Sanitary pads, expired pharmaceuticals, paint containers, solvent cans, and syringes.", "Incinerate at Common Bio-medical / Hazardous Waste Treatment Facility."),
    ("Mixed / Unsegregated Waste", "#64748B", 30.0, "Unsorted domestic waste mixture requiring mechanical sorting and RDF separation.", "Send through trommel screens for RDF recovery; residue to secured landfill.")
]

PLANTS_DATA = [
    ("Perungudi Solid Waste Processing Center", "Segregation Plant & Secured Landfill", 14, 170, 12.9372, 80.2312, 2600.0, 2180.0, "active", "Organic,Plastic,Paper,Metal,Glass,Cardboard", "Urbaser Sumeet / GCC", "+91 44 2496 1122", "Perungudi Dump Yard Complex, Pallavaram 200 Ft Radial Road, Chennai"),
    ("Kodungaiyur Integrated Waste Management Facility", "Segregation Plant & Processing Hub", 4, 38, 13.1412, 80.2645, 2400.0, 2120.0, "active", "Organic,Plastic,Paper,Metal,Glass,Cardboard", "Ramky Enviro Engineers / GCC", "+91 44 2598 4401", "Kodungaiyur, Tondiarpet High Road, Chennai"),
    ("Madhavaram 100 TPD Bio-CNG Facility", "Bio-CNG & Bio-Methanation", 3, 32, 13.1524, 80.2185, 100.0, 88.5, "active", "Food Waste,Organic Waste", "GCC Green Energy Venture", "+91 44 2553 7810", "Near Madhavaram Truck Terminal, GNT Road, Chennai"),
    ("Chetpet Micro Composting Center (MCC)", "Composting Plant", 9, 112, 13.0694, 80.2425, 25.0, 21.0, "active", "Food Waste,Organic Waste", "Greater Chennai Corporation", "+91 44 2836 2901", "Harrington Road, Chetpet, Chennai"),
    ("Pallikaranai Material Recovery Facility (MRF)", "Recycling Facility (Dry Waste)", 14, 175, 12.9410, 80.2080, 150.0, 128.0, "active", "Plastic,Paper,Cardboard,Glass,Metal", "Tamil Nadu Waste Management Ltd", "+91 44 2246 8812", "Velachery-Tambaram Main Road, Pallikaranai, Chennai"),
    ("Otteri Resource Recovery & Baling Station", "Material Recovery Facility", 6, 74, 13.0921, 80.2514, 80.0, 64.0, "active", "Plastic,Paper,Cardboard,Metal", "Greater Chennai Corporation", "+91 44 2662 1099", "Strahans Road, Otteri, Chennai"),
    ("Koyambedu Wholesale Market Biogas Unit", "Bio-CNG & Biomethanation", 10, 127, 13.0688, 80.1912, 35.0, 31.5, "active", "Food Waste,Organic Waste", "CMDA & GCC Joint Venture", "+91 44 2479 6633", "Koyambedu Wholesale Flower & Veg Market, Chennai"),
    ("Alandur Waste Transfer & Compactor Station", "Transfer Station", 12, 160, 12.9975, 80.1985, 300.0, 245.0, "active", "Mixed Waste,Organic,Plastic", "Urbaser Sumeet", "+91 44 2234 1500", "GST Road, Guindy-Alandur Border, Chennai"),
    ("Royapuram Decentralized MCC & Nursery", "Composting Facility", 5, 50, 13.1118, 80.2925, 20.0, 14.5, "active", "Organic Waste,Food Waste", "GCC Zone 5 SWM", "+91 44 2595 3320", "Kalmandapam, Royapuram, Chennai"),
    ("Sholinganallur E-Waste & Plastic Segregation Unit", "Recycling Facility", 15, 196, 12.9015, 80.2275, 60.0, 42.0, "active", "Electronic Waste,Plastic,Metal", "Greengate Eco Solutions", "+91 44 2450 7788", "OMR IT Corridor, Sholinganallur, Chennai"),
    ("Ambattur Industrial Dry Waste Recovery Hub", "Recycling Facility", 7, 85, 13.1145, 80.1542, 120.0, 95.0, "active", "Cardboard,Paper,Metal,Plastic", "Ambattur Industrial Association", "+91 44 2625 4411", "Ambattur Industrial Estate Phase II, Chennai"),
    ("Valasaravakkam Micro Processing Plant", "Micro Segregation Plant", 11, 148, 13.0425, 80.1740, 40.0, 12.0, "maintenance", "Organic,Plastic,Cardboard", "GCC Zone 11 SWM", "+91 44 2486 9911", "Arcot Road, Valasaravakkam, Chennai")
]

WARD_NAMES = [
    "Tollgate", "Ernavoor", "Kathivakkam", "Sathangadu", "Chinnasekkadu", "Manali New Town",
    "Madhavaram Central", "Moolakadai", "Vyasarpadi", "Tondiarpet East", "Old Washermanpet",
    "Royapuram Harbor", "Sowcarpet", "Chintadripet", "Otteri", "Purasawalkam", "Perambur",
    "Kolathur", "Villivakkam", "Ambattur Industrial", "Korattur Lake", "Anna Nagar Tower",
    "Shenoy Nagar", "Aminjikarai", "Chetpet", "Nungambakkam", "T. Nagar Panagal Park",
    "Teynampet", "Alwarpet", "Mylapore", "Triplicane", "Royapettah", "Kodambakkam",
    "Vadapalani", "Ashok Nagar", "KK Nagar", "Valasaravakkam", "Virugambakkam", "Porur",
    "Ramapuram", "Alandur Metro", "Guindy", "St. Thomas Mount", "Adyar", "Besant Nagar",
    "Thiruvanmiyur", "Kotturpuram", "Perungudi OMR", "Thoraipakkam", "Palavakkam",
    "Neelankarai", "Sholinganallur", "Semmancheri", "Uthandi"
]

def init_all_tables():
    """Ensure tables are created independently in all three databases."""
    logger.info("Initializing tables in Database A (Users), Database B (Staff), and Database C (Waste Operations)...")
    UserBase.metadata.create_all(bind=user_engine)
    StaffBase.metadata.create_all(bind=staff_engine)
    WasteBase.metadata.create_all(bind=waste_engine)

def seed_database_a(user_db: Session):
    """Seed Database A: Users and Authentication."""
    # 1. Bootstrap Admin account requested: admin@wastesegeregate.in / admin123
    bootstrap_email = settings.ADMIN_BOOTSTRAP_EMAIL.lower()
    existing_bootstrap = user_db.query(User).filter(User.email == bootstrap_email).first()
    if not existing_bootstrap:
        b_admin = User(
            username="system_admin",
            email=bootstrap_email,
            hashed_password=hash_password(settings.ADMIN_BOOTSTRAP_PASSWORD),
            full_name="Platform Security Administrator",
            role="system_admin",
            organization="Greater Chennai Corporation IT Cell",
            city="Chennai",
            is_active=True,
            email_verified=True,
            must_change_password=True, # Requires password change on initial login
            contribution_points=5000,
            badges="System Architect, Super Admin"
        )
        user_db.add(b_admin)
        user_db.commit()
        logger.info(f"Provisioned initial bootstrap administrator: {bootstrap_email}")

    # 2. Migrate legacy users from chennai_waste.db if present
    legacy_db_path = os.path.join(settings.BASE_DIR, "chennai_waste.db")
    if os.path.exists(legacy_db_path):
        try:
            con = sqlite3.connect(legacy_db_path)
            cur = con.cursor()
            for row in cur.execute("SELECT username, email, hashed_password, full_name, role, organization, city, contribution_points, badges FROM users;").fetchall():
                u_name, u_email, u_hash, u_fn, u_role, u_org, u_city, u_pts, u_bdg = row
                if not user_db.query(User).filter(User.email == u_email).first():
                    user_db.add(User(
                        username=u_name,
                        email=u_email,
                        hashed_password=u_hash,
                        full_name=u_fn,
                        role=u_role,
                        organization=u_org or "GCC",
                        city=u_city or "Chennai",
                        contribution_points=u_pts or 50,
                        badges=u_bdg or "Eco Citizen",
                        is_active=True,
                        email_verified=True
                    ))
            user_db.commit()
            con.close()
        except Exception as e:
            logger.warning(f"Legacy user migration notice: {e}")

    # 3. Add representative staff users and public contributors
    initial_users = [
        User(username="admin", email="admin@chennaiswm.gov.in", hashed_password=hash_password("Admin@123"), full_name="Dr. M. Soundararajan, IAS (Municipal Commissioner)", role="system_admin", organization="Greater Chennai Corporation (GCC)", city="Chennai", contribution_points=1250, badges="Municipal Director"),
        User(username="commissioner", email="commissioner@chennaiswm.gov.in", hashed_password=hash_password("Admin@123"), full_name="Dr. M. Soundararajan, IAS", role="municipal_commissioner", organization="Greater Chennai Corporation", city="Chennai", contribution_points=1200, badges="Municipal Commissioner"),
        User(username="kumar_officer", email="kumar.swm@chennaiswm.gov.in", hashed_password=hash_password("Officer@123"), full_name="Er. R. Kumar", role="sanitary_officer", organization="GCC Zone 8 - Anna Nagar", city="Chennai", contribution_points=850, badges="Senior Sanitary Officer"),
        User(username="perungudi_operator", email="operator.perungudi@chennaiswm.gov.in", hashed_password=hash_password("Operator@123"), full_name="K. Vaitheeswaran", role="waste_processing_plant_operator", organization="Perungudi SWM Processing Plant", city="Chennai", contribution_points=600, badges="Plant Operator"),
        User(username="ai_lead", email="ai.lead@chennaiswm.gov.in", hashed_password=hash_password("Admin@123"), full_name="Dr. Ananya Natarajan", role="ai_admin", organization="IIT Madras / GCC AI Lab", city="Chennai", contribution_points=2400, badges="AI Vision Lead"),
        User(username="citizen_priya", email="priya.chennai@gmail.com", hashed_password=hash_password("Citizen@123"), full_name="Priya Subramanian", role="contributor", organization="Chennai Green Earth Volunteers", city="Chennai", contribution_points=420, badges="Eco Citizen, Master Segregator"),
        User(username="public_guest", email="guest@chennai.in", hashed_password=hash_password("Guest@123"), full_name="Public Resident of Chennai", role="public", organization="Chennai Resident", city="Chennai", contribution_points=50, badges="Eco Citizen")
    ]
    for u in initial_users:
        if not user_db.query(User).filter(User.email == u.email).first():
            user_db.add(u)
    user_db.commit()

def seed_database_b(staff_db: Session, user_db: Session):
    """Seed Database B: All 35 Municipal Staff Profiles."""
    if staff_db.query(StaffProfile).count() >= 35:
        return

    logger.info("Seeding Database B with 35 GCC Municipal Staff Profiles...")

    # Ensure users exist in Database A for linking
    role_specs = list(MUNICIPAL_STAFF_ROLES.items())
    for idx, (role_code, meta) in enumerate(role_specs, start=1):
        emp_code = f"GCC-EMP-{idx:03d}"
        existing = staff_db.query(StaffProfile).filter(StaffProfile.employee_id == emp_code).first()
        if existing:
            continue

        staff_email = f"staff.{role_code}@chennaiswm.gov.in"
        u = user_db.query(User).filter(User.email == staff_email).first()
        if not u:
            u = User(
                username=f"staff_{role_code[:15]}_{idx}",
                email=staff_email,
                hashed_password=hash_password("Staff@123"),
                full_name=f"{meta['title']} Staff Official",
                role=role_code,
                organization=f"GCC - {meta['department']}",
                city="Chennai",
                is_active=True,
                email_verified=True,
                must_change_password=False
            )
            user_db.add(u)
            user_db.commit()
            user_db.refresh(u)

        # Assign realistic zone, ward, or facility based on role scope
        zone_num = (idx % 15) + 1
        ward_num = ((idx * 5) % 200) + 1
        facility_idx = (idx % len(PLANTS_DATA))
        facility_name = PLANTS_DATA[facility_idx][0]

        profile = StaffProfile(
            user_id=u.id,
            employee_id=emp_code,
            full_name=u.full_name,
            job_title=meta["title"],
            role_code=role_code,
            department=meta["department"],
            assigned_zone_number=zone_num if meta["scope"] in ["zone_level", "ward_level"] else None,
            assigned_ward_number=ward_num if meta["scope"] == "ward_level" else None,
            assigned_facility_id=facility_idx + 1 if meta["scope"] == "facility_level" else None,
            assigned_facility_name=facility_name if meta["scope"] == "facility_level" else None,
            assigned_vehicle_code=f"GC-{(idx % 24) + 1:02d}" if "Driver" in meta["title"] or "Vehicle" in meta["title"] else None,
            phone_number=f"+91 44 2538 {1000 + idx}",
            shift="Morning (06:00 - 14:00)" if idx % 2 == 0 else "General (09:00 - 17:30)",
            employment_status="Active"
        )
        staff_db.add(profile)
        staff_db.commit()

        # Add initial duty assignment
        duty = StaffDutyAssignment(
            staff_id=profile.id,
            duty_date=datetime.now(timezone.utc),
            shift=profile.shift,
            task_description=f"Operational Duty: {meta['title']} for {meta['department']}",
            ward_number=profile.assigned_ward_number,
            facility_name=profile.assigned_facility_name,
            status="In Progress"
        )
        staff_db.add(duty)
        staff_db.commit()

def seed_database_c(waste_db: Session):
    """Seed Database C: Waste Operations, Geography, Vehicles, Plants, AI, and Grievances."""
    # Check if geography already seeded
    if waste_db.query(Zone).count() > 0:
        return

    logger.info("Seeding Database C with Zones, 200 Wards, Facilities, Fleet, AI, and Grievance Data...")

    # 1. 15 Zones
    zone_objs = {}
    for z_no, z_name, z_hq in CHENNAI_ZONES:
        z = Zone(zone_number=z_no, name=z_name, headquarters=z_hq)
        waste_db.add(z)
        waste_db.commit()
        zone_objs[z_no] = z

    # 2. 200 Wards with realistic Chennai geographic data
    wards = []
    for w_no in range(1, 201):
        z_no = min(15, max(1, (w_no - 1) // 13 + 1))
        zone_ref = zone_objs[z_no]
        lat_base = 13.18 - ((w_no - 1) / 200.0) * 0.31
        lat = round(lat_base + random.uniform(-0.012, 0.012), 4)
        lng = round(80.21 + random.uniform(-0.065, 0.065), 4)

        name_idx = (w_no - 1) % len(WARD_NAMES)
        w_name = f"{WARD_NAMES[name_idx]} (Ward {w_no})"
        pop = random.randint(35000, 68000)
        daily_waste = round((pop * random.uniform(0.48, 0.62)) / 1000.0, 1)

        if z_no in [8, 9, 13]:
            seg_eff = round(random.uniform(62.0, 84.0), 1)
            poll_risk = round(random.uniform(25.0, 48.0), 1)
            rec_pot = round(random.uniform(72.0, 89.0), 1)
        elif z_no in [4, 5, 10]:
            seg_eff = round(random.uniform(38.0, 58.0), 1)
            poll_risk = round(random.uniform(55.0, 85.0), 1)
            rec_pot = round(random.uniform(65.0, 78.0), 1)
        else:
            seg_eff = round(random.uniform(48.0, 68.0), 1)
            poll_risk = round(random.uniform(40.0, 65.0), 1)
            rec_pot = round(random.uniform(68.0, 82.0), 1)

        primary = random.choices(
            ["Organic Waste", "Food Waste", "Plastic", "Cardboard", "Mixed / Unsegregated Waste"],
            weights=[40, 25, 15, 10, 10]
        )[0]

        ward = Ward(
            ward_number=w_no,
            name=w_name,
            zone_id=zone_ref.id,
            latitude=lat,
            longitude=lng,
            population=pop,
            area_sqkm=round(random.uniform(1.2, 3.8), 2),
            daily_waste_tons=daily_waste,
            segregation_efficiency=seg_eff,
            pollution_risk_score=poll_risk,
            recycling_potential=rec_pot,
            primary_waste_type=primary,
            collection_frequency_per_day=random.choice([2, 2, 3])
        )
        wards.append(ward)

    waste_db.add_all(wards)
    waste_db.commit()

    # 3. 11 Canonical Waste Categories
    for c_name, c_col, c_rec, c_desc, c_inst in WASTE_CATEGORIES_DATA:
        cat = WasteCategory(
            name=c_name,
            color=c_col,
            recyclability_pct=c_rec,
            description=c_desc,
            handling_instructions=c_inst
        )
        waste_db.add(cat)
    waste_db.commit()

    # 4. 12 Segregation Plants
    for p_name, p_type, p_z, p_w, p_lat, p_lng, p_cap, p_curr, p_stat, p_acc, p_op, p_ph, p_addr in PLANTS_DATA:
        plant = SegregationPlant(
            name=p_name,
            facility_type=p_type,
            zone_id=p_z,
            ward_id=p_w,
            latitude=p_lat,
            longitude=p_lng,
            capacity_tpd=p_cap,
            current_input_tpd=p_curr,
            status=p_stat,
            accepted_categories=p_acc,
            operator_name=p_op,
            contact_phone=p_ph,
            address=p_addr
        )
        waste_db.add(plant)
    waste_db.commit()

    # 5. 24 Smart Collection Trucks
    driver_names = [
        "M. Selvam", "R. Arumugam", "S. Murugan", "T. Vijay", "K. Anbarasan", "V. Manikandan",
        "P. Karthik", "G. Venkatesh", "B. Balaji", "D. Dinesh", "A. Jayakumar", "M. Saravanan",
        "R. Thangaraj", "S. Senthil", "C. Prakash", "E. Ramesh", "N. Suresh", "L. Natarajan",
        "K. Ravi", "J. Mohan", "V. Sridhar", "P. Ganesan", "T. Elangovan", "M. Palani"
    ]
    vehicles = []
    for i in range(1, 25):
        code = f"GC-{i:02d}"
        assigned_ward = random.randint(1, 200)
        w_obj = waste_db.query(Ward).filter(Ward.ward_number == assigned_ward).first()
        lat = w_obj.latitude + random.uniform(-0.005, 0.005) if w_obj else 13.0827
        lng = w_obj.longitude + random.uniform(-0.005, 0.005) if w_obj else 80.2707

        v = CollectionVehicle(
            vehicle_code=code,
            vehicle_type="Smart Compactor Truck (IoT + AI Camera)",
            registration_no=f"TN-01-GCC-{1000 + i}",
            driver_name=driver_names[i - 1],
            driver_phone=f"+91 98400 {20000 + i}",
            capacity_tons=5.0,
            current_fill_pct=round(random.uniform(25.0, 92.0), 1),
            battery_or_fuel_pct=round(random.uniform(55.0, 98.0), 1),
            status=random.choice(["collecting", "collecting", "in_transit", "collecting", "unloading"]),
            latitude=round(lat, 4),
            longitude=round(lng, 4),
            assigned_zone_id=w_obj.zone_id if w_obj else 5,
            assigned_ward_id=assigned_ward,
            assigned_route=f"Sector {i} - Route {chr(65 + (i % 6))}",
            current_speed_kmh=round(random.uniform(12.0, 26.0), 1),
            last_ping=datetime.now(timezone.utc),
            camera_status="Active - Streaming AI Feed"
        )
        vehicles.append(v)
    waste_db.add_all(vehicles)
    waste_db.commit()

    # 6. AI Model Registry
    models = [
        AIModelVersion(
            model_name="GCC-WasteVision-YOLO",
            version="v2.1",
            status="production",
            framework="PyTorch 2.2 / YOLOv8-Waste",
            accuracy=0.894,
            precision=0.882,
            recall=0.865,
            f1_score=0.871,
            training_images_count=12400,
            training_date=datetime.now(timezone.utc) - timedelta(days=28),
            dataset_version="GCC-DS-2026.1",
            is_active_production=True,
            class_metrics_json=json.dumps({
                "Plastic": {"accuracy": 0.91, "f1": 0.89},
                "Organic Waste": {"accuracy": 0.86, "f1": 0.84},
                "E-Waste": {"accuracy": 0.85, "f1": 0.83}
            })
        ),
        AIModelVersion(
            model_name="GCC-WasteVision-MobileNet",
            version="v2.2-candidate",
            status="candidate",
            framework="PyTorch 2.2 / MobileNetV3-Waste",
            accuracy=0.923,
            precision=0.918,
            recall=0.912,
            f1_score=0.915,
            training_images_count=16500,
            training_date=datetime.now(timezone.utc) - timedelta(days=2),
            dataset_version="GCC-DS-2026.2",
            is_active_production=False
        )
    ]
    waste_db.add_all(models)
    waste_db.commit()

    # 7. Realistic Synthetic Waste Operations Records (Labeled Provenance)
    simulation_run_id = "GCC-INIT-SEED-2026"
    now = datetime.now(timezone.utc)
    waste_records = []
    for d in range(14, 0, -1):
        record_date = now - timedelta(days=d)
        for w_id in [102, 105, 82, 85, 112, 114, 170, 175, 32, 38]:
            waste_records.append(WasteRecord(
                ward_id=w_id,
                category_id=1, # Organic
                quantity_kg=round(random.uniform(1200.0, 3400.0), 1),
                segregation_status="Segregated",
                timestamp=record_date,
                data_source="simulation",
                data_type="SIMULATED DATA"
            ))
            waste_records.append(WasteRecord(
                ward_id=w_id,
                category_id=3, # Plastic
                quantity_kg=round(random.uniform(300.0, 950.0), 1),
                segregation_status="Segregated",
                timestamp=record_date,
                data_source="simulation",
                data_type="SIMULATED DATA"
            ))
    waste_db.add_all(waste_records)
    waste_db.commit()

    # 8. Weighbridge Records at Processing Facilities
    weigh_records = []
    for plant_id in [1, 2, 3, 5]:
        p = waste_db.query(SegregationPlant).filter(SegregationPlant.id == plant_id).first()
        if p:
            for k in range(5):
                gross = round(random.uniform(7.5, 12.0), 2)
                tare = round(random.uniform(4.5, 5.5), 2)
                weigh_records.append(WeighbridgeRecord(
                    facility_id=p.id,
                    facility_name=p.name,
                    vehicle_code=f"GC-{(k % 24) + 1:02d}",
                    gross_weight_tons=gross,
                    tare_weight_tons=tare,
                    net_weight_tons=round(gross - tare, 2),
                    primary_waste_category="Mixed Waste",
                    source_ward_number=random.randint(1, 200),
                    is_simulated=True,
                    data_source="simulation",
                    timestamp=now - timedelta(hours=k*3)
                ))
    waste_db.add_all(weigh_records)
    waste_db.commit()

    # 9. Public Grievances (Sanitation Complaints)
    complaints = [
        PublicComplaint(
            complaint_code="GCC-SAN-2026-001",
            category="Overflowing bins",
            description="Public bin near Anna Nagar 2nd Avenue bus stop is overflowing onto the pedestrian pathway.",
            location_name="2nd Avenue, Near Roundtana, Anna Nagar",
            ward_number=102,
            zone_number=8,
            latitude=13.0850,
            longitude=80.2100,
            citizen_name="S. Sundaram",
            citizen_phone="+91 98401 22334",
            priority="High",
            assigned_department="Solid Waste Management",
            assigned_staff_name="S. Jayaraman (Sanitary Inspector)",
            status="In Progress",
            is_simulated=True,
            data_source="simulation",
            created_at=now - timedelta(hours=6)
        ),
        PublicComplaint(
            complaint_code="GCC-SAN-2026-002",
            category="Missed garbage collection",
            description="Door-to-door waste collection truck did not visit 4th Street this morning.",
            location_name="4th Cross Street, Besant Nagar",
            ward_number=175,
            zone_number=13,
            latitude=12.9980,
            longitude=80.2670,
            citizen_name="Priya Subramanian",
            citizen_phone="+91 98402 55667",
            priority="Medium",
            assigned_department="Solid Waste Management",
            assigned_staff_name="G. Anand (Ward Supervisor)",
            status="Assigned",
            is_simulated=True,
            data_source="simulation",
            created_at=now - timedelta(hours=4)
        ),
        PublicComplaint(
            complaint_code="GCC-SAN-2026-003",
            category="Illegal dumping",
            description="Commercial building debris dumped along vacant land plot.",
            location_name="Mount-Poonamallee Road, Porur",
            ward_number=152,
            zone_number=11,
            latitude=13.0380,
            longitude=80.1580,
            citizen_name="M. Karthikeyan",
            citizen_phone="+91 98403 99881",
            priority="Critical",
            assigned_department="Sanitation Operations",
            assigned_staff_name="Er. R. Kumar (Sanitary Officer)",
            status="Submitted",
            is_simulated=True,
            data_source="simulation",
            created_at=now - timedelta(hours=1)
        )
    ]
    waste_db.add_all(complaints)
    waste_db.commit()

    # 10. Operational Alerts
    alerts = [
        OperationalAlert(
            alert_code="ALT-2026-01",
            priority="Critical",
            category="Plant Capacity",
            location_name="Perungudi Solid Waste Processing Center",
            ward_number=170,
            issue="Intake capacity reached 84% (2180 TPD of 2600 TPD max). Rerouting recommended.",
            recommended_action="Divert incoming compaction trucks from Zone 13 & 14 to Pallikaranai MRF.",
            status="Active"
        ),
        OperationalAlert(
            alert_code="ALT-2026-02",
            priority="High",
            category="Segregation",
            location_name="Ward 38 (Kodungaiyur East)",
            ward_number=38,
            issue="Segregation efficiency dropped below 40% threshold for three consecutive collection shifts.",
            recommended_action="Deploy Ward Sanitation Outreach team and issue notices to commercial establishments.",
            status="Active"
        )
    ]
    waste_db.add_all(alerts)
    waste_db.commit()

    # 11. IoT Devices & Telemetry
    devices = [
        IoTDevice(device_id="BIN-ZONE8-01", device_type="smart_bin", name="Anna Nagar Metro Smart Bin", ward_number=102, zone_number=8, status="online", battery_level=88.0, is_simulated=True),
        IoTDevice(device_id="BIN-ZONE13-01", device_type="smart_bin", name="Besant Nagar Beach Smart Bin", ward_number=175, zone_number=13, status="online", battery_level=94.0, is_simulated=True),
        IoTDevice(device_id="TRUCK-GC01", device_type="vehicle_tracker", name="GC-01 Fleet Telemetry Unit", ward_number=102, zone_number=8, status="online", battery_level=98.0, is_simulated=True)
    ]
    waste_db.add_all(devices)
    waste_db.commit()

    telemetry = [
        DeviceTelemetry(device_id="BIN-ZONE8-01", latitude=13.0850, longitude=80.2100, bin_fill_pct=72.5, temperature_c=31.2, is_simulated=True, data_source="simulation"),
        DeviceTelemetry(device_id="BIN-ZONE13-01", latitude=12.9980, longitude=80.2670, bin_fill_pct=45.0, temperature_c=30.8, is_simulated=True, data_source="simulation"),
        DeviceTelemetry(device_id="TRUCK-GC01", latitude=13.0827, longitude=80.2707, speed_kmh=22.4, battery_pct=98.0, is_simulated=True, data_source="simulation")
    ]
    waste_db.add_all(telemetry)
    waste_db.commit()

    # 12. Simulation Run State
    sim_run = SimulationRun(
        simulation_run_id=simulation_run_id,
        status="running" if settings.SIMULATION_MODE else "stopped",
        tick_interval_seconds=settings.SIMULATION_TICK_SECONDS,
        events_generated=150,
        last_tick_at=now
    )
    waste_db.add(sim_run)
    waste_db.commit()

def seed_all_databases():
    """Master seeding function: creates tables and seeds all three distinct databases."""
    init_all_tables()

    user_db = UserSessionLocal()
    staff_db = StaffSessionLocal()
    waste_db = WasteSessionLocal()

    try:
        seed_database_a(user_db)
        seed_database_b(staff_db, user_db)
        waste_db = WasteSessionLocal()
        seed_database_c(waste_db)
        logger.info("Successfully completed multi-database initialization and realistic synthetic seeding.")
    except Exception as e:
        logger.error(f"Error during multi-database seeding: {e}")
        raise e
    finally:
        user_db.close()
        staff_db.close()
        waste_db.close()

# Backward compatibility alias
seed_database = lambda db: seed_all_databases()
