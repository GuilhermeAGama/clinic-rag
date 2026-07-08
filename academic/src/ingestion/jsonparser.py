import json
from pathlib import Path
from datetime import datetime

#config

folder = Path(__file__).resolve().parents[2] / "data" / "raw" / "json" / "synthea"

output_file = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "synthea.jsonl"
)

output_file.parent.mkdir(parents=True, exist_ok=True)


def calculate_age(birth_date):
    """Calcula a idade com base na data de nascimento fornecida. Recebe uma string no formato 'YYYY-MM-DD' e retorna a idade em anos como um inteiro.
    Se a data de nascimento for inválida ou não estiver no formato esperado, retorna 'Unknown'."""
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.today()

        age = today.year - birth.year

        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1

        return age

    except Exception:
        return "Unknown"


# ---------------- MAIN ---------------- #

count = 0

with output_file.open("w", encoding="utf-8") as out:

    for patient_file in folder.glob("*.json"):

        print(f"Processing {patient_file.name}")

        with patient_file.open(encoding="utf-8") as f:
            bundle = json.load(f)

        patients = {}

        #Primeira passada

        for entry in bundle["entry"]:

            resource = entry["resource"]
            resource_type = resource["resourceType"]

            #Patient

            if resource_type == "Patient":

                patient_id = resource["id"]

                name = resource.get("name", [{}])[0]

                first = " ".join(name.get("given", []))
                last = name.get("family", "")

                birth = resource.get("birthDate", "Unknown")

                patients[patient_id] = {
                "name": f"{first} {last}".strip(),
                "gender": resource.get("gender", "Unknown"),
                "birth": birth,
                "age": calculate_age(birth),

                # elimina duplicatas automaticamente
                "conditions": set(),
                "medications": set(),
                "encounters": set(),

                # guarda apenas o último valor de cada observação
                "vitals": {},
                "labs": {}
            }

            else:

                patient_id = (
                    resource.get("subject", {})
                    .get("reference", "")
                    .replace("urn:uuid:", "")
                )

                if patient_id not in patients:
                    continue

                #Condition

                if resource_type == "Condition":

                    condition = (
                        resource.get("code", {})
                        .get("coding", [{}])[0]
                        .get("display", "Unknown")
                    )

                    if (
                        condition != "Medication review due (situation)"
                        and condition != "Unknown"
                    ):
                        patients[patient_id]["conditions"].add(condition)

                #Medication

                elif resource_type == "MedicationRequest":

                    medication = (
                        resource.get("medicationCodeableConcept", {})
                        .get("coding", [{}])[0]
                        .get("display", "Unknown")
                    )

                    if medication != "Unknown":
                        patients[patient_id]["medications"].add(medication)

                #Observation

                elif resource_type == "Observation":

                    obs = (
                        resource.get("code", {})
                        .get("coding", [{}])[0]
                        .get("display", "Unknown")
                    )

                    value = resource.get("valueQuantity", {}).get("value")
                    unit = resource.get("valueQuantity", {}).get("unit", "")

                    if value is None:
                        continue

                    texto = f"{value} {unit}".strip()

                    # sinais vitais
                    vital_names = {
                        "Body Height",
                        "Body Weight",
                        "Heart rate",
                        "Respiratory rate",
                        "Body temperature",
                        "Body mass index (BMI) [Ratio]"
                    }

                    if obs in vital_names:
                        patients[patient_id]["vitals"][obs] = texto
                    else:
                        patients[patient_id]["labs"][obs] = texto

                #Encounter

                elif resource_type == "Encounter":

                    encounter = (
                        resource.get("type", [{}])[0]
                        .get("coding", [{}])[0]
                        .get("display", "Unknown")
                    )

                    patients[patient_id]["encounters"].add(encounter)

        #Geração do documento

        for patient_id, patient in patients.items():

            text = f"""Paciente
Name: {patient["name"]}
Age: {patient["age"]} years
Gender: {patient["gender"]}
Birth: {patient["birth"]}
Conditions:
"""

            if patient["conditions"]:
                text += "\n".join(f"- {x}" for x in sorted(patient["conditions"]))
            else:
                text += "- Nenhum"

            text += "\n\nMedications:\n"

            if patient["medications"]:
                text += "\n".join(f"- {x}" for x in sorted(patient["medications"]))
            else:
                text += "- Nenhum"

            text += "\n\nVital Signs:\n"

            if patient["vitals"]:
                for nome, valor in sorted(patient["vitals"].items()):
                    text += f"- {nome}: {valor}\n"
            else:
                text += "- Nenhum\n"

            text += "\nLaboratory Tests:\n"

            if patient["labs"]:
                for nome, valor in sorted(patient["labs"].items()):
                    text += f"- {nome}: {valor}\n"
            else:
                text += "- Nenhum\n"

            text += "\nEncounter Types:\n"

            if patient["encounters"]:
                text += "\n".join(f"- {x}" for x in sorted(patient["encounters"]))
            else:
                text += "- Nenhuma"
                
            print(text)

            document = {
                "text": text,
                "metadata": {
                    "type": "Synthea FHIR",
                    "patient_id": patient_id,
                    "patient_name": patient["name"],
                    "source": patient_file.name
                }
            }

            json.dump(document, out, ensure_ascii=False)
            out.write("\n")

            count += 1

print(f"Created {count} patient documents.")