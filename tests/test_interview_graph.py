import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import radar_common as rc
import render_graph as rg


def page(name, *, page_type="interview", links=None, related=None):
    return rc.PageInfo(name, Path(f"pages/{name}.md"), {
        "page_type": page_type,
        "related_concepts": related or [],
    }, "", links or [])


def test_interview_profile_separates_and_resolves_external():
    interviews = {"Q1": page("Q1", links=["Q2"], related=["Concept"]), "Q2": page("Q2")}
    knowledge = {"Concept": page("Concept", page_type="knowledge")}
    edges, broken, degree, external = rg.interview_graph_data(interviews, knowledge)
    assert edges == [("Q1", "Q2"), ("Q1", "Concept")]
    assert broken == []
    assert external == {"Concept"}
    payload = json.loads(rg.render_graph_data(interviews, edges, broken, degree,
                                              external_nodes=external, profile="interview",
                                              external_pages=knowledge))
    assert payload["stats"]["nodeCount"] == 2
    assert payload["stats"]["externalNodeCount"] == 1
    assert next(n for n in payload["nodes"] if n["id"] == "Concept")["external"] is True


def test_broken_related_concept_is_reported():
    edges, broken, _, _ = rg.interview_graph_data({"Q": page("Q", related=["Missing"])}, {})
    assert edges == []
    assert broken == [("Q", "Missing")]
