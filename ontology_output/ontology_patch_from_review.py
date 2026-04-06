#!/usr/bin/env python3
"""
ontology_patch_from_review.py
Apply expert-reviewed xrefs and definitions back to the OWL ontology.
Run AFTER experts have filled Expert_Approved column in enriched CSV.
"""
import csv
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from pathlib import Path

OWL_IN  = "corpus_analysis/ontology_output/ards_poi_ontology_v9_fixed.owl"
OWL_OUT = "corpus_analysis/ontology_output/ards_poi_ontology_v10_expert.owl"
CSV_IN  = "corpus_analysis/ontology_output/expert_review_sheet_enriched.csv"

POI    = Namespace("http://purl.obolibrary.org/obo/poi/")
OBO    = Namespace("http://purl.obolibrary.org/obo/")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
IAO    = OBO["IAO_0000115"]

g = Graph()
g.parse(OWL_IN)
print(f"Loaded {len(g)} triples from {OWL_IN}")

applied_xrefs = 0
applied_defs  = 0
reclassified  = 0

with open(CSV_IN) as f:
    for row in csv.DictReader(f):
        approved = row.get("Expert_Approved","").strip().upper()
        if approved not in ("YES","MODIFY"):
            continue

        iri_suffix = row["IRI"]
        cls = URIRef(f"http://purl.obolibrary.org/obo/{iri_suffix}")

        # Apply xref if expert approved
        xref = row.get("Auto_Xref","").strip()
        if xref and approved == "YES":
            g.add((cls, OBOINOWL.hasDbXref, Literal(xref)))
            applied_xrefs += 1

        # Apply definition if missing
        cur_def = row.get("Definition","").strip()
        auto_def = row.get("Auto_Definition","").strip()
        if not cur_def and auto_def and "[Definition needed" not in auto_def:
            g.add((cls, IAO, Literal(auto_def)))
            applied_defs += 1

        # Apply PMID evidence
        pmid = row.get("PMID_Evidence","").strip()
        if pmid:
            g.add((cls, OBOINOWL.hasDbXref, Literal(f"PMID:{pmid}")))

        # Apply reclassification (change inSubset)
        new_subset = row.get("Suggested_Subset","").strip()
        correction = row.get("Suggested_Correction","").strip()
        if new_subset and approved == "YES":
            # Remove old subset
            old_subsets = list(g.objects(cls, OBO.inSubset))
            for s in old_subsets:
                g.remove((cls, OBO.inSubset, s))
            # Add new subset
            new_uri = URIRef(f"http://purl.obolibrary.org/obo/poi/{new_subset}")
            g.add((cls, OBO.inSubset, new_uri))
            reclassified += 1

g.serialize(destination=OWL_OUT, format="xml")
print(f"Applied: {applied_xrefs} xrefs, {applied_defs} definitions, {reclassified} reclassifications")
print(f"Output: {OWL_OUT} ({len(g)} triples)")
