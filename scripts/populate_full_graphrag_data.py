#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import base64
import sys
import os
import random
from datetime import datetime, timedelta
from src.db.connection import get_connection

FHIR_BASE_URL = os.getenv('FHIR_BASE_URL', "http://localhost:32783/csp/healthshare/demo/fhir/r4")
FHIR_USERNAME = os.getenv('FHIR_USERNAME', "_SYSTEM")
FHIR_PASSWORD = os.getenv('FHIR_PASSWORD', "SYS")
IRIS_NAMESPACE = os.getenv('IRIS_NAMESPACE', '%SYS')
NUM_PATIENTS = 50

# Heuristic mapping for entity types
MEDICATIONS = {
    "metformin", "insulin glargine", "lisinopril", "amlodipine", "furosemide", 
    "carvedilol", "ceftriaxone", "azithromycin", "albuterol", "tiotropium", 
    "prednisone", "warfarin", "apixaban", "metoprolol", "aspirin", "atorvastatin", 
    "nitroglycerin", "levothyroxine", "loratadine", "cetirizine", "avoid penicillin"
}

CONDITIONS_LIST = [
    ("diabetes mellitus type 2", "Condition", ["metformin", "insulin glargine", "hyperglycemia", "neuropathy", "retinopathy"]),
    ("hypertension", "Condition", ["lisinopril", "amlodipine", "elevated blood pressure", "headache", "dizziness"]),
    ("congestive heart failure", "Condition", ["furosemide", "carvedilol", "shortness of breath", "peripheral edema", "fatigue"]),
    ("chronic kidney disease", "Condition", ["creatinine elevated", "proteinuria", "anemia", "fatigue", "fluid retention"]),
    ("pneumonia", "Condition", ["ceftriaxone", "azithromycin", "fever", "cough", "chest pain", "dyspnea"]),
    ("COPD", "Condition", ["albuterol", "tiotropium", "prednisone", "wheezing", "chronic cough", "dyspnea"]),
    ("atrial fibrillation", "Condition", ["warfarin", "apixaban", "metoprolol", "palpitations", "irregular heartbeat"]),
    ("coronary artery disease", "Condition", ["aspirin", "atorvastatin", "nitroglycerin", "chest pain", "angina"]),
    ("hypothyroidism", "Condition", ["levothyroxine", "fatigue", "weight gain", "cold intolerance"]),
    ("seasonal allergies", "Condition", ["loratadine", "cetirizine", "sneezing", "rhinitis", "itchy eyes"]),
    ("penicillin allergy", "Condition", ["hives", "rash", "anaphylaxis risk", "avoid penicillin"]),
]

IMAGING_FINDINGS = [
    ("No acute cardiopulmonary findings", "normal"),
    ("Mild cardiomegaly", "abnormal"),
    ("Clear lungs, no focal consolidation", "normal"),
    ("Bilateral pulmonary infiltrates", "abnormal"),
    ("Right lower lobe opacity concerning for pneumonia", "abnormal"),
    ("Pleural effusion, small bilateral", "abnormal"),
    ("No active disease", "normal"),
]

def generate_patients():
    patients = []
    first_m = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    first_f = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen"]
    last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    for i in range(1, NUM_PATIENTS + 1):
        gender = random.choice(["male", "female"])
        fname = random.choice(first_m if gender == "male" else first_f)
        lname = random.choice(last)
        bdate = f"{random.randint(1940, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        conds = random.sample(CONDITIONS_LIST, random.randint(1, 3))
        notes = []
        for j, (name, _, items) in enumerate(conds):
            text = f"Patient {fname} {lname} presents with {items[0]}. History of {name}. Plan: Follow up."
            notes.append({"id": f"note-p{i:03d}-{j+1}", "type": "Progress Note", "text": text, "name": name, "items": items})
        finding, ftype = random.choice(IMAGING_FINDINGS)
        patients.append({
            "id": str(i), "fname": fname, "lname": lname, "gender": gender, "bdate": bdate,
            "conds": conds, "notes": notes,
            "img": {"id": f"study-s{50414267 + i}", "finding": finding, "type": ftype, "date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat() + "Z"}
        })
    return patients

def put_resource(resource):
    url = f"{FHIR_BASE_URL}/{resource['resourceType']}/{resource['id']}"
    data = json.dumps(resource).encode("utf-8")
    auth = "Basic " + base64.b64encode(f"{FHIR_USERNAME}:{FHIR_PASSWORD}".encode()).decode()
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/fhir+json")
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, resp.getcode()
    except Exception as e:
        return False, str(e)

def main():
    print(f"Populating data for {NUM_PATIENTS} patients...")
    patients = generate_patients()
    
    print("Uploading FHIR Resources...")
    p_count = 0
    for p in patients:
        res, code = put_resource({"resourceType": "Patient", "id": p["id"], "name": [{"family": p["lname"], "given": [p["fname"]]}], "gender": p["gender"], "birthDate": p["bdate"]})
        if res: p_count += 1
        put_resource({"resourceType": "ImagingStudy", "id": p["img"]["id"], "status": "available", "subject": {"reference": f"Patient/{p['id']}"}, "started": p["img"]["date"], "modality": [{"code": "CR"}], "description": p["img"]["finding"]})
    print(f"✅ {p_count} Patients uploaded")

    print("Populating IRIS Tables...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        for t in ["SQLUser.FHIRDocuments", "VectorSearch.FHIRTextVectors", "RAG.Entities", "RAG.EntityRelationships"]:
            try: cur.execute(f"DELETE FROM {t}")
            except: pass
        
        e_count = 0
        r_count = 0
        for p in patients:
            for n in p["notes"]:
                res_str = json.dumps({"resourceType": "Composition", "id": n["id"], "status": "final", "text": {"div": n["text"]}})
                cur.execute("INSERT INTO SQLUser.FHIRDocuments (FHIRResourceId, ResourceType, TextContent, ResourceString, CreatedAt) VALUES (?, ?, ?, ?, NOW())", (n["id"], n["type"], n["text"], res_str))
                vec = ",".join(str(round(random.uniform(-0.1, 0.1), 4)) for _ in range(1024))
                cur.execute("INSERT INTO VectorSearch.FHIRTextVectors (ResourceID, ResourceType, TextContent, Vector, EmbeddingModel, Provider, CreatedAt) VALUES (?, ?, ?, TO_VECTOR(?, DOUBLE, 1024), ?, ?, NOW())", (n["id"], n["type"], n["text"], vec, 'mock', 'nim'))
                
                doc_id = int(n["id"].split('-p')[1].replace('-', ''))
                
                cur.execute("INSERT INTO RAG.Entities (EntityText, EntityType, ResourceID, Confidence) VALUES (?, ?, ?, ?)", (n["name"], "CONDITION", doc_id, 0.95))
                e_count += 1
                cur.execute("SELECT LAST_IDENTITY()")
                cond_db_id = cur.fetchone()[0]
                
                for item in n["items"]:
                    etype = "MEDICATION" if item.lower() in MEDICATIONS else "SYMPTOM"
                    cur.execute("INSERT INTO RAG.Entities (EntityText, EntityType, ResourceID, Confidence) VALUES (?, ?, ?, ?)", (item, etype, doc_id, 0.90))
                    e_count += 1
                    cur.execute("SELECT LAST_IDENTITY()")
                    item_db_id = cur.fetchone()[0]
                    
                    rtype = "TREATS" if etype == "MEDICATION" else "CAUSES"
                    src, tgt = (item_db_id, cond_db_id) if etype == "MEDICATION" else (cond_db_id, item_db_id)
                    cur.execute("INSERT INTO RAG.EntityRelationships (SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence) VALUES (?, ?, ?, ?, ?)", (src, tgt, rtype, doc_id, 0.85))
                    r_count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ IRIS Data Populated: {e_count} entities, {r_count} relationships")
    except Exception as e:
        print(f"IRIS Error: {e}")

if __name__ == "__main__":
    main()
