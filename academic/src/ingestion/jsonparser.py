import json
from pathlib import Path


# ---------- PARSERS ----------

def parse_patient(resource):
    """Parseia um recurso Patient do FHIR e retorna um dicionário com o texto e metadados."""
    name = resource.get("name", [{}])[0]

    first = " ".join(name.get("given", []))
    last = name.get("family", "")

    return {
        "text": f"""
Patient

Patient ID: {resource.get("subject", {}).get("reference", "").replace("urn:uuid:", "")}
Name: {first} {last}
Gender: {resource.get("gender", "Unknown")}
Birth date: {resource.get("birthDate", "Unknown")}
""".strip(),

        "metadata": {
            "resource_type": "Patient",
            "patient_id": resource.get("id"),
        }
    }
    

def parse_condition(resource):
    """Parseia um recurso Condition do FHIR e retorna um dicionário com o texto e metadados."""

    description = (
        resource.get("code", {})
        .get("coding", [{}])[0]
        .get("display", "Unknown")
    )

    status = (
        resource.get("clinicalStatus", {})
        .get("coding", [{}])[0]
        .get("display", "Unknown")
    )

    return {
        "text": f"""
Condition

Patient ID: {resource.get("subject", {}).get("reference", "").replace("urn:uuid:", "")}
Description: {description}
Status: {status}
Recorded: {resource.get("recordedDate", "Unknown")}
""".strip(),

        "metadata": {
            "resource_type": "Condition",
            "patient_id": (
                resource.get("subject", {})
                .get("reference", "")
                .replace("urn:uuid:", "")
            )
        }
    }


def parse_observation(resource):
    """Parseia um recurso Observation do FHIR e retorna um dicionário com o texto e metadados."""

    name = (
        resource.get("code", {})
        .get("coding", [{}])[0]
        .get("display", "Unknown")
    )

    value = resource.get("valueQuantity", {}).get("value", "Unknown")
    unit = resource.get("valueQuantity", {}).get("unit", "")

    return {
        "text": f"""
Observation

Patient ID: {resource.get("subject", {}).get("reference", "").replace("urn:uuid:", "")}
Test: {name}
Result: {value} {unit}
Date: {resource.get("effectiveDateTime", "Unknown")}
""".strip(),

        "metadata": {
            "resource_type": "Observation",
            "patient_id": (
                resource.get("subject", {})
                .get("reference", "")
                .replace("urn:uuid:", "")
            )
        }
    }


def parse_medication(resource):
    """Parseia um recurso MedicationRequest do FHIR e retorna um dicionário com o texto e metadados."""

    medication = (
        resource.get("medicationCodeableConcept", {})
        .get("coding", [{}])[0]
        .get("display", "Unknown")
    )

    return {
        "text": f"""
Medication

Patient ID: {resource.get("subject", {}).get("reference", "").replace("urn:uuid:", "")}
Medication: {medication}
Status: {resource.get("status", "Unknown")}
Authored: {resource.get("authoredOn", "Unknown")}
""".strip(),

        "metadata": {
            "resource_type": "MedicationRequest",
            "patient_id": (
                resource.get("subject", {})
                .get("reference", "")
                .replace("urn:uuid:", "")
            )
        }
    }


def parse_encounter(resource):
    """Parseia um recurso Encounter do FHIR e retorna um dicionário com o texto e metadados."""

    encounter_type = (
        resource.get("type", [{}])[0]
        .get("coding", [{}])[0]
        .get("display", "Unknown")
    )

    period = resource.get("period", {})

    return {
        "text": f"""
Encounter

Patient ID: {resource.get("subject", {}).get("reference", "").replace("urn:uuid:", "")}
Type: {encounter_type}
Start: {period.get("start", "Unknown")}
End: {period.get("end", "Unknown")}
""".strip(),

        "metadata": {
            "resource_type": "Encounter",
            "patient_id": (
                resource.get("subject", {})
                .get("reference", "")
                .replace("urn:uuid:", "")
            )
        }
    }


# seletor de parsers

PARSERS = {
    "Patient": parse_patient,
    "Condition": parse_condition,
    "Observation": parse_observation,
    "MedicationRequest": parse_medication,
    "Encounter": parse_encounter,
}


# main

folder = Path(__file__).resolve().parents[2] / "data" / "raw" / "json" / "synthea"

output_file = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "synthea.jsonl"
)

output_file.parent.mkdir(parents=True, exist_ok=True)

count = 0

with output_file.open("w", encoding="utf-8") as out:

    for patient_file in folder.glob("*.json"):

        print(f"Processing {patient_file.name}")

        with patient_file.open(encoding="utf-8") as f:
            bundle = json.load(f)

        for entry in bundle["entry"]:

            resource = entry["resource"]

            parser = PARSERS.get(resource["resourceType"])

            if parser:
                document = parser(resource)
                document["metadata"]["source"] = patient_file.name

                json.dump(document, out, ensure_ascii=False)
                out.write("\n")

                count += 1

print(f"Created {count} documents.")
