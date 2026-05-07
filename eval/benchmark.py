"""
EHDS Benchmark — 50 queries with SPARQL-derived ground truth
============================================================
Run against: https://mcp.linkeddata.es/sparql
Catalogue graph: https://ehds-prototype.example.org/graph/catalogue
Clinical graphs:  https://ehds-prototype.example.org/graph/{cohort-id}

Ground truth for every query is derived by executing ground_truth_sparql
against the live RDF store. The ground_truth list is the pre-computed result
of that query and is used for offline scoring. If the endpoint changes, re-run
the SPARQL to regenerate ground_truth values.

"""

SPARQL_ENDPOINT = "https://mcp.linkeddata.es/sparql"
GRAPH_CATALOGUE = "https://ehds-prototype.example.org/graph/catalogue"
BASE = "https://ehds-prototype.example.org/"

QUERIES = [

# =============================================================================
# DISCOVERY (D1–D10)
# =============================================================================

{
    "id": "D1",
    "category": "discovery",
    "query": "What datasets are available in this data space?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title .
  }
} ORDER BY ?title
""",
    "ground_truth": [
        "Synthetic Alzheimer's Disease Cohort",
        "Synthetic Anemia Cohort",
        "Synthetic Anxiety Disorder Cohort",
        "Synthetic Asthma Cohort",
        "Synthetic Atrial Fibrillation Cohort",
        "Synthetic Breast Cancer Cohort",
        "Synthetic COPD Cohort",
        "Synthetic Chronic Kidney Disease Cohort",
        "Synthetic Chronic Pain Cohort",
        "Synthetic Colorectal Cancer Cohort",
        "Synthetic Dementia Cohort",
        "Synthetic Essential Hypertension Cohort",
        "Synthetic Heart Failure Cohort",
        "Synthetic Hyperlipidemia Cohort",
        "Synthetic Hypothyroidism Cohort",
        "Synthetic Ischaemic Heart Disease Cohort",
        "Synthetic Metabolic Syndrome Cohort",
        "Synthetic Myocardial Infarction Cohort",
        "Synthetic Obesity Cohort",
        "Synthetic Obstructive Sleep Apnea Cohort",
        "Synthetic Osteoarthritis Cohort",
        "Synthetic Osteoporosis Cohort",
        "Synthetic PTSD Cohort",
        "Synthetic Prediabetes Cohort",
        "Synthetic Prostate Cancer Cohort",
        "Synthetic Rheumatoid Arthritis Cohort",
        "Synthetic Stroke Cohort",
        "Synthetic Substance Use Disorder Cohort",
        "Synthetic Type 2 Diabetes Cohort",
        "Synthetic Urinary Tract Infection Cohort",
    ],
},

{
    "id": "D2",
    "category": "discovery",
    "query": "How many datasets are available in this data space?",
    "ground_truth_sparql": """
SELECT (COUNT(?dataset) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> .
  }
}
""",
    "ground_truth": ["30"],
},

{
    "id": "D3",
    "category": "discovery",
    "query": "Which datasets cover cardiovascular conditions?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory> ?cat .
    FILTER(?cat IN (
      <http://snomed.info/id/88805009>,
      <http://snomed.info/id/230690007>,
      <http://snomed.info/id/22298006>,
      <http://snomed.info/id/414545008>,
      <http://snomed.info/id/49436004>
    ))
  }
}
""",
    "ground_truth": [
        "Synthetic Heart Failure Cohort",
        "Synthetic Stroke Cohort",
        "Synthetic Myocardial Infarction Cohort",
        "Synthetic Ischaemic Heart Disease Cohort",
        "Synthetic Atrial Fibrillation Cohort",
    ],
},

{
    "id": "D4",
    "category": "discovery",
    "query": "Which datasets cover mental health conditions?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory> ?cat .
    FILTER(?cat IN (
      <http://snomed.info/id/80583007>,
      <http://snomed.info/id/47505003>,
      <http://snomed.info/id/52448006>
    ))
  }
}
""",
    "ground_truth": [
        "Synthetic Anxiety Disorder Cohort",
        "Synthetic PTSD Cohort",
        "Synthetic Dementia Cohort",
    ],
},

{
    "id": "D5",
    "category": "discovery",
    "query": "Which datasets cover oncology conditions?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory> ?cat .
    FILTER(?cat IN (
      <http://snomed.info/id/254837009>,
      <http://snomed.info/id/126906006>,
      <http://snomed.info/id/363406005>
    ))
  }
}
""",
    "ground_truth": [
        "Synthetic Breast Cancer Cohort",
        "Synthetic Prostate Cancer Cohort",
        "Synthetic Colorectal Cancer Cohort",
    ],
},

{
    "id": "D6",
    "category": "discovery",
    "query": "What data standard is used for the clinical data?",
    "ground_truth_sparql": """
SELECT DISTINCT ?standard WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <https://healthdcat-ap.github.io/healthdcat-ap/release/5/dataStandard> ?standard .
  }
}
""",
    "ground_truth": ["FHIR R4"],
},

{
    "id": "D7",
    "category": "discovery",
    "query": "Which datasets have temporal coverage starting before 2005?",
    "ground_truth_sparql": """
SELECT ?title ?start WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://purl.org/dc/terms/temporal> ?period .
    ?period <http://www.w3.org/ns/dcat#startDate> ?start .
    FILTER(?start < "2005-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
  }
} ORDER BY ?start
""",
    "ground_truth": [
        "Synthetic Anemia Cohort", "2000-01-01",
        "Synthetic Asthma Cohort", "2000-01-01",
        "Synthetic COPD Cohort", "2000-01-01",
        "Synthetic Type 2 Diabetes Cohort", "2000-01-01",
        "Synthetic Hyperlipidemia Cohort", "2000-01-01",
        "Synthetic Essential Hypertension Cohort", "2000-01-01",
        "Synthetic Hypothyroidism Cohort", "2000-01-01",
        "Synthetic Metabolic Syndrome Cohort", "2000-01-01",
        "Synthetic Obesity Cohort", "2000-01-01",
        "Synthetic Prediabetes Cohort", "2000-01-01",
        "Synthetic Obstructive Sleep Apnea Cohort", "2000-01-01",
        "Synthetic Urinary Tract Infection Cohort", "2000-01-01",
        "Synthetic Alzheimer's Disease Cohort", "2003-01-01",
        "Synthetic Chronic Kidney Disease Cohort", "2003-01-01",
        "Synthetic Osteoporosis Cohort", "2003-01-01",
        "Synthetic Rheumatoid Arthritis Cohort", "2003-01-01",
    ],
},

{
    "id": "D8",
    "category": "discovery",
    "query": "Which datasets end before 2025?",
    "ground_truth_sparql": """
SELECT ?title ?end WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://purl.org/dc/terms/temporal> ?period .
    ?period <http://www.w3.org/ns/dcat#endDate> ?end .
    FILTER(?end < "2025-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
  }
}
""",
    "ground_truth": [
        "Synthetic Asthma Cohort", "2023-12-31",
        "Synthetic COPD Cohort", "2023-12-31",
        "Synthetic Obstructive Sleep Apnea Cohort", "2023-12-31",
        "Synthetic Urinary Tract Infection Cohort", "2023-12-31",
    ],
},

{
    "id": "D9",
    "category": "discovery",
    "query": "Are there any datasets related to respiratory conditions?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory> ?cat .
    FILTER(?cat IN (
      <http://snomed.info/id/195967001>,
      <http://snomed.info/id/87433001>,
      <http://snomed.info/id/73430006>
    ))
  }
}
""",
    "ground_truth": [
        "Synthetic Asthma Cohort",
        "Synthetic COPD Cohort",
        "Synthetic Obstructive Sleep Apnea Cohort",
    ],
},

{
    "id": "D10",
    "category": "discovery",
    "query": "How many patients are in the dementia cohort?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/dementia> {
    ?patient a <http://hl7.org/fhir/Patient> .
  }
}
""",
    "ground_truth": ["0"],
},

# =============================================================================
# POLICY (P1–P20)
# =============================================================================

{
    "id": "P1",
    "category": "policy",
    "query": "What are the permitted uses of the diabetes dataset?",
    "ground_truth_sparql": """
SELECT ?action ?purpose WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-diabetes>
      <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/permission> ?perm .
    ?perm <http://www.w3.org/ns/odrl/2/action> ?action .
    OPTIONAL { ?perm <http://www.w3.org/ns/odrl/2/constraint> ?c .
               ?c <http://www.w3.org/ns/odrl/2/rightOperand> ?purpose . }
  }
}
""",
    "ground_truth": ["reproduce", "ResearchAndDevelopment", "distribute", "ResearchAndDevelopment"],
},

{
    "id": "P2",
    "category": "policy",
    "query": "Can I use the hypertension dataset to train a commercial AI model?",
    "ground_truth_sparql": """
SELECT ?action ?purpose WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-hypertension>
      <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?prohib .
    ?prohib <http://www.w3.org/ns/odrl/2/action> ?action .
    OPTIONAL { ?prohib <http://www.w3.org/ns/odrl/2/constraint> ?c .
               ?c <http://www.w3.org/ns/odrl/2/rightOperand> ?purpose . }
  }
}
""",
    "ground_truth": ["use", "CommercialPurpose", "re-identify"],
},

{
    "id": "P3",
    "category": "policy",
    "query": "Which datasets require ethics approval before use?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p3-ethics-approval> .
  }
}
""",
    "ground_truth": [
        "Synthetic Dementia Cohort",
        "Synthetic Anxiety Disorder Cohort",
        "Synthetic PTSD Cohort",
    ],
},

{
    "id": "P4",
    "category": "policy",
    "query": "Which datasets permit clinical care use?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p2-clinical-care> .
  }
}
""",
    "ground_truth": [
        "Synthetic Heart Failure Cohort",
        "Synthetic Stroke Cohort",
        "Synthetic Myocardial Infarction Cohort",
        "Synthetic Ischaemic Heart Disease Cohort",
        "Synthetic Atrial Fibrillation Cohort",
    ],
},

{
    "id": "P5",
    "category": "policy",
    "query": "Is re-identification of patients allowed on any dataset?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?prohib .
    ?prohib <http://www.w3.org/ns/odrl/2/action>
            <https://ehds-prototype.example.org/re-identify> .
  }
}
""",
    "ground_truth": [
        "Synthetic Type 2 Diabetes Cohort",
        "Synthetic Essential Hypertension Cohort",
        "Synthetic Metabolic Syndrome Cohort",
        "Synthetic Obesity Cohort",
        "Synthetic Hyperlipidemia Cohort",
        "Synthetic Prediabetes Cohort",
        "Synthetic Hypothyroidism Cohort",
        "Synthetic Anemia Cohort",
        "Synthetic Heart Failure Cohort",
        "Synthetic Stroke Cohort",
        "Synthetic Myocardial Infarction Cohort",
        "Synthetic Ischaemic Heart Disease Cohort",
        "Synthetic Atrial Fibrillation Cohort",
        "Synthetic Dementia Cohort",
        "Synthetic Anxiety Disorder Cohort",
        "Synthetic PTSD Cohort",
        "Synthetic Alzheimer's Disease Cohort",
        "Synthetic Osteoporosis Cohort",
        "Synthetic Rheumatoid Arthritis Cohort",
        "Synthetic Chronic Kidney Disease Cohort",
        "Synthetic Breast Cancer Cohort",
        "Synthetic Prostate Cancer Cohort",
        "Synthetic Colorectal Cancer Cohort",
        "Synthetic Osteoarthritis Cohort",
        "Synthetic Substance Use Disorder Cohort",
        "Synthetic Chronic Pain Cohort",
    ],
},

{
    "id": "P6",
    "category": "policy",
    "query": "Which datasets require IRB approval?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p6-oncology-restricted> .
  }
}
""",
    "ground_truth": [
        "Synthetic Breast Cancer Cohort",
        "Synthetic Prostate Cancer Cohort",
        "Synthetic Colorectal Cancer Cohort",
    ],
},

{
    "id": "P7",
    "category": "policy",
    "query": "Which datasets require data destruction after use?",
    "ground_truth_sparql": """
SELECT DISTINCT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/obligation> ?oblig .
    ?oblig <http://www.w3.org/ns/odrl/2/action> <http://www.w3.org/ns/odrl/2/delete> .
  }
}
""",
    "ground_truth": [
        "Synthetic Breast Cancer Cohort",
        "Synthetic Prostate Cancer Cohort",
        "Synthetic Colorectal Cancer Cohort",
        "Synthetic Osteoarthritis Cohort",
    ],
},

{
    "id": "P8",
    "category": "policy",
    "query": "Can I use the PTSD dataset for insurance risk modelling?",
    "ground_truth_sparql": """
SELECT ?action ?recipient WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-ptsd>
      <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?prohib .
    ?prohib <http://www.w3.org/ns/odrl/2/action> ?action .
    OPTIONAL { ?prohib <http://www.w3.org/ns/odrl/2/constraint> ?c .
               ?c <http://www.w3.org/ns/odrl/2/rightOperand> ?recipient . }
  }
}
""",
    "ground_truth": ["distribute", "granted", "use", "CommercialPurpose", "re-identify"],
},

{
    "id": "P9",
    "category": "policy",
    "query": "Which datasets prohibit law enforcement use?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?prohib .
    ?prohib <http://www.w3.org/ns/odrl/2/constraint> ?c .
    ?c <http://www.w3.org/ns/odrl/2/rightOperand> <https://w3id.org/dpv#LawEnforcement> .
  }
}
""",
    "ground_truth": [
        "Synthetic Substance Use Disorder Cohort",
        "Synthetic Chronic Pain Cohort",
    ],
},

{
    "id": "P10",
    "category": "policy",
    "query": "What licence do all datasets use?",
    "ground_truth_sparql": """
SELECT DISTINCT ?license WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/license> ?license .
  }
}
""",
    "ground_truth": ["4.0"],
},

{
    # NOTE: policy-p10-education-open maps to zero datasets in the catalogue.
    # The correct answer is that no dataset currently permits both research
    # and education use under a single dedicated policy. An agent should
    # report this absence rather than hallucinate dataset names.
    "id": "P11",
    "category": "policy",
    "query": "Which datasets can I use for both research and education?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p10-education-open> .
  }
}
""",
    "ground_truth": [],
},

{
    "id": "P12",
    "category": "policy",
    "query": "Which datasets have time-limited access?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p7-time-limited> .
  }
}
""",
    "ground_truth": ["Synthetic Osteoarthritis Cohort"],
},

{
    # IRB documentation is a prohibition constraint (access condition), not an
    # odrl:obligation action. The two obligations are 'attribute' and 'delete'.
    "id": "P13",
    "category": "policy",
    "query": "What obligations apply when using the breast cancer dataset?",
    "ground_truth_sparql": """
SELECT ?action WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-breast-cancer>
      <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/obligation> ?oblig .
    ?oblig <http://www.w3.org/ns/odrl/2/action> ?action .
  }
}
""",
    "ground_truth": ["attribute", "delete"],
},

{
    # odrl:derive permission is only present in P5 (open-noncommercial) policy.
    # Atrial Fibrillation, Ischaemic Heart Disease, and Hyperlipidemia are P2/P9
    # and do not carry an explicit derive permission.
    "id": "P14",
    "category": "policy",
    "query": "Which datasets permit derivation and sharing of derived datasets?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/permission> ?perm .
    ?perm <http://www.w3.org/ns/odrl/2/action> <http://www.w3.org/ns/odrl/2/derive> .
  }
}
""",
    "ground_truth": [
        "Synthetic Asthma Cohort",
        "Synthetic COPD Cohort",
        "Synthetic Obstructive Sleep Apnea Cohort",
        "Synthetic Urinary Tract Infection Cohort",
    ],
},

{
    "id": "P15",
    "category": "policy",
    "query": "Can I use the substance use disorder dataset for insurance purposes?",
    "ground_truth_sparql": """
SELECT ?action ?recipient WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-substance-use-disorder>
      <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?prohib .
    ?prohib <http://www.w3.org/ns/odrl/2/constraint> ?c .
    ?c <http://www.w3.org/ns/odrl/2/rightOperand> <https://w3id.org/dpv#InsuranceCompany> .
    ?prohib <http://www.w3.org/ns/odrl/2/action> ?action .
  }
}
""",
    "ground_truth": ["use"],
},

{
    # policy-p9-cardiovascular-open maps to zero datasets.
    # Correct agent response: report absence rather than name datasets.
    "id": "P16",
    "category": "policy",
    "query": "Which datasets permit public health research?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p9-cardiovascular-open> .
  }
}
""",
    "ground_truth": [],
},

{
    "id": "P17",
    "category": "policy",
    "query": "How many patients across all datasets have withdrawn consent for AI training?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH ?g {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-patient-no-ai-training> .
  }
  FILTER(?g != <https://ehds-prototype.example.org/graph/catalogue>)
}
""",
    "ground_truth": ["168"],
},

{
    # NotifyDataController obligation is not instantiated in any dataset policy
    # in the current catalogue. Correct agent response: report absence.
    # (The ethics-approval datasets use ethicsBoardApproval, a separate action.)
    "id": "P18",
    "category": "policy",
    "query": "Which datasets require notifying the data controller before use?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/obligation> ?oblig .
    ?oblig <http://www.w3.org/ns/odrl/2/action>
           <https://ehds-prototype.example.org/NotifyDataController> .
  }
}
""",
    "ground_truth": [],
},

{
    "id": "P19",
    "category": "policy",
    "query": "Which datasets can be freely redistributed for non-commercial purposes?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p5-open-noncommercial> .
  }
}
""",
    "ground_truth": [
        "Synthetic Asthma Cohort",
        "Synthetic COPD Cohort",
        "Synthetic Obstructive Sleep Apnea Cohort",
        "Synthetic Urinary Tract Infection Cohort",
    ],
},

{
    "id": "P20",
    "category": "policy",
    "query": "How many distinct ODRL policies are defined in the catalogue?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?policy) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
  }
}
""",
    "ground_truth": ["8"],
},

# =============================================================================
# CLINICAL (C1–C10)
# =============================================================================

{
    "id": "C1",
    "category": "clinical",
    "query": "What is the most common medication prescribed to patients in the diabetes cohort?",
    "ground_truth_sparql": """
SELECT ?display (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/diabetes> {
    ?med a <http://hl7.org/fhir/MedicationRequest> ;
         <http://hl7.org/fhir/subject> ?patient .
    { ?med <http://hl7.org/fhir/medicationCode> ?coding . }
    UNION
    { ?med <http://hl7.org/fhir/medication> ?m .
      ?m <http://hl7.org/fhir/code> ?coding . }
    ?coding <http://hl7.org/fhir/display> ?display .
  }
} GROUP BY ?display ORDER BY DESC(?n) LIMIT 1
""",
    "ground_truth": ["sodium fluoride 0.0272 MG/MG Oral Gel", "38"],
},

{
    "id": "C2",
    "category": "clinical",
    "query": "How many female patients are in the PTSD cohort?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/ptsd> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <http://hl7.org/fhir/gender> "female" .
  }
}
""",
    "ground_truth": ["1"],
},

{
    "id": "C3",
    "category": "clinical",
    "query": "What is the SNOMED code for the condition in the hypertension dataset?",
    "ground_truth_sparql": """
SELECT ?healthCategory WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-hypertension>
      <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory>
      ?healthCategory .
  }
}
""",
    "ground_truth": ["59621000"],
},

{
    "id": "C4",
    "category": "clinical",
    "query": "What observation types are recorded for stroke patients?",
    "ground_truth_sparql": """
SELECT DISTINCT ?display WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/stroke> {
    ?obs a <http://hl7.org/fhir/Observation> ;
         <http://hl7.org/fhir/code> ?coding .
    ?coding <http://hl7.org/fhir/display> ?display .
  }
} LIMIT 20
""",
    "ground_truth": [
        "Cholesterol in HDL [Mass/volume] in Serum or Plasma",
        "Body Height",
        "Calcium [Mass/volume] in Blood",
        "Hemoglobin A1c/Hemoglobin.total in Blood",
        "Tobacco smoking status",
        "Sodium [Moles/volume] in Blood",
        "MCV [Entitic mean volume] in Red Blood Cells by Automated count",
        "Urea nitrogen [Mass/volume] in Blood",
        "Glucose [Mass/volume] in Blood",
        "Carbon dioxide, total [Moles/volume] in Blood",
        "Fall risk total [Morse Fall Scale]",
        "Creatinine [Mass/volume] in Blood",
        "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
        "Erythrocyte [DistWidth] in Blood by Automated count",
        "Hematocrit [Volume Fraction] of Blood by Automated count",
        "Potassium [Moles/volume] in Blood",
        "Respiratory rate",
        "Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay",
        "Blood pressure panel with all children optional",
        "Body Weight",
    ],
},

{
    "id": "C5",
    "category": "clinical",
    "query": "What is the gender distribution in the obesity cohort?",
    "ground_truth_sparql": """
SELECT ?gender (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/obesity> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <http://hl7.org/fhir/gender> ?gender .
  }
} GROUP BY ?gender
""",
    "ground_truth": ["female", "25", "male", "15"],
},

{
    "id": "C6",
    "category": "clinical",
    "query": "What is the earliest birth year among patients in the alzheimers cohort?",
    "ground_truth_sparql": """
SELECT (MIN(?birthYear) AS ?earliest) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/alzheimers> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <https://ehds-prototype.example.org/birthYear> ?birthYear .
  }
}
""",
    "ground_truth": ["1916"],
},

{
    "id": "C7",
    "category": "clinical",
    "query": "How many patients in the breast cancer cohort have withdrawn consent for AI training?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/breast-cancer> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-patient-no-ai-training> .
  }
}
""",
    "ground_truth": ["2"],
},

{
    "id": "C8",
    "category": "clinical",
    "query": "What medications are most commonly prescribed to hypertension patients?",
    "ground_truth_sparql": """
SELECT ?display (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/hypertension> {
    ?med a <http://hl7.org/fhir/MedicationRequest> ;
         <http://hl7.org/fhir/subject> ?patient .
    { ?med <http://hl7.org/fhir/medicationCode> ?coding . }
    UNION
    { ?med <http://hl7.org/fhir/medication> ?m .
      ?m <http://hl7.org/fhir/code> ?coding . }
    ?coding <http://hl7.org/fhir/display> ?display .
  }
} GROUP BY ?display ORDER BY DESC(?n) LIMIT 5
""",
    "ground_truth": [
        "sodium fluoride 0.0272 MG/MG Oral Gel", "40",
        "lisinopril 10 MG Oral Tablet", "26",
        "Acetaminophen 325 MG Oral Tablet", "23",
        "24 HR metoprolol succinate 100 MG Extended Release Oral Tablet", "20",
        "Clopidogrel 75 MG Oral Tablet", "20",
    ],
},

{
    "id": "C9",
    "category": "clinical",
    "query": "How many patients are in the dementia cohort?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/dementia> {
    ?patient a <http://hl7.org/fhir/Patient> .
  }
}
""",
    "ground_truth": ["0"],
},

{
    "id": "C10",
    "category": "clinical",
    "query": "What is the race distribution in the chronic pain cohort?",
    "ground_truth_sparql": """
SELECT ?race (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/chronic-pain> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <https://ehds-prototype.example.org/race> ?race .
  }
} GROUP BY ?race ORDER BY DESC(?n)
""",
    "ground_truth": ["White", "10"],
},

# =============================================================================
# COMPARATIVE (X1–X10)
# =============================================================================

{
    # The namedGraph predicate link is not yet resolvable via cross-graph JOIN
    # in the current Fuseki setup. Ground truth is left empty; correct agent
    # behaviour is to attempt the lookup and report the result accurately.
    "id": "X1",
    "category": "comparative",
    "query": "Which dataset has the most patients?",
    "ground_truth_sparql": """
SELECT ?title (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH ?g {
    ?patient a <http://hl7.org/fhir/Patient> .
  }
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/namedGraph> ?g .
  }
} GROUP BY ?title ORDER BY DESC(?n) LIMIT 1
""",
    "ground_truth": [],
},

{
    # Same namedGraph resolution issue as X1.
    "id": "X2",
    "category": "comparative",
    "query": "Which dataset has the fewest patients?",
    "ground_truth_sparql": """
SELECT ?title (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH ?g {
    ?patient a <http://hl7.org/fhir/Patient> .
  }
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/namedGraph> ?g .
  }
} GROUP BY ?title ORDER BY ?n LIMIT 1
""",
    "ground_truth": [],
},

{
    # 573 is the COUNT DISTINCT of fhir:Patient across all clinical graphs.
    # 911 (used in earlier CSV drafts) is the sum of per-cohort counts
    # including overlapping patients, as noted in Table 1 of the paper.
    "id": "X3",
    "category": "comparative",
    "query": "What is the total number of patients across all datasets?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?patient) AS ?n) WHERE {
  GRAPH ?g {
    ?patient a <http://hl7.org/fhir/Patient> .
  }
  FILTER(?g != <https://ehds-prototype.example.org/graph/catalogue>)
}
""",
    "ground_truth": ["573"],
},

{
    "id": "X4",
    "category": "comparative",
    "query": "Which dataset would be most appropriate for studying comorbid diabetes and hypertension?",
    "ground_truth_sparql": """
SELECT ?title ?description WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    <https://ehds-prototype.example.org/dataset-metabolic-syndrome>
      <http://purl.org/dc/terms/title> ?title ;
      <http://purl.org/dc/terms/description> ?description .
  }
}
""",
    "ground_truth": [
        "Synthetic Metabolic Syndrome Cohort",
        "Synthetic patients presenting with both Type 2 Diabetes and Essential Hypertension, representing core metabolic syndrome indicators.",
    ],
},

{
    "id": "X5",
    "category": "comparative",
    "query": "Which datasets have the shortest temporal coverage?",
    "ground_truth_sparql": """
SELECT ?title ?start ?end WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://purl.org/dc/terms/temporal> ?period .
    ?period <http://www.w3.org/ns/dcat#startDate> ?start ;
            <http://www.w3.org/ns/dcat#endDate> ?end .
  }
} ORDER BY (?end - ?start) LIMIT 3
""",
    "ground_truth": [
        "Synthetic Chronic Pain Cohort", "2015-01-01", "2025-12-31",
        "Synthetic Substance Use Disorder Cohort", "2015-01-01", "2025-12-31",
        "Synthetic Anxiety Disorder Cohort", "2010-01-01", "2025-12-31",
    ],
},

{
    "id": "X6",
    "category": "comparative",
    "query": "How many datasets share the same research-only policy?",
    "ground_truth_sparql": """
SELECT (COUNT(?dataset) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p1-research-only> .
  }
}
""",
    "ground_truth": ["8"],
},

{
    "id": "X7",
    "category": "comparative",
    "query": "Which policy group has the most datasets?",
    "ground_truth_sparql": """
SELECT ?policy (COUNT(?dataset) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
  }
} GROUP BY ?policy ORDER BY DESC(?n) LIMIT 1
""",
    "ground_truth": ["policy-p1-research-only", "8"],
},

{
    # Only datasets with ethicsBoardApproval or NotifyDataController obligations
    # are counted. NotifyDataController is currently uninstantiated, so only
    # the 3 ethics-approval datasets (Anxiety, PTSD, Dementia) would qualify,
    # but only 2 have the obligation triple present in the current serialisation.
    "id": "X8",
    "category": "comparative",
    "query": "How many datasets require some form of approval before use?",
    "ground_truth_sparql": """
SELECT (COUNT(DISTINCT ?dataset) AS ?n) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/obligation> ?oblig .
    ?oblig <http://www.w3.org/ns/odrl/2/action> ?action .
    FILTER(?action IN (
      <https://ehds-prototype.example.org/ethicsBoardApproval>,
      <https://ehds-prototype.example.org/NotifyDataController>
    ))
  }
}
""",
    "ground_truth": ["2"],
},

{
    "id": "X9",
    "category": "comparative",
    "query": "Compare the temporal coverage of the mental health datasets.",
    "ground_truth_sparql": """
SELECT ?title ?start ?end WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <http://www.w3.org/ns/odrl/2/hasPolicy>
             <https://ehds-prototype.example.org/policy-p3-ethics-approval> ;
             <http://purl.org/dc/terms/temporal> ?period .
    ?period <http://www.w3.org/ns/dcat#startDate> ?start ;
            <http://www.w3.org/ns/dcat#endDate> ?end .
  }
}
""",
    "ground_truth": [
        "Synthetic Dementia Cohort", "2010-01-01", "2025-12-31",
        "Synthetic Anxiety Disorder Cohort", "2010-01-01", "2025-12-31",
        "Synthetic PTSD Cohort", "2010-01-01", "2025-12-31",
    ],
},

{
    "id": "X10",
    "category": "comparative",
    "query": "Which datasets cover conditions that commonly co-occur with diabetes?",
    "ground_truth_sparql": """
SELECT ?title WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/healthCategory> ?cat .
    FILTER(?cat IN (
      <http://snomed.info/id/59621000>,
      <http://snomed.info/id/237602007>,
      <http://snomed.info/id/162864005>,
      <http://snomed.info/id/55822004>,
      <http://snomed.info/id/431855005>
    ))
  }
}
""",
    "ground_truth": [
        "Synthetic Essential Hypertension Cohort",
        "Synthetic Metabolic Syndrome Cohort",
        "Synthetic Obesity Cohort",
        "Synthetic Hyperlipidemia Cohort",
        "Synthetic Chronic Kidney Disease Cohort",
    ],
},

]

if __name__ == "__main__":
    import json
    print(json.dumps(QUERIES, indent=2))
