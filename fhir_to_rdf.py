#!/usr/bin/env python3
"""
synthea_to_rdf_v3.py
Converts Synthea FHIR R4 JSON bundles to RDF (Turtle/TriG).

Improvements over v2:
- Race and ethnicity as explicit typed triples (US Core extension)
- Bidirectional Patient ↔ Condition/Observation/MedicationRequest links
- Observation component values (blood pressure systolic/diastolic)
- Medication as a named individual node (not just inline BNode)
- Encounter reasonCode linking encounters to conditions
- Birth year as integer triple for demographic range queries
- Patient consent flags (20% no-AI, 10% no-secondary-use, 5% erasure)

Usage:
    python3 synthea_to_rdf_v3.py <input_dir> <output_file.ttl> \
        [--graph <named_graph_uri>] \
        [--consent-seed 42]
"""

import json
import argparse
import hashlib
import random
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

FHIR  = Namespace("http://hl7.org/fhir/")
BASE  = Namespace("https://ehds-prototype.example.org/data/")
EHDS  = Namespace("https://ehds-prototype.example.org/")
ODRL  = Namespace("http://www.w3.org/ns/odrl/2/")
DPV   = Namespace("https://w3id.org/dpv#")
SNOMED = Namespace("http://snomed.info/id/")
LOINC  = Namespace("http://loinc.org/rdf/")
RXNORM = Namespace("http://www.nlm.nih.gov/research/umls/rxnorm/")

# US Core race/ethnicity extension URLs
US_CORE_RACE      = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
US_CORE_ETHNICITY = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
RACE_SYSTEM       = "urn:oid:2.16.840.1.113883.6.238"

# ---------------------------------------------------------------------------
# Consent flag probabilities
# ---------------------------------------------------------------------------

CONSENT_NO_AI        = 0.20   # 20% of patients prohibit AI training
CONSENT_NO_SECONDARY = 0.10   # 10% prohibit secondary use
CONSENT_ERASURE      = 0.05   # 5% have requested erasure


def fhir_uri(resource_type: str, resource_id: str) -> URIRef:
    return BASE[f"{resource_type}/{resource_id}"]


def uri_from_code(system: str, code: str) -> URIRef:
    """Convert a coding system+code to a proper URI."""
    if system == "http://snomed.info/sct":
        return SNOMED[code]
    if system == "http://loinc.org":
        return LOINC[code]
    if system == "http://www.nlm.nih.gov/research/umls/rxnorm":
        return RXNORM[code]
    # Generic fallback
    safe = system.rstrip("/").rstrip("#")
    return URIRef(f"{safe}/{code}")


def add_coding(g: Graph, subject: URIRef, predicate: URIRef,
               coding_list: list, as_uri: bool = True):
    """
    Add FHIR CodeableConcept codings to graph.
    If as_uri=True and system is known, add a direct URI link alongside the BNode.
    """
    for coding in coding_list:
        system  = coding.get("system", "")
        code    = coding.get("code", "")
        display = coding.get("display", "")

        bn = BNode()
        g.add((subject, predicate, bn))
        g.add((bn, RDF.type, FHIR.Coding))
        if system:
            g.add((bn, FHIR.system, Literal(system)))
        if code:
            g.add((bn, FHIR.code, Literal(code)))
        if display:
            g.add((bn, FHIR.display, Literal(display)))

        # Also add a direct typed URI link for semantic query support
        if as_uri and system and code:
            concept_uri = uri_from_code(system, code)
            g.add((subject, FHIR.conceptReference, concept_uri))
            g.add((concept_uri, RDF.type, FHIR.Concept))
            if display:
                g.add((concept_uri, RDFS.label, Literal(display, lang="en")))


def get_race_ethnicity(resource: dict) -> tuple:
    """Extract race and ethnicity from US Core extensions."""
    race = None
    ethnicity = None
    for ext in resource.get("extension", []):
        url = ext.get("url", "")
        if url == US_CORE_RACE:
            for sub in ext.get("extension", []):
                if sub.get("url") == "ombCategory":
                    vc = sub.get("valueCoding", {})
                    race = vc.get("display", vc.get("code", ""))
        elif url == US_CORE_ETHNICITY:
            for sub in ext.get("extension", []):
                if sub.get("url") == "ombCategory":
                    vc = sub.get("valueCoding", {})
                    ethnicity = vc.get("display", vc.get("code", ""))
    return race, ethnicity


def convert_patient(g: Graph, resource: dict, rng: random.Random) -> URIRef:
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("Patient", rid)
    g.add((subj, RDF.type, FHIR.Patient))
    g.add((subj, FHIR.id, Literal(rid)))

    # Gender
    if "gender" in resource:
        g.add((subj, FHIR.gender, Literal(resource["gender"])))

    # Birth date + birth year as integer for range queries
    if "birthDate" in resource:
        bd = resource["birthDate"]
        g.add((subj, FHIR.birthDate, Literal(bd, datatype=XSD.date)))
        try:
            birth_year = int(bd[:4])
            g.add((subj, EHDS.birthYear, Literal(birth_year, datatype=XSD.integer)))
        except (ValueError, IndexError):
            pass

    # Race and ethnicity (US Core extensions)
    race, ethnicity = get_race_ethnicity(resource)
    if race:
        g.add((subj, EHDS.race, Literal(race)))
    if ethnicity:
        g.add((subj, EHDS.ethnicity, Literal(ethnicity)))

    # Address (city, state only)
    for addr in resource.get("address", []):
        bn = BNode()
        g.add((subj, FHIR.address, bn))
        g.add((bn, RDF.type, FHIR.Address))
        if "city" in addr:
            g.add((bn, FHIR.city, Literal(addr["city"])))
        if "state" in addr:
            g.add((bn, FHIR.state, Literal(addr["state"])))
        if "country" in addr:
            g.add((bn, FHIR.country, Literal(addr["country"])))

    # Patient-level consent flags
    r = rng.random()
    if r < CONSENT_ERASURE:
        g.add((subj, ODRL.hasPolicy, EHDS["policy-patient-erasure-requested"]))
    elif r < CONSENT_ERASURE + CONSENT_NO_SECONDARY:
        g.add((subj, ODRL.hasPolicy, EHDS["policy-patient-no-secondary-use"]))
    elif r < CONSENT_ERASURE + CONSENT_NO_SECONDARY + CONSENT_NO_AI:
        g.add((subj, ODRL.hasPolicy, EHDS["policy-patient-no-ai-training"]))

    return subj


def convert_condition(g: Graph, resource: dict,
                      patient_index: dict) -> URIRef:
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("Condition", rid)
    g.add((subj, RDF.type, FHIR.Condition))
    g.add((subj, FHIR.id, Literal(rid)))

    # Subject reference — bidirectional
    subject_ref = resource.get("subject", {}).get("reference", "")
    if subject_ref.startswith("urn:uuid:"):
        patient_id = subject_ref.replace("urn:uuid:", "")
        patient_uri = fhir_uri("Patient", patient_id)
        g.add((subj, FHIR.subject, patient_uri))
        g.add((patient_uri, FHIR.condition, subj))   # inverse link

    # Code with URI reference
    code = resource.get("code", {})
    add_coding(g, subj, FHIR.code, code.get("coding", []), as_uri=True)

    # Clinical status
    clinical_status = resource.get("clinicalStatus", {})
    add_coding(g, subj, FHIR.clinicalStatus,
               clinical_status.get("coding", []), as_uri=False)

    # Verification status
    verification_status = resource.get("verificationStatus", {})
    add_coding(g, subj, FHIR.verificationStatus,
               verification_status.get("coding", []), as_uri=False)

    # Onset
    if "onsetDateTime" in resource:
        g.add((subj, FHIR.onsetDateTime,
               Literal(resource["onsetDateTime"], datatype=XSD.dateTime)))

    # Abatement
    if "abatementDateTime" in resource:
        g.add((subj, FHIR.abatementDateTime,
               Literal(resource["abatementDateTime"], datatype=XSD.dateTime)))

    return subj


def convert_observation(g: Graph, resource: dict) -> URIRef:
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("Observation", rid)
    g.add((subj, RDF.type, FHIR.Observation))
    g.add((subj, FHIR.id, Literal(rid)))

    # Subject — bidirectional
    subject_ref = resource.get("subject", {}).get("reference", "")
    if subject_ref.startswith("urn:uuid:"):
        patient_id = subject_ref.replace("urn:uuid:", "")
        patient_uri = fhir_uri("Patient", patient_id)
        g.add((subj, FHIR.subject, patient_uri))
        g.add((patient_uri, FHIR.observation, subj))  # inverse link

    # Code
    code = resource.get("code", {})
    add_coding(g, subj, FHIR.code, code.get("coding", []), as_uri=True)

    # Simple value quantity
    if "valueQuantity" in resource:
        vq = resource["valueQuantity"]
        bn = BNode()
        g.add((subj, FHIR.valueQuantity, bn))
        g.add((bn, RDF.type, FHIR.Quantity))
        if "value" in vq:
            g.add((bn, FHIR.value, Literal(vq["value"], datatype=XSD.decimal)))
        if "unit" in vq:
            g.add((bn, FHIR.unit, Literal(vq["unit"])))
        if "system" in vq:
            g.add((bn, FHIR.system, Literal(vq["system"])))
        if "code" in vq:
            g.add((bn, FHIR.code, Literal(vq["code"])))

    # Value codeable concept (e.g. for categorical observations)
    if "valueCodeableConcept" in resource:
        vcc = resource["valueCodeableConcept"]
        add_coding(g, subj, FHIR.valueCode, vcc.get("coding", []), as_uri=True)

    # Component values (e.g. blood pressure systolic/diastolic)
    for comp in resource.get("component", []):
        comp_bn = BNode()
        g.add((subj, FHIR.component, comp_bn))
        g.add((comp_bn, RDF.type, FHIR.ObservationComponent))
        comp_code = comp.get("code", {})
        add_coding(g, comp_bn, FHIR.code,
                   comp_code.get("coding", []), as_uri=True)
        if "valueQuantity" in comp:
            vq = comp["valueQuantity"]
            vq_bn = BNode()
            g.add((comp_bn, FHIR.valueQuantity, vq_bn))
            g.add((vq_bn, RDF.type, FHIR.Quantity))
            if "value" in vq:
                g.add((vq_bn, FHIR.value,
                       Literal(vq["value"], datatype=XSD.decimal)))
            if "unit" in vq:
                g.add((vq_bn, FHIR.unit, Literal(vq["unit"])))

    # Effective date
    if "effectiveDateTime" in resource:
        g.add((subj, FHIR.effectiveDateTime,
               Literal(resource["effectiveDateTime"], datatype=XSD.dateTime)))

    # Status
    if "status" in resource:
        g.add((subj, FHIR.status, Literal(resource["status"])))

    return subj


def convert_medication(g: Graph, resource: dict) -> URIRef:
    """Convert a Medication resource to a named individual node."""
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("Medication", rid)
    g.add((subj, RDF.type, FHIR.Medication))
    g.add((subj, FHIR.id, Literal(rid)))
    code = resource.get("code", {})
    add_coding(g, subj, FHIR.code, code.get("coding", []), as_uri=True)
    return subj


def convert_medication_request(g: Graph, resource: dict,
                                bundle_medications: dict) -> URIRef:
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("MedicationRequest", rid)
    g.add((subj, RDF.type, FHIR.MedicationRequest))
    g.add((subj, FHIR.id, Literal(rid)))

    # Subject — bidirectional
    subject_ref = resource.get("subject", {}).get("reference", "")
    if subject_ref.startswith("urn:uuid:"):
        patient_id = subject_ref.replace("urn:uuid:", "")
        patient_uri = fhir_uri("Patient", patient_id)
        g.add((subj, FHIR.subject, patient_uri))
        g.add((patient_uri, FHIR.medicationRequest, subj))  # inverse

    # Medication — prefer named node
    if "medicationReference" in resource:
        ref_id = resource["medicationReference"].get(
            "reference", "").replace("urn:uuid:", "")
        if ref_id in bundle_medications:
            med_uri = fhir_uri("Medication", ref_id)
            g.add((subj, FHIR.medication, med_uri))
        else:
            g.add((subj, FHIR.medicationReference,
                   Literal(ref_id)))
    elif "medicationCodeableConcept" in resource:
        med_cc = resource["medicationCodeableConcept"]
        add_coding(g, subj, FHIR.medicationCode,
                   med_cc.get("coding", []), as_uri=True)

    if "status" in resource:
        g.add((subj, FHIR.status, Literal(resource["status"])))
    if "authoredOn" in resource:
        g.add((subj, FHIR.authoredOn,
               Literal(resource["authoredOn"], datatype=XSD.dateTime)))

    return subj


def convert_encounter(g: Graph, resource: dict) -> URIRef:
    rid  = resource.get("id", "unknown")
    subj = fhir_uri("Encounter", rid)
    g.add((subj, RDF.type, FHIR.Encounter))
    g.add((subj, FHIR.id, Literal(rid)))

    # Subject — bidirectional
    subject_ref = resource.get("subject", {}).get("reference", "")
    if subject_ref.startswith("urn:uuid:"):
        patient_id = subject_ref.replace("urn:uuid:", "")
        patient_uri = fhir_uri("Patient", patient_id)
        g.add((subj, FHIR.subject, patient_uri))
        g.add((patient_uri, FHIR.encounter, subj))  # inverse

    # Class
    enc_class = resource.get("class", {})
    if "code" in enc_class:
        g.add((subj, FHIR["class"], Literal(enc_class["code"])))

    # Type
    for t in resource.get("type", []):
        add_coding(g, subj, FHIR.type,
                   t.get("coding", []), as_uri=False)

    # Reason codes — link to condition concepts
    for reason in resource.get("reasonCode", []):
        add_coding(g, subj, FHIR.reasonCode,
                   reason.get("coding", []), as_uri=True)

    # Reason references — link to Condition resources
    for reason_ref in resource.get("reasonReference", []):
        ref = reason_ref.get("reference", "")
        if ref.startswith("urn:uuid:"):
            condition_id = ref.replace("urn:uuid:", "")
            g.add((subj, FHIR.reasonReference,
                   fhir_uri("Condition", condition_id)))

    # Period
    period = resource.get("period", {})
    if "start" in period:
        g.add((subj, FHIR.periodStart,
               Literal(period["start"], datatype=XSD.dateTime)))
    if "end" in period:
        g.add((subj, FHIR.periodEnd,
               Literal(period["end"], datatype=XSD.dateTime)))

    # Status
    if "status" in resource:
        g.add((subj, FHIR.status, Literal(resource["status"])))

    return subj


def convert_bundle(g: Graph, bundle_path: Path, rng: random.Random) -> int:
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    if bundle.get("resourceType") != "Bundle":
        return 0

    # First pass — index Medication resources as named nodes
    bundle_medications = {}
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Medication":
            rid = resource.get("id", "")
            bundle_medications[rid] = resource
            convert_medication(g, resource)

    count = 0
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            convert_patient(g, resource, rng)
            count += 1
        elif rtype == "Condition":
            convert_condition(g, resource, {})
            count += 1
        elif rtype == "Observation":
            convert_observation(g, resource)
            count += 1
        elif rtype == "MedicationRequest":
            convert_medication_request(g, resource, bundle_medications)
            count += 1
        elif rtype == "Encounter":
            convert_encounter(g, resource)
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Convert Synthea FHIR JSON to RDF Turtle (v3 — graph structure)")
    parser.add_argument("input_dir",   help="Directory containing FHIR JSON files")
    parser.add_argument("output_file", help="Output Turtle file path")
    parser.add_argument("--graph",     help="Named graph URI", default=None)
    parser.add_argument("--consent-seed", type=int, default=42,
                        help="Random seed for consent flag assignment")
    args = parser.parse_args()

    input_dir  = Path(args.input_dir)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.consent_seed)

    g = Graph()
    g.bind("fhir",   FHIR)
    g.bind("xsd",    XSD)
    g.bind("ehds",   EHDS)
    g.bind("odrl",   ODRL)
    g.bind("dpv",    DPV)
    g.bind("snomed", SNOMED)
    g.bind("loinc",  LOINC)
    g.bind("rxnorm", RXNORM)
    g.bind("rdfs",   RDFS)

    json_files = [f for f in input_dir.glob("*.json")
                  if "hospital" not in f.name
                  and "practitioner" not in f.name]

    print(f"Found {len(json_files)} patient FHIR bundles in {input_dir}")

    total_resources = 0
    for i, json_file in enumerate(json_files):
        try:
            n = convert_bundle(g, json_file, rng)
            total_resources += n
        except Exception as e:
            print(f"  WARNING: Failed to convert {json_file.name}: {e}")
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(json_files)} files — {len(g)} triples so far")

    print(f"\nConverted {total_resources} resources → {len(g)} triples")
    print(f"Writing to {output_file}...")

    if args.graph:
        trig_output = output_file.with_suffix(".trig")
        prefixes = "\n".join([
            "@prefix fhir:   <http://hl7.org/fhir/> .",
            "@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix ehds:   <https://ehds-prototype.example.org/data/> .",
            "@prefix odrl:   <http://www.w3.org/ns/odrl/2/> .",
            "@prefix dpv:    <https://w3id.org/dpv#> .",
            "@prefix snomed: <http://snomed.info/id/> .",
            "@prefix loinc:  <http://loinc.org/rdf/> .",
            "@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .",
        ])
        with open(trig_output, "w", encoding="utf-8") as f:
            f.write(prefixes + "\n\n")
            f.write(f"<{args.graph}> {{\n")
            for line in g.serialize(format="turtle").splitlines():
                if not line.startswith("@prefix"):
                    f.write(f"  {line}\n")
            f.write("}\n")
        print(f"Wrote TriG to {trig_output}")
    else:
        g.serialize(destination=str(output_file), format="turtle")

    print("Done.")


if __name__ == "__main__":
    main()
