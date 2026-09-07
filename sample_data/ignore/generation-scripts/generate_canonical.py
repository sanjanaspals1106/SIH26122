import csv
import os

BASE_DIR = r"D:\SIH26122\sample_data"
CANONICAL_DIR = os.path.join(BASE_DIR, "canonical")
INPUT_XER_DIR = os.path.join(BASE_DIR, "input", "schedule-xer")

os.makedirs(CANONICAL_DIR, exist_ok=True)
os.makedirs(INPUT_XER_DIR, exist_ok=True)

# 45 Activities Across 6 Disciplines
# Civil (8), Piping (10), Static/Rotating Equipment (7), Electrical (8), Instrumentation (7), HSE (5)
ACTIVITIES = [
    # Civil (8)
    {
        "Activity_ID": "CIV-PS3-TR-0180",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.01",
        "Discipline": "Civil",
        "Activity_Name": "Utility Trench Excavation CH 0+180 to CH 0+220",
        "Description": "Excavation of utility corridor trench section CH 0+180 to CH 0+220",
        "Location": "Pump Station 3",
        "Asset_Tag": "TR-0180",
        "Planned_Quantity": 40.0,
        "Unit": "m",
        "Planned_Start": "2026-08-14",
        "Planned_Finish": "2026-08-14",
        "Status": "Complete",
        "Responsible_Role": "Civil Supervisor",
        "Inspection_Hold_Point": "Trench depth and invert level check",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "CIV-PS3-TR-0220",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.02",
        "Discipline": "Civil",
        "Activity_Name": "Utility Trench Excavation CH 0+220 to CH 0+260",
        "Description": "Excavation of utility corridor trench section CH 0+220 to CH 0+260",
        "Location": "Pump Station 3",
        "Asset_Tag": "TR-0220",
        "Planned_Quantity": 40.0,
        "Unit": "m",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "Civil Supervisor",
        "Inspection_Hold_Point": "Trench depth and invert level check",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "CIV-PS3-FND-001",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.03",
        "Discipline": "Civil",
        "Activity_Name": "Pump P-101/P-102 Foundation Blinding",
        "Description": "Soil excavation and lean concrete blinding for crude pump base",
        "Location": "Pump Station 3",
        "Asset_Tag": "FND-P101",
        "Planned_Quantity": 65.0,
        "Unit": "m3",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-13",
        "Status": "Complete",
        "Responsible_Role": "Civil QC Inspector",
        "Inspection_Hold_Point": "Bearing capacity soil test",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "CIV-PS3-FND-002",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.04",
        "Discipline": "Civil",
        "Activity_Name": "Pump P-101/P-102 Rebar & Formwork",
        "Description": "Rebar fixing, embedded anchor bolts, and shuttering for pump base",
        "Location": "Pump Station 3",
        "Asset_Tag": "FND-P101",
        "Planned_Quantity": 12.0,
        "Unit": "t",
        "Planned_Start": "2026-08-14",
        "Planned_Finish": "2026-08-18",
        "Status": "Complete",
        "Responsible_Role": "Civil Supervisor",
        "Inspection_Hold_Point": "Pre-pour rebar and anchor alignment check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "CIV-PS3-FND-003",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.05",
        "Discipline": "Civil",
        "Activity_Name": "Pump P-101/P-102 Foundation Concrete Pour",
        "Description": "Grade 40 concrete pouring and wet burlap curing for pump foundation",
        "Location": "Pump Station 3",
        "Asset_Tag": "FND-P101",
        "Planned_Quantity": 60.0,
        "Unit": "m3",
        "Planned_Start": "2026-08-19",
        "Planned_Finish": "2026-08-21",
        "Status": "Complete",
        "Responsible_Role": "Civil Lead",
        "Inspection_Hold_Point": "Concrete slump and cube sampling",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "CIV-PS3-DRN-001",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.06",
        "Discipline": "Civil",
        "Activity_Name": "Stormwater Drainage Channel Installation",
        "Description": "Precast concrete U-drain channel placement Section A",
        "Location": "Pump Station 3",
        "Asset_Tag": "DRN-001",
        "Planned_Quantity": 120.0,
        "Unit": "m",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-20",
        "Status": "Ongoing",
        "Responsible_Role": "Civil Supervisor",
        "Inspection_Hold_Point": "Slope and invert elevation check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "CIV-PS3-RD-001",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.07",
        "Discipline": "Civil",
        "Activity_Name": "Road Crossing Duct Bank Encasement",
        "Description": "Excavation, duct laying, and concrete encasement across perimeter road",
        "Location": "Perimeter Road",
        "Asset_Tag": "RD-001",
        "Planned_Quantity": 50.0,
        "Unit": "m",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Civil Supervisor",
        "Inspection_Hold_Point": "Mandrel pull test through ducts",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "CIV-PS3-BKF-001",
        "Parent_ID": "WBS-CIV",
        "WBS": "1.01.08",
        "Discipline": "Civil",
        "Activity_Name": "Trench Backfill & Compaction CH 0+000-0+180",
        "Description": "Layer-by-layer select soil backfill and vibratory plate compaction",
        "Location": "Pump Station 3",
        "Asset_Tag": "BKF-001",
        "Planned_Quantity": 350.0,
        "Unit": "m3",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Civil QC Inspector",
        "Inspection_Hold_Point": "Nuclear density compaction test 95% MDD",
        "Safety_Critical": "No"
    },

    # Piping (10)
    {
        "Activity_ID": "PIP-PS3-WLD-024",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.01",
        "Discipline": "Piping",
        "Activity_Name": "Utility Header Field Weld Joints",
        "Description": "Complete field weld joints for 16-inch utility header",
        "Location": "Pump Station 3",
        "Asset_Tag": "P-102",
        "Planned_Quantity": 24.0,
        "Unit": "joints",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-15",
        "Status": "Complete",
        "Responsible_Role": "Welding Inspector",
        "Inspection_Hold_Point": "100% Visual Testing and 20% Radiographic Testing",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "PIP-PS3-HDR-100",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.02",
        "Discipline": "Piping",
        "Activity_Name": "Above Ground Utility Header Fabrication",
        "Description": "Complete fabrication and erection of utility header line",
        "Location": "Pump Station 3",
        "Asset_Tag": "HDR-100",
        "Planned_Quantity": 100.0,
        "Unit": "m",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Piping Superintendent",
        "Inspection_Hold_Point": "Line walk and punch list clearing",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-HDR-100-A",
        "Parent_ID": "PIP-PS3-HDR-100",
        "WBS": "1.02.02.01",
        "Discipline": "Piping",
        "Activity_Name": "Utility Header Spool Section A",
        "Description": "Spool placement, fit-up and tack welding for Section A",
        "Location": "Pump Station 3",
        "Asset_Tag": "HDR-100-A",
        "Planned_Quantity": 40.0,
        "Unit": "m",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "Piping Supervisor",
        "Inspection_Hold_Point": "Fit-up inspection",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-HDR-100-B",
        "Parent_ID": "PIP-PS3-HDR-100",
        "WBS": "1.02.02.02",
        "Discipline": "Piping",
        "Activity_Name": "Utility Header Spool Section B",
        "Description": "Spool placement, fit-up and tack welding for Section B",
        "Location": "Pump Station 3",
        "Asset_Tag": "HDR-100-B",
        "Planned_Quantity": 30.0,
        "Unit": "m",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-19",
        "Status": "Ongoing",
        "Responsible_Role": "Piping Supervisor",
        "Inspection_Hold_Point": "Fit-up inspection",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-HDR-100-C",
        "Parent_ID": "PIP-PS3-HDR-100",
        "WBS": "1.02.02.03",
        "Discipline": "Piping",
        "Activity_Name": "Utility Header Spool Section C",
        "Description": "Spool placement, fit-up and tack welding for Section C",
        "Location": "Pump Station 3",
        "Asset_Tag": "HDR-100-C",
        "Planned_Quantity": 30.0,
        "Unit": "m",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Piping Supervisor",
        "Inspection_Hold_Point": "Fit-up inspection",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-SPO-015",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.03",
        "Discipline": "Piping",
        "Activity_Name": "Firewater Line Spool Placement",
        "Description": "Underground carbon steel firewater ringmain spool installation",
        "Location": "Pump Station 3",
        "Asset_Tag": "FW-SPO-015",
        "Planned_Quantity": 80.0,
        "Unit": "m",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-15",
        "Status": "Complete",
        "Responsible_Role": "Piping Supervisor",
        "Inspection_Hold_Point": "Holiday detection coating test",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "PIP-PS3-HYD-001",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.04",
        "Discipline": "Piping",
        "Activity_Name": "Hydrostatic Pressure Test Firewater Sector 1",
        "Description": "Pressure test firewater loop sector 1 to 24 bar for 4 hours",
        "Location": "Pump Station 3",
        "Asset_Tag": "FW-LOOP-01",
        "Planned_Quantity": 1.0,
        "Unit": "test",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-19",
        "Status": "Complete",
        "Responsible_Role": "QC Manager",
        "Inspection_Hold_Point": "Client pressure hold sign-off",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "PIP-PS3-VLV-005",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.05",
        "Discipline": "Piping",
        "Activity_Name": "12-inch Gate Valve Installation",
        "Description": "Rigging, gasket placement, and flange bolt torqueing for gate valves",
        "Location": "Pump Station 3",
        "Asset_Tag": "VLV-12-005",
        "Planned_Quantity": 8.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-19",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Piping Supervisor",
        "Inspection_Hold_Point": "Torque wrench calibration and tightening check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-SPT-030",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.06",
        "Discipline": "Piping",
        "Activity_Name": "Pipe Support Secondary Steel Erection",
        "Description": "Fabrication, welding, and erection of secondary pipe support brackets",
        "Location": "Pump Station 3",
        "Asset_Tag": "SPT-030",
        "Planned_Quantity": 100.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-13",
        "Planned_Finish": "2026-08-21",
        "Status": "Ongoing",
        "Responsible_Role": "Structural/Piping Supervisor",
        "Inspection_Hold_Point": "Support elevation and plumbness check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "PIP-PS3-TIE-002",
        "Parent_ID": "WBS-PIP",
        "WBS": "1.02.07",
        "Discipline": "Piping",
        "Activity_Name": "Tie-in Spool Fit-up Manifold M-01",
        "Description": "Flange alignment and bolt-up for tie-in spool to existing manifold M-01",
        "Location": "Manifold M-01",
        "Asset_Tag": "M-01",
        "Planned_Quantity": 4.0,
        "Unit": "joints",
        "Planned_Start": "2026-08-21",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Senior Piping Engineer",
        "Inspection_Hold_Point": "Flange parallelism and gap inspection",
        "Safety_Critical": "Yes"
    },

    # Static/Rotating Equipment (7)
    {
        "Activity_ID": "MECH-PS3-DWP-003",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.01",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Dewatering Pump Relocation",
        "Description": "Relocate submersible dewatering pump after water ingress",
        "Location": "Pump Station 3",
        "Asset_Tag": "DWP-003",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-14",
        "Planned_Finish": "2026-08-14",
        "Status": "Complete",
        "Responsible_Role": "Mechanical Supervisor",
        "Inspection_Hold_Point": "Pump discharge hose and electrical isolation check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "EQP-PS3-PMP-101",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.02",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Crude Pump P-101 Baseplate Grouting",
        "Description": "Non-shrink epoxy grouting of baseplate for Crude Transfer Pump P-101",
        "Location": "Pump Station 3",
        "Asset_Tag": "P-101",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-20",
        "Status": "Complete",
        "Responsible_Role": "Mechanical QC Inspector",
        "Inspection_Hold_Point": "Grout flowability and void tap test",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "EQP-PS3-PMP-102",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.03",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Crude Pump P-102 Positioning & Alignment",
        "Description": "Rigging, leveling, and laser shaft alignment for Crude Transfer Pump P-102",
        "Location": "Pump Station 3",
        "Asset_Tag": "P-102",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-19",
        "Planned_Finish": "2026-08-21",
        "Status": "Complete",
        "Responsible_Role": "Millwright Specialist",
        "Inspection_Hold_Point": "Cold laser alignment tolerance (+/- 0.05 mm)",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "EQP-PS3-TK-001",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.04",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Sump Tank TK-01 Internal Inspection",
        "Description": "Confined space entry, cleaning, and internal nozzle inspection for TK-01",
        "Location": "Sump Area",
        "Asset_Tag": "TK-01",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-15",
        "Status": "Complete",
        "Responsible_Role": "Mechanical Inspector",
        "Inspection_Hold_Point": "Internal vessel cleanliness and coating acceptance",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "EQP-PS3-SKD-002",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.05",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Chemical Dosing Skid SK-02 Positioning",
        "Description": "Crane offloading, skid positioning, and anchor bolt torquing",
        "Location": "Chemical Area",
        "Asset_Tag": "SK-02",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-18",
        "Status": "Complete",
        "Responsible_Role": "Mechanical Supervisor",
        "Inspection_Hold_Point": "Skid elevation and orientation sign-off",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "EQP-PS3-AIR-001",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.06",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Air Receiver Vessel V-103 Erection",
        "Description": "Vertical vessel crane erection and anchor tightening on foundation",
        "Location": "Utility Bay",
        "Asset_Tag": "V-103",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-13",
        "Planned_Finish": "2026-08-15",
        "Status": "Complete",
        "Responsible_Role": "Rigging Supervisor",
        "Inspection_Hold_Point": "Verticality plumb check and anchor bolt torque",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "EQP-PS3-GEN-001",
        "Parent_ID": "WBS-EQP",
        "WBS": "1.03.07",
        "Discipline": "Static/Rotating Equipment",
        "Activity_Name": "Diesel Generator DG-01 Installation",
        "Description": "Standby diesel generator DG-01 positioning on acoustic plinth",
        "Location": "Generator Bay",
        "Asset_Tag": "DG-01",
        "Planned_Quantity": 1.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-20",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Mechanical Lead",
        "Inspection_Hold_Point": "Vibration damper pad positioning check",
        "Safety_Critical": "No"
    },

    # Electrical (8)
    {
        "Activity_ID": "ELE-PS3-CT-011",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.01",
        "Discipline": "Electrical",
        "Activity_Name": "Cable Trench Bedding at MCC-02",
        "Description": "Place sieved sand bedding in electrical cable trench at MCC-02",
        "Location": "MCC Building",
        "Asset_Tag": "MCC-02",
        "Planned_Quantity": 160.0,
        "Unit": "m",
        "Planned_Start": "2026-08-10",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "Electrical Supervisor",
        "Inspection_Hold_Point": "Sand layer thickness 100mm verification",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "ELE-PS3-CT-012",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.02",
        "Discipline": "Electrical",
        "Activity_Name": "Cable Trench Bedding at MCC-01",
        "Description": "Place sieved sand bedding in electrical cable trench at MCC-01",
        "Location": "MCC Building",
        "Asset_Tag": "MCC-01",
        "Planned_Quantity": 140.0,
        "Unit": "m",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-17",
        "Status": "Complete",
        "Responsible_Role": "Electrical Supervisor",
        "Inspection_Hold_Point": "Sand layer thickness 100mm verification",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "ELE-PS3-CBL-001",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.03",
        "Discipline": "Electrical",
        "Activity_Name": "11kV Medium Voltage Cable Pulling",
        "Description": "Pull 11kV 3C 300sqmm XLPE power cable from Substation to MCC-02",
        "Location": "Substation",
        "Asset_Tag": "MV-CBL-01",
        "Planned_Quantity": 500.0,
        "Unit": "m",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-18",
        "Status": "Delayed",
        "Responsible_Role": "Electrical Lead",
        "Inspection_Hold_Point": "Cable pulling tension record and insulation test",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "ELE-PS3-CBL-002",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.04",
        "Discipline": "Electrical",
        "Activity_Name": "415V Low Voltage Auxiliary Cable Pulling",
        "Description": "Pull 415V 4C 70sqmm copper power cables for auxiliary pumps",
        "Location": "Pump Station 3",
        "Asset_Tag": "LV-CBL-02",
        "Planned_Quantity": 450.0,
        "Unit": "m",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Electrical Supervisor",
        "Inspection_Hold_Point": "Cable insulation resistance megger check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "ELE-PS3-TR-005",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.05",
        "Discipline": "Electrical",
        "Activity_Name": "Cable Tray Installation Piperack Tier 2",
        "Description": "Erection and grounding of 600mm perforated GI cable trays",
        "Location": "Piperack PR-01",
        "Asset_Tag": "TR-005",
        "Planned_Quantity": 200.0,
        "Unit": "m",
        "Planned_Start": "2026-08-14",
        "Planned_Finish": "2026-08-20",
        "Status": "Ongoing",
        "Responsible_Role": "Electrical Supervisor",
        "Inspection_Hold_Point": "Tray continuity and bonding jumper inspection",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "ELE-PS3-EAR-001",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.06",
        "Discipline": "Electrical",
        "Activity_Name": "Earth Pit Grid Installation",
        "Description": "Excavation, copper clad rod driving, and bare copper earth tape grid",
        "Location": "Substation Yard",
        "Asset_Tag": "EAR-001",
        "Planned_Quantity": 24.0,
        "Unit": "pits",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "Electrical QC Inspector",
        "Inspection_Hold_Point": "Earth resistance test (< 1.0 Ohm)",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "ELE-PS3-LGT-002",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.07",
        "Discipline": "Electrical",
        "Activity_Name": "High Mast Lighting Wiring & Conduits",
        "Description": "Heavy duty GI conduit installation and cabling for lighting poles",
        "Location": "Yard Area",
        "Asset_Tag": "LGT-002",
        "Planned_Quantity": 6.0,
        "Unit": "poles",
        "Planned_Start": "2026-08-19",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Electrical Supervisor",
        "Inspection_Hold_Point": "Circuit continuity and earthing check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "ELE-PS3-SWG-001",
        "Parent_ID": "WBS-ELE",
        "WBS": "1.04.08",
        "Discipline": "Electrical",
        "Activity_Name": "11kV Switchgear Panel Positioning",
        "Description": "Uncrating, visual inspection, and positioning of 11kV vacuum switchgear panels",
        "Location": "Substation",
        "Asset_Tag": "SWG-001",
        "Planned_Quantity": 8.0,
        "Unit": "panels",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-19",
        "Status": "Complete",
        "Responsible_Role": "Electrical Engineer",
        "Inspection_Hold_Point": "Panel base frame alignment and torqueing",
        "Safety_Critical": "Yes"
    },

    # Instrumentation (7)
    {
        "Activity_ID": "INS-PS3-JB-001",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.01",
        "Discipline": "Instrumentation",
        "Activity_Name": "Field Junction Box Installation",
        "Description": "Wall and stanchion mounting of SS316 field junction boxes JB-101 to 112",
        "Location": "Pump Station 3",
        "Asset_Tag": "JB-101",
        "Planned_Quantity": 12.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "Instrumentation Supervisor",
        "Inspection_Hold_Point": "Ingress protection (IP66) gasket check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "INS-PS3-ITR-002",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.02",
        "Discipline": "Instrumentation",
        "Activity_Name": "Instrument Cable Tray Installation",
        "Description": "Installation of 300mm ladder type cable tray with cover",
        "Location": "Piperack PR-01",
        "Asset_Tag": "ITR-002",
        "Planned_Quantity": 180.0,
        "Unit": "m",
        "Planned_Start": "2026-08-13",
        "Planned_Finish": "2026-08-18",
        "Status": "Complete",
        "Responsible_Role": "Instrumentation Supervisor",
        "Inspection_Hold_Point": "Tray separation from power cables (> 300mm)",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "INS-PS3-CBL-004",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.03",
        "Discipline": "Instrumentation",
        "Activity_Name": "Signal & Thermocouple Cable Pulling",
        "Description": "Pull multi-pair screened instrumentation signal cables to control room",
        "Location": "Control Room",
        "Asset_Tag": "INS-CBL-04",
        "Planned_Quantity": 600.0,
        "Unit": "m",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Instrumentation Supervisor",
        "Inspection_Hold_Point": "Shield grounding and loop resistance check",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "INS-PS3-PT-021",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.04",
        "Discipline": "Instrumentation",
        "Activity_Name": "Pressure Transmitter Mounting & Impulse Piping",
        "Description": "2-inch pipe stanchion mounting and 1/2-inch SS tubing impulse lines",
        "Location": "Pump Station 3",
        "Asset_Tag": "PT-1021",
        "Planned_Quantity": 6.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-19",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Instrumentation Technician",
        "Inspection_Hold_Point": "Impulse tubing pressure test at 1.5x design pressure",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "INS-PS3-FT-010",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.05",
        "Discipline": "Instrumentation",
        "Activity_Name": "Ultrasonic Flowmeter Spool Installation",
        "Description": "In-line mounting and transducer fitting for flowmeters FT-201/202",
        "Location": "Pump Station 3",
        "Asset_Tag": "FT-201",
        "Planned_Quantity": 2.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-20",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Instrumentation Engineer",
        "Inspection_Hold_Point": "Transducer acoustic signal coupling test",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "INS-PS3-FGS-001",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.06",
        "Discipline": "Instrumentation",
        "Activity_Name": "Fire & Gas Detector Mounting",
        "Description": "Installation of optical flame detectors and toxic gas sensors",
        "Location": "Process Area",
        "Asset_Tag": "FGS-001",
        "Planned_Quantity": 16.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-18",
        "Planned_Finish": "2026-08-22",
        "Status": "Not Started",
        "Responsible_Role": "F&G Specialist",
        "Inspection_Hold_Point": "Detector cone of vision and sensor zero check",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "INS-PS3-CAL-003",
        "Parent_ID": "WBS-INS",
        "WBS": "1.05.07",
        "Discipline": "Instrumentation",
        "Activity_Name": "Control Valve Bench Calibration",
        "Description": "Pre-commissioning stroke test and smart positioner calibration",
        "Location": "Instrument Workshop",
        "Asset_Tag": "FCV-101",
        "Planned_Quantity": 10.0,
        "Unit": "ea",
        "Planned_Start": "2026-08-21",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "QC Instrument Inspector",
        "Inspection_Hold_Point": "5-point calibration hysterisis check (0, 25, 50, 75, 100%)",
        "Safety_Critical": "Yes"
    },

    # HSE (5)
    {
        "Activity_ID": "HSE-PS3-IND-001",
        "Parent_ID": "WBS-HSE",
        "WBS": "1.06.01",
        "Discipline": "HSE",
        "Activity_Name": "Daily Site Safety Induction & Toolbox Talks",
        "Description": "Mandatory morning toolbox talks, hazard awareness, and PPE checks",
        "Location": "Site Wide",
        "Asset_Tag": "HSE-IND",
        "Planned_Quantity": 10.0,
        "Unit": "days",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "HSE Officer",
        "Inspection_Hold_Point": "Toolbox attendance sheet and permit verification",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "HSE-PS3-BAR-002",
        "Parent_ID": "WBS-HSE",
        "WBS": "1.06.02",
        "Discipline": "HSE",
        "Activity_Name": "Deep Excavation Hard Barricading",
        "Description": "Erection of rigid scaffolding tube barricades and warning signage around trenches",
        "Location": "Trench Zone",
        "Asset_Tag": "HSE-BAR",
        "Planned_Quantity": 300.0,
        "Unit": "m",
        "Planned_Start": "2026-08-11",
        "Planned_Finish": "2026-08-16",
        "Status": "Complete",
        "Responsible_Role": "HSE Supervisor",
        "Inspection_Hold_Point": "Toe board and 1m handrail stability check",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "HSE-PS3-GAS-001",
        "Parent_ID": "WBS-HSE",
        "WBS": "1.06.03",
        "Discipline": "HSE",
        "Activity_Name": "Confined Space Atmospheric Gas Monitoring",
        "Description": "Multi-gas detector air sampling (LEL, O2, H2S, CO) for confined entries",
        "Location": "Sump / Trench",
        "Asset_Tag": "HSE-GAS",
        "Planned_Quantity": 40.0,
        "Unit": "checks",
        "Planned_Start": "2026-08-14",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "Certified Gas Tester",
        "Inspection_Hold_Point": "Gas entry permit gas test sign-off (< 10% LEL, 19.5-23.5% O2)",
        "Safety_Critical": "Yes"
    },
    {
        "Activity_ID": "HSE-PS3-WST-003",
        "Parent_ID": "WBS-HSE",
        "WBS": "1.06.04",
        "Discipline": "HSE",
        "Activity_Name": "Hazardous Chemical Waste Storage & Manifesting",
        "Description": "Safe disposal logging, secondary containment, and waste manifest",
        "Location": "Waste Storage",
        "Asset_Tag": "HSE-WST",
        "Planned_Quantity": 12.0,
        "Unit": "bins",
        "Planned_Start": "2026-08-12",
        "Planned_Finish": "2026-08-21",
        "Status": "Ongoing",
        "Responsible_Role": "Environmental Specialist",
        "Inspection_Hold_Point": "Spill kit availability and secondary containment integrity",
        "Safety_Critical": "No"
    },
    {
        "Activity_ID": "HSE-PS3-AUD-001",
        "Parent_ID": "WBS-HSE",
        "WBS": "1.06.05",
        "Discipline": "HSE",
        "Activity_Name": "Weekly Environmental Compliance Audit",
        "Description": "Site spill prevention, erosion control, and environmental inspection audit",
        "Location": "Site Wide",
        "Asset_Tag": "HSE-AUD",
        "Planned_Quantity": 2.0,
        "Unit": "audits",
        "Planned_Start": "2026-08-15",
        "Planned_Finish": "2026-08-22",
        "Status": "Ongoing",
        "Responsible_Role": "HSE Manager",
        "Inspection_Hold_Point": "Client joint weekly walk inspection",
        "Safety_Critical": "No"
    }
]

def write_canonical_schedule():
    sched_file = os.path.join(CANONICAL_DIR, "schedule.csv")
    fieldnames = [
        "Activity_ID", "Parent_ID", "WBS", "Discipline", "Activity_Name",
        "Description", "Location", "Asset_Tag", "Planned_Quantity", "Unit",
        "Planned_Start", "Planned_Finish", "Status"
    ]
    with open(sched_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for act in ACTIVITIES:
            row = {k: act[k] for k in fieldnames}
            writer.writerow(row)
    print(f"Written {len(ACTIVITIES)} activities to {sched_file}")

def write_activity_master():
    master_file = os.path.join(CANONICAL_DIR, "activity_master.csv")
    fieldnames = [
        "Activity_ID", "Parent_ID", "WBS", "Discipline", "Activity_Name",
        "Description", "Location", "Asset_Tag", "Planned_Quantity", "Unit",
        "Planned_Start", "Planned_Finish", "Status",
        "Responsible_Role", "Inspection_Hold_Point", "Safety_Critical"
    ]
    with open(master_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for act in ACTIVITIES:
            writer.writerow(act)
    print(f"Written {len(ACTIVITIES)} activities to {master_file}")

def write_sih26122_xer():
    xer_file = os.path.join(INPUT_XER_DIR, "sih26122_schedule.xer")
    lines = []
    lines.append("ERMHDR\t19.12\t2026-08-10\tProject\tadmin\tSIH26122_Planner\tNORTH_FIELD_CORRIDOR\tUSD\tDD/MM/YYYY\t1\t0\t0")
    lines.append("%T\tPROJECT")
    lines.append("%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date")
    lines.append("%R\t1\tSIH26122_NFU\t2026-08-10 08:00\t2026-08-22 18:00")
    
    lines.append("%T\tPROJWBS")
    lines.append("%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name")
    wbs_map = {
        "WBS-ROOT": ("100", "", "1", "North Field Utility Corridor"),
        "WBS-CIV": ("101", "100", "1.01", "Civil Works"),
        "WBS-PIP": ("102", "100", "1.02", "Piping Works"),
        "WBS-EQP": ("103", "100", "1.03", "Static and Rotating Equipment"),
        "WBS-ELE": ("104", "100", "1.04", "Electrical Works"),
        "WBS-INS": ("105", "100", "1.05", "Instrumentation Works"),
        "WBS-HSE": ("106", "100", "1.06", "Health Safety Environment")
    }
    for k, (wid, pid, sname, wname) in wbs_map.items():
        lines.append(f"%R\t{wid}\t1\t{pid}\t{sname}\t{wname}")
    
    lines.append("%T\tTASK")
    lines.append("%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\tstatus_code\ttarget_drtn_hr_cnt\ttarget_start_date\ttarget_end_date\ttotal_float_hr_cnt\tcstr_type\tcstr_date")
    
    wbs_disc_map = {
        "Civil": "101",
        "Piping": "102",
        "Static/Rotating Equipment": "103",
        "Electrical": "104",
        "Instrumentation": "105",
        "HSE": "106"
    }
    
    for idx, act in enumerate(ACTIVITIES, start=2001):
        wid = wbs_disc_map[act["Discipline"]]
        code = act["Activity_ID"]
        name = act["Activity_Name"]
        status_map = {"Complete": "TK_Complete", "Ongoing": "TK_Active", "Delayed": "TK_Active", "Not Started": "TK_NotStart"}
        st = status_map.get(act["Status"], "TK_Active")
        start = f"{act['Planned_Start']} 08:00"
        finish = f"{act['Planned_Finish']} 18:00"
        lines.append(f"%R\t{idx}\t1\t{wid}\t{code}\t{name}\tTT_Task\t{st}\t80\t{start}\t{finish}\t0\t\t")
        
    lines.append("%E")
    
    with open(xer_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Written SIH26122 XER file to {xer_file}")

if __name__ == "__main__":
    write_canonical_schedule()
    write_activity_master()
    write_sih26122_xer()
