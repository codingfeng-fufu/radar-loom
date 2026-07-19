import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import radar_common as rc
import render_graph as rg
import taxonomy_models as tm


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


def test_external_nodes_do_not_count_or_enter_taxonomy_memberships():
    interviews = {"Q": page("Q", related=["Concept"])}
    knowledge = {"Concept": page("Concept", page_type="knowledge")}
    edges, broken, degree, external = rg.interview_graph_data(interviews, knowledge)
    registry = tm.Registry.empty("", "2026-01-01")
    payload = json.loads(rg.render_graph_data(interviews, edges, broken, degree, registry,
                                              external_nodes=external, profile="interview",
                                              external_pages=knowledge))
    assert payload["stats"]["internalNodeCount"] == 1
    assert payload["stats"]["nodeCount"] == 1
    assert payload["stats"]["externalNodeCount"] == 1
    assert payload["taxonomy"]["stats"]["memberships"] == 0


def test_interview_taxonomy_payload_is_not_knowledge_taxonomy():
    registry = tm.Registry.empty("", "2026-01-01")
    registry.categories["interview"] = tm.Category("interview", "Interview", "q", "stable")
    payload = json.loads(rg.render_graph_data({}, [], [], {}, registry, profile="interview"))
    assert [c["id"] for c in payload["taxonomy"]["categories"]] == ["interview"]


def test_interview_payload_is_deterministic_for_reversed_input():
    a = {"Q1": page("Q1", links=["Q2"], related=["Concept"]), "Q2": page("Q2")}
    b = dict(reversed(list(a.items())))
    knowledge = {"Concept": page("Concept", page_type="knowledge")}
    def render(pages):
        e, broken, degree, external = rg.interview_graph_data(pages, knowledge)
        return rg.render_graph_data(pages, e, broken, degree, external_nodes=external,
                                    profile="interview", external_pages=knowledge)
    assert render(a) == render(b)


def test_missing_interview_registry_is_empty_and_generator_succeeds():
    payload = json.loads(rg.render_graph_data({}, [], [], {}, tm.Registry.empty("", "2026-01-01"), profile="interview"))
    assert payload["taxonomy"]["stats"] == {
        "categories": 0, "activeCategories": 0, "memberships": 0,
        "forming": 0, "pendingPages": 0, "seedCategories": 0,
        "automaticCategories": 0, "candidates": 0,
    }
