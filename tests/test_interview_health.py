import contextlib
import io
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_health
import radar_common as rc

HEADINGS = "\n".join("## " + h for h in check_health.INTERVIEW_HEADINGS)
BASE_FM = {"page_type":"interview","summary":"s","source":"https://x","confidence":"高","first_recorded":"d","tags":["t"],"roles":["r"],"difficulty":"基础","question":"q","related_concepts":[]}

def _run(monkeypatch, pages):
    monkeypatch.setattr(rc, "scan_pages", lambda: pages)
    for name in ("INDEX_FILE","INTERVIEW_INDEX_FILE","GRAPH_FILE","GRAPH_DATA_FILE","INTERVIEW_GRAPH_FILE","INTERVIEW_GRAPH_DATA_FILE"):
        monkeypatch.setattr(rc, name, Path("/tmp/health-missing-" + name))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        check_health.main([])
    return out.getvalue()


def _page(name, fm, body=""):
    return rc.PageInfo(name, Path(name + ".md"), fm, body, rc.WIKILINK_RE.findall(body))


def test_interview_metadata_and_headings_are_checked(monkeypatch):
    good = _page("Q", {
        "page_type": "interview", "summary": "s", "source": "https://example.test",
        "confidence": "高", "first_recorded": "2026-01-01", "tags": ["缓存"],
        "roles": ["后端"], "difficulty": "进阶", "question": "q",
        "related_concepts": [],
    }, "## 面试问题\n## 考察意图\n## 30 秒回答\n## 2 分钟回答\n## 原理拆解\n## 递进追问与参考回答\n## 常见错误回答\n## 评分标准\n## 关联概念\n## 来源核验\n## 更新记录\n")
    old = {name: getattr(rc, name) for name in ("scan_pages", "INDEX_FILE", "INTERVIEW_INDEX_FILE", "GRAPH_FILE", "GRAPH_DATA_FILE", "INTERVIEW_GRAPH_FILE", "INTERVIEW_GRAPH_DATA_FILE")}
    try:
        monkeypatch.setattr(rc, "scan_pages", lambda: {"Q": good})
        for name in old:
            if name.endswith("FILE"):
                monkeypatch.setattr(rc, name, Path("/tmp/does-not-exist") / name)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_health.main([])
        assert code == 1  # missing generated artifacts are intentionally errors
        assert "E19" in out.getvalue()
    finally:
        for name, value in old.items():
            setattr(rc, name, value)


def test_related_concepts_accept_scalar_and_resolve_cross_zone(monkeypatch):
    interview = _page("Q", {"page_type": "interview", "summary": "s", "source": "https://x", "confidence": "高", "first_recorded": "d", "tags": ["t"], "roles": ["r"], "difficulty": "基础", "question": "q", "related_concepts": "Concept"}, "[[Concept]]")
    concept = _page("Concept", {"tags": ["KG"], "来源": "https://x", "信度": "高", "摘要": "s"}, "")
    knowledge, interviews = rc.partition_pages({"Q": interview, "Concept": concept})
    assert set(knowledge) == {"Concept"}
    assert set(interviews) == {"Q"}


def test_missing_related_concepts_is_reported(monkeypatch, capsys):
    fm = {"page_type": "interview", "summary": "s", "source": "https://x", "confidence": "高", "first_recorded": "d", "tags": ["t"], "roles": ["r"], "difficulty": "基础", "question": "q"}
    monkeypatch.setattr(rc, "scan_pages", lambda: {"Q": _page("Q", fm)})
    monkeypatch.setattr(rc, "INDEX_FILE", Path("/tmp/missing-index")); monkeypatch.setattr(rc, "INTERVIEW_INDEX_FILE", Path("/tmp/missing-i-index"))
    monkeypatch.setattr(rc, "GRAPH_FILE", Path("/tmp/missing-graph")); monkeypatch.setattr(rc, "GRAPH_DATA_FILE", Path("/tmp/missing-graph-data")); monkeypatch.setattr(rc, "INTERVIEW_GRAPH_FILE", Path("/tmp/missing-i-graph")); monkeypatch.setattr(rc, "INTERVIEW_GRAPH_DATA_FILE", Path("/tmp/missing-i-graph-data"))
    check_health.main([])
    assert "缺少 related_concepts 字段" in capsys.readouterr().out


def test_invalid_explicit_page_type_is_not_ordinary(monkeypatch, capsys):
    monkeypatch.setattr(rc, "scan_pages", lambda: {"Bad": _page("Bad", {"page_type": "other"})})
    check_health.main([])
    output = capsys.readouterr().out
    assert "page_type 不支持" in output


import re

import pytest
import unittest

INTERVIEW_PAGES = (
    "设计一个AI Agent的记忆系统.md",
    "多头注意力机制的核心作用是什么.md",
    "知识图谱的存储方式与索引优化.md",
)

def test_existing_interview_pages_use_scan_first_structure():
    pages = rc.scan_pages()
    for filename in INTERVIEW_PAGES:
        body = pages[filename[:-3]].body
        brief = body.split("## 30 秒回答", 1)[1].split("## ", 1)[0]
        assert re.search(r"(?m)^1\. .+\n2\. .+\n3\. .+", brief)
        assert "```mermaid" in body or "](../assets/interview/" in body
        assert not re.search(r"!\[[^]]*\]\(https?://", body)

class InterviewHealthDiscoveryTests(unittest.TestCase):
    def test_matrix_module_discovery(self):
        self.assertIn("E12", check_health.CODE_ORDER)

@pytest.mark.parametrize("field,value,code", [
    ("summary", "", "E12"), ("source", "", "E14"), ("confidence", "X", "E12"),
    ("tags", [], "E12"), ("roles", [], "E12"), ("difficulty", "错误", "E13"), ("question", "", "E12"),
])
def test_interview_invalid_metadata_matrix(monkeypatch, field, value, code):
    fm = dict(BASE_FM); fm[field] = value
    assert f"[ERROR {code}]" in _run(monkeypatch, {"Q": _page("Q", fm, HEADINGS)})

@pytest.mark.parametrize("body,code", [(HEADINGS.replace("## 评分标准", ""), "E16"), (HEADINGS + "\n[TODO]", "E17"), (HEADINGS + "\na_b = c", "E18")])
def test_interview_content_matrix(monkeypatch, body, code):
    assert f"[ERROR {code}]" in _run(monkeypatch, {"Q": _page("Q", dict(BASE_FM), body)})

def test_broken_links_and_related_concepts(monkeypatch):
    fm = dict(BASE_FM); fm["related_concepts"] = ["Missing"]
    output = _run(monkeypatch, {"Q": _page("Q", fm, HEADINGS + "\n[[Missing]]")})
    assert output.count("[ERROR E15]") >= 2

def test_ordinary_page_unaffected_and_empty_interview_zone(monkeypatch):
    ordinary = _page("K", {"tags":["KG"],"来源":"https://x","信度":"高","摘要":"s"})
    ordinary_output = _run(monkeypatch, {"K": ordinary})
    assert "[ERROR E12]" not in ordinary_output and "[ERROR E15]" not in ordinary_output
    assert "[ERROR E12]" not in _run(monkeypatch, {})

@pytest.mark.parametrize("filename,code", [("taxonomy.json", "E20"), ("interview-taxonomy.json", "E19")])
def test_malformed_taxonomy_is_reported_without_traceback(monkeypatch, tmp_path, filename, code):
    (tmp_path / filename).write_text("{malformed", encoding="utf-8")
    monkeypatch.setattr(rc, "VAULT_ROOT", tmp_path)
    monkeypatch.setattr(rc, "scan_pages", lambda: {})
    for name in ("INDEX_FILE","INTERVIEW_INDEX_FILE","GRAPH_FILE","GRAPH_DATA_FILE","INTERVIEW_GRAPH_FILE","INTERVIEW_GRAPH_DATA_FILE"):
        monkeypatch.setattr(rc, name, tmp_path / name)
    output = _run(monkeypatch, {})
    assert f"[ERROR {code}]" in output
