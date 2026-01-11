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

CONDITIONS = [
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
        conds = random.sample(CONDITIONS, random.randint(1, 3))
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

def send_bundle(entries):
    bundle = {"resourceType": "Bundle", "type": "transaction", "entry": entries}
    data = json.dumps(bundle).encode("utf-8")
    auth = "Basic " + base64.b64encode(f"{FHIR_USERNAME}:{FHIR_PASSWORD}".encode()).decode()
    req = urllib.request.Request(FHIR_BASE_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/fhir+json")
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return True, json.loads(resp.read())
    except Exception as e:
        return False, str(e)

def main():
    print("Generating 50 patients...")
    patients = generate_patients()
    entries = []
    for p in patients:
        entries.append({"resource": {"resourceType": "Patient", "id": p["id"], "name": [{"family": p["lname"], "given": [p["fname"]]}], "gender": p["gender"], "birthDate": p["bdate"]}, "request": {"method": "PUT", "url": f"Patient/{p['id']}"}})
        entries.append({"resource": {"resourceType": "ImagingStudy", "id": p["img"]["id"], "status": "available", "subject": {"reference": f"Patient/{p['id']}"}, "started": p["img"]["date"], "modality": [{"code": "CR"}], "description": p["img"]["finding"]}, "request": {"method": "PUT", "url": f"ImagingStudy/{p['img']['id']}"}})
    
    print("Uploading FHIR Bundle...")
    success, res = send_bundle(entries)
    if not success:
        print(f"FHIR Error: {res}")
    else:
        print("✅ FHIR Data Populated")

    print("Populating IRIS Tables...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        for t in ["SQLUser.FHIRDocuments", "VectorSearch.FHIRTextVectors", "RAG.Entities", "RAG.EntityRelationships"]:
            try: cur.execute(f"DELETE FROM {t}")
            except: pass
        
        for p in patients:
            for n in p["notes"]:
                res_str = json.dumps({"resourceType": "Composition", "id": n["id"], "status": "final", "text": {"div": n["text"]}})
                cur.execute("INSERT INTO SQLUser.FHIRDocuments (FHIRResourceId, ResourceType, TextContent, ResourceString, CreatedAt) VALUES (?, ?, ?, ?, NOW())", (n["id"], n["type"], n["text"], res_str))
                vec = ",".join(str(round(random.uniform(-0.5, 0.5), 4)) for _ in range(1024))
                cur.execute("INSERT INTO VectorSearch.FHIRTextVectors (ResourceID, ResourceType, TextContent, Vector, EmbeddingModel, Provider, CreatedAt) VALUES (?, ?, ?, TO_VECTOR(?, DOUBLE, 1024), ?, ?, NOW())", (n["id"], n["type"], n["text"], vec, 'mock', 'nim'))
                doc_id = int(n["id"].split('-p')[1].replace('-', ''))
                cur.execute("INSERT INTO RAG.Entities (EntityText, EntityType, ResourceID, Confidence) VALUES (?, ?, ?, ?)", (n["name"], "CONDITION", doc_id, 0.95))
        
        conn.commit()
        conn.close()
        print("✅ IRIS Data Populated")
    except Exception as e:
        print(f"IRIS Error: {e}")

if __name__ == "__main__":
    main()
