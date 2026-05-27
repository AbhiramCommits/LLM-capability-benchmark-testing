#!/usr/bin/env python3
"""Automated grader for the Collections Feature benchmark task.

Evaluates a FastAPI codebase submission on two dimensions:
  1. Procedural correctness (endpoint behavior, edge cases)     — 50 points
  2. Documentation completeness (specs, changelog, docstrings) — 50 points

Run from the project root:
    python grader.py
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from io import BytesIO
from pathlib import Path

# ── Bootstrap: import the app (may fail) ────────────────────────────────────
try:
    from fastapi.testclient import TestClient

    from app.main import app as _app
    from app import database as _db

    APP_LOADED = True
except Exception as exc:
    APP_LOADED = False
    _LOAD_ERROR = str(exc)
    _app = None
    _db = None


# ── Helpers ──────────────────────────────────────────────────────────────────

RESULT = {
    "procedural_scores": {},
    "procedural_total": 0,
    "documentation_scores": {},
    "documentation_total": 0,
    "llm_score": 0,
    "total": 0,
    "failure_reasons": [],
}


def _fail(reason: str) -> None:
    RESULT["failure_reasons"].append(reason)


PROCEDURAL_MAX = 50  # 5 checks * 10 pts
DOC_MAX = 50  # 5 checks * 10 pts


# ── Module reload helper (simulate server restart) ───────────────────────────

def _fresh_client():
    """Reload all app modules in dependency order, return a new TestClient."""
    try:
        # Reload leaves-first so each module picks up fresh dependencies
        for mod_name in (
            "app.models",
            "app.schemas",
            "app.database",
            "app.routers.documents",
            "app.routers.collections",
            "app.routers",
            "app.main",
        ):
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        from app.main import app as fresh_app

        return TestClient(fresh_app)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PROCEDURAL CHECKS  (10 points each, 50 total)
# ══════════════════════════════════════════════════════════════════════════════

def _run_procedural_checks():
    """Run all 5 procedural checks against the running app."""
    if not APP_LOADED:
        for i in range(1, 6):
            RESULT["procedural_scores"][f"check_{i}"] = 0
            _fail(f"App failed to load: {_LOAD_ERROR}")
        return

    client = TestClient(_app)

    # --- Check 1: All 5 endpoints exist and return correct statuses ----------
    score = 0
    coll_id = None
    doc_id = None

    # 1a: Create collection
    resp = client.post(
        "/api/v1/collections",
        json={"name": "Test Collection", "description": "A test"},
    )
    if resp.status_code in (200, 201):
        body = resp.json()
        coll_id = body.get("id") or body.get("collection", {}).get("id")
        if coll_id:
            score += 2

    # 1b: Add document to collection (need a document first)
    doc_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
        data={"filename": "test.txt", "tags": "test", "description": "a doc"},
    )
    doc_id = doc_resp.json()["document"]["id"] if doc_resp.status_code == 201 else None

    if coll_id and doc_id:
        add_resp = client.post(
            f"/api/v1/collections/{coll_id}/documents",
            json={"document_id": doc_id},
        )
        if add_resp.status_code in (200, 201):
            score += 2

    # 1c: List collections
    list_resp = client.get("/api/v1/collections")
    if list_resp.status_code == 200:
        data = list_resp.json()
        if "collections" in data or "total" in data:
            score += 2

    # 1d: Get collection by ID
    if coll_id:
        get_resp = client.get(f"/api/v1/collections/{coll_id}")
        if get_resp.status_code == 200:
            score += 2

    # 1e: Delete collection
    if coll_id:
        del_resp = client.delete(f"/api/v1/collections/{coll_id}")
        if del_resp.status_code in (200, 204):
            score += 2

    RESULT["procedural_scores"]["check_1_all_endpoints_exist"] = score
    if score < 10:
        missing = 10 - score
        _fail(f"Check 1: {missing // 2} endpoint(s) missing or returning wrong status")

    # --- Check 2: Collections persist data correctly -------------------------
    score = 0
    client2 = _fresh_client()
    if client2 is None:
        _fail("Check 2: failed to reload modules for persistence test")
    else:
        # Create collection in fresh instance
        resp = client2.post(
            "/api/v1/collections",
            json={"name": "Persist Test", "description": "Testing persistence"},
        )
        if resp.status_code in (200, 201):
            body = resp.json()
            cid = body.get("id") or body.get("collection", {}).get("id")
            if cid:
                score += 3
                # Verify it appears in list
                lr = client2.get("/api/v1/collections")
                if lr.status_code == 200:
                    ldata = lr.json()
                    items = ldata.get("collections", ldata.get("data", []))
                    if items is not None and len(items) > 0:
                        score += 4
                # Verify get returns it
                gr = client2.get(f"/api/v1/collections/{cid}")
                if gr.status_code == 200:
                    score += 3

    RESULT["procedural_scores"]["check_2_persistence"] = score
    if score < 10:
        _fail(
            f"Check 2: persistence issues ({score}/10) — data not surviving across requests"
        )

    # --- Check 3: Adding non-existent document returns 404 -------------------
    score = 0
    client3 = _fresh_client()
    if client3 is None:
        _fail("Check 3: failed to reload modules")
    else:
        # Create a collection
        r = client3.post(
            "/api/v1/collections",
            json={"name": "404 Test", "description": ""},
        )
        if r.status_code in (200, 201):
            cid = (r.json().get("id") or r.json().get("collection", {}).get("id"))
            if cid:
                score += 3
                # Try adding fake document
                bad = client3.post(
                    f"/api/v1/collections/{cid}/documents",
                    json={"document_id": "nonexistent_id_12345"},
                )
                if bad.status_code == 404:
                    score += 7
                elif bad.status_code in (400, 422):
                    score += 4  # wrong error code type but at least not 200
                else:
                    _fail(
                        f"Check 3: expected 404, got {bad.status_code}"
                    )

    RESULT["procedural_scores"]["check_3_nonexistent_doc_404"] = score
    if score < 10:
        _fail(f"Check 3: non-existent document handling ({score}/10)")

    # --- Check 4: Deleting collection does NOT delete documents --------------
    score = 0
    client4 = _fresh_client()
    if client4 is None:
        _fail("Check 4: failed to reload modules")
    else:
        # Upload a document
        dr = client4.post(
            "/api/v1/documents/upload",
            files={"file": ("safe.txt", BytesIO(b"safe content"), "text/plain")},
            data={"filename": "safe.txt", "tags": "test"},
        )
        if dr.status_code == 201:
            doc_id = dr.json()["document"]["id"]
            score += 2
            # Create collection and add doc
            cr = client4.post(
                "/api/v1/collections",
                json={"name": "Delete Test", "description": ""},
            )
            if cr.status_code in (200, 201):
                cid = cr.json().get("id") or cr.json().get("collection", {}).get("id")
                if cid:
                    add_r = client4.post(
                        f"/api/v1/collections/{cid}/documents",
                        json={"document_id": doc_id},
                    )
                    if add_r.status_code in (200, 201):
                        score += 2
                        # Delete the collection
                        del_r = client4.delete(f"/api/v1/collections/{cid}")
                        if del_r.status_code in (200, 204):
                            score += 2
                            # Verify document still exists
                            get_doc = client4.get(f"/api/v1/documents/{doc_id}")
                            if get_doc.status_code == 200:
                                score += 4

    RESULT["procedural_scores"]["check_4_delete_collection_spares_docs"] = score
    if score < 10:
        _fail(f"Check 4: document safety after collection delete ({score}/10)")

    # --- Check 5: Listing collection documents returns insertion order --------
    score = 0
    client5 = _fresh_client()
    if client5 is None:
        _fail("Check 5: failed to reload modules")
    else:
        # Upload two docs
        d1 = client5.post(
            "/api/v1/documents/upload",
            files={"file": ("first.txt", BytesIO(b"first"), "text/plain")},
            data={"filename": "first.txt", "tags": "order"},
        )
        d2 = client5.post(
            "/api/v1/documents/upload",
            files={"file": ("second.txt", BytesIO(b"second"), "text/plain")},
            data={"filename": "second.txt", "tags": "order"},
        )
        if d1.status_code == 201 and d2.status_code == 201:
            id1 = d1.json()["document"]["id"]
            id2 = d2.json()["document"]["id"]
            score += 2

            cr = client5.post(
                "/api/v1/collections",
                json={"name": "Order Test", "description": ""},
            )
            if cr.status_code in (200, 201):
                cid = cr.json().get("id") or cr.json().get("collection", {}).get("id")
                if cid:
                    # Add in order: id1 first, then id2
                    a1 = client5.post(
                        f"/api/v1/collections/{cid}/documents",
                        json={"document_id": id1},
                    )
                    a2 = client5.post(
                        f"/api/v1/collections/{cid}/documents",
                        json={"document_id": id2},
                    )
                    if a1.status_code in (200, 201) and a2.status_code in (
                        200,
                        201,
                    ):
                        score += 3
                        # Get collection and check order
                        gr = client5.get(f"/api/v1/collections/{cid}")
                        if gr.status_code == 200:
                            gdata = gr.json()
                            coll = gdata if "collection" not in gdata else gdata["collection"]
                            doc_ids = coll.get("document_ids", [])
                            if len(doc_ids) >= 2:
                                if doc_ids[0] == id1 and doc_ids[1] == id2:
                                    score += 5
                                else:
                                    _fail(
                                        f"Check 5: insertion order wrong — "
                                        f"expected [{id1},{id2}], got {doc_ids[:2]}"
                                    )
                            else:
                                _fail(f"Check 5: expected >=2 doc_ids, got {len(doc_ids)}")

    RESULT["procedural_scores"]["check_5_insertion_order"] = score
    if score < 10:
        _fail(f"Check 5: insertion order violation ({score}/10)")

    RESULT["procedural_total"] = sum(RESULT["procedural_scores"].values())


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENTATION CHECKS  (10 points each, 50 total)
# ══════════════════════════════════════════════════════════════════════════════

def _run_documentation_checks():
    """Check that all documentation artifacts were updated."""

    # --- Check 6: api-reference.md updated -----------------------------------
    score = 0
    api_ref = Path("docs/api-reference.md")
    if api_ref.exists():
        text = api_ref.read_text()
        # Should have sections for the 5 new endpoints
        patterns = [
            (r"(?i)#+\s+.*(create|add).*collection", "Create/Add to collection"),
            (r"(?i)#+\s+.*list.*collection", "List collections"),
            (r"(?i)#+\s+.*get.*collection", "Get collection"),
            (r"(?i)#+\s+.*delete.*collection", "Delete collection"),
            (r"/api/v1/collections", "Collection path reference"),
        ]
        matches = []
        for pat, label in patterns:
            if re.search(pat, text):
                matches.append(label)
                score += 2
        if len(matches) < 3:
            _fail(
                f"Check 6: api-reference.md has {len(matches)}/5 expected "
                f"Collection sections (missing: "
                f"{[l for p, l in patterns if l not in matches]}"
            )
    else:
        _fail("Check 6: docs/api-reference.md not found")

    RESULT["documentation_scores"]["check_6_api_reference_updated"] = min(10, score)

    # --- Check 7: openapi.yaml updated ---------------------------------------
    score = 0
    oapi = Path("docs/openapi.yaml")
    if oapi.exists():
        text = oapi.read_text()
        # 7a: Check for collection path definitions (2 pts per path, max 4)
        path_count = len(re.findall(r"\n\s+/api/v1/collections", text))
        score += min(4, path_count * 1)

        # 7b: Check for collection-related schemas (3 pts)
        schema_refs = len(
            re.findall(
                r"(?i)(Collection|CreateCollection|AddDocumentToCollection|"
                r"CollectionList|CollectionResponse)",
                text,
            )
        )
        if schema_refs >= 3:
            score += 3

        # 7c: Structural validation — verify $ref targets exist (3 pts)
        # Only run if collection paths were actually added
        if path_count >= 1:
            try:
                import yaml

                spec = yaml.safe_load(text)
                components = spec.get("components", {}).get("schemas", {})
                ref_pattern = re.compile(r"#/components/schemas/(\w+)")
                all_refs = set(ref_pattern.findall(text))
                missing = [r for r in all_refs if r not in components]
                if not missing:
                    score += 3
                else:
                    _fail(f"Check 7: broken $ref targets in openapi.yaml: {missing}")
            except Exception:
                _fail("Check 7: could not parse openapi.yaml for structural validation")

        if score < 5:
            _fail(
                f"Check 7: openapi.yaml has {path_count} collection path(s) and"
                f" ~{schema_refs} schema reference(s)"
            )
    else:
        _fail("Check 7: docs/openapi.yaml not found")

    RESULT["documentation_scores"]["check_7_openapi_updated"] = min(10, score)

    # --- Check 8: CHANGELOG.md updated ---------------------------------------
    score = 0
    cl = Path("CHANGELOG.md")
    if cl.exists():
        text = cl.read_text()
        has_collections = re.search(r"(?i)collection", text) is not None
        has_endpoints = re.search(r"(?i)(POST|GET|DELETE)\s+/api/v1/collection", text) is not None
        if has_collections and has_endpoints:
            score = 10
        elif has_collections:
            score = 5
            _fail("Check 8: CHANGELOG mentions Collections but not specific endpoint paths")
        else:
            _fail("Check 8: CHANGELOG.md has no Collections entry")
    else:
        _fail("Check 8: CHANGELOG.md not found")

    RESULT["documentation_scores"]["check_8_changelog_updated"] = score

    # --- Check 9: Route functions have docstrings ----------------------------
    score = 0
    router_path = Path("app/routers/collections.py")
    if router_path.exists():
        text = router_path.read_text()
        # Count function definitions with docstrings immediately after
        # Match: async def func_name(...):\n    """some docstring"""
        funcs_with_docs = len(
            re.findall(
                r"async\s+def\s+\w+\([^)]*\):\s*\n\s+\"\"\"[^\"]+\"\"\"",
                text,
            )
        ) + len(
            re.findall(
                r"def\s+\w+\([^)]*\):\s*\n\s+\"\"\"[^\"]+\"\"\"",
                text,
            )
        )
        # There should be at least 5 route functions
        total_funcs = len(re.findall(r"async\s+def\s+\w+", text)) + len(
            re.findall(r"^(?!async\s)def\s+\w+", text, re.MULTILINE)
        )
        if total_funcs >= 5 and funcs_with_docs >= 5:
            score = 10
        elif funcs_with_docs >= 4:
            score = 8
            _fail(f"Check 9: only {funcs_with_docs} of {total_funcs} route functions have docstrings")
        elif funcs_with_docs >= 1:
            score = 4
            _fail(f"Check 9: only {funcs_with_docs} of {total_funcs} route functions have docstrings")
        else:
            _fail("Check 9: no docstrings found in collections.py")
    else:
        _fail("Check 9: app/routers/collections.py not found")

    RESULT["documentation_scores"]["check_9_route_docstrings"] = score

    # --- Check 10: README references Collections -----------------------------
    score = 0
    readme = Path("README.md")
    if readme.exists():
        text = readme.read_text()
        has_mention = re.search(r"(?i)collection", text) is not None

        # Check endpoint table has collection rows
        table_has_collections = bool(
            re.search(r"\|\s*`(POST|GET|DELETE)`\s+\|\s*`/api/v1/collections", text)
        )

        if has_mention and table_has_collections:
            score = 10
        elif has_mention:
            score = 5
            _fail("Check 10: README mentions Collections but endpoint table not updated")
        else:
            _fail("Check 10: README does not mention Collections")
    else:
        _fail("Check 10: README.md not found")

    RESULT["documentation_scores"]["check_10_readme_updated"] = score

    RESULT["documentation_total"] = sum(RESULT["documentation_scores"].values())


# ══════════════════════════════════════════════════════════════════════════════
# LLM GRADER  (0-10 points)
# ══════════════════════════════════════════════════════════════════════════════

def _run_llm_check():
    """Use Anthropic API to evaluate documentation consistency."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        _fail("LLM check skipped: ANTHROPIC_API_KEY not set")
        RESULT["llm_score"] = 0
        return

    # Gather existing and new documentation excerpts
    api_ref = Path("docs/api-reference.md")
    oapi = Path("docs/openapi.yaml")

    existing_excerpt = ""
    new_excerpt = ""

    if api_ref.exists():
        text = api_ref.read_text()
        # Split: sections before "Collections" vs after
        coll_idx = re.search(r"(?i)^#{1,4}\s+.*collection", text, re.MULTILINE)
        if coll_idx:
            # Heuristic: existing docs are before first collection mention,
            # new docs include that section and beyond
            split_point = text.rfind("\n---", 0, coll_idx.start())
            if split_point == -1:
                split_point = text.rfind("\n## ", 0, coll_idx.start())
            if split_point > 0:
                existing_excerpt = text[:split_point].strip()
                new_excerpt = text[split_point:].strip()
            else:
                existing_excerpt = text[: coll_idx.start()].strip()
                new_excerpt = text[coll_idx.start() :].strip()
        else:
            # No new docs at all
            existing_excerpt = text.strip()

    if oapi.exists():
        yaml_text = oapi.read_text()
        # Similar split for YAML
        coll_yaml_idx = re.search(r"/api/v1/collections", yaml_text)
        if coll_yaml_idx:
            existing_excerpt += "\n\n--- YAML EXISTING ---\n" + yaml_text[
                : coll_yaml_idx.start()
            ].strip()
            new_excerpt += "\n\n--- YAML NEW ---\n" + yaml_text[
                coll_yaml_idx.start() :
            ].strip()

    if not new_excerpt:
        _fail("LLM check: no new documentation content detected to evaluate")
        RESULT["llm_score"] = 0
        return

    # Build prompt
    prompt = f"""You are evaluating a software engineer's documentation updates for consistency.

Below is the EXISTING documentation (style, depth, format to match):

{existing_excerpt[:6000]}

Below is the NEW documentation added for a "Collections" feature:

{new_excerpt[:6000]}

Rate the new documentation on a scale of 0-10 for how consistent it is with the existing documentation in:
- Level of detail (parameter tables, response examples, error cases)
- Formatting conventions (header hierarchy, table structure, code blocks)
- Tone and writing style
- Completeness (all endpoints covered, edge cases documented)

Respond with ONLY a single integer between 0 and 10. No explanation."""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        score = int(re.search(r"\d+", raw).group(0))
        score = max(0, min(10, score))
        RESULT["llm_score"] = score
    except ImportError:
        # Fallback: use requests directly
        import requests

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 10,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data["content"][0]["text"].strip()
            score = int(re.search(r"\d+", raw).group(0))
            score = max(0, min(10, score))
            RESULT["llm_score"] = score
        else:
            _fail(f"LLM check: Anthropic API returned {resp.status_code}")
            RESULT["llm_score"] = 0
    except Exception as e:
        _fail(f"LLM check failed: {e}")
        RESULT["llm_score"] = 0


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Collections Feature Benchmark — Grader")
    print("=" * 60)
    print()

    # 1. Procedural checks
    print("Running procedural checks...")
    _run_procedural_checks()
    print(f"  Procedural: {RESULT['procedural_total']}/{PROCEDURAL_MAX}")
    for k, v in RESULT["procedural_scores"].items():
        print(f"    {k}: {v}/10")

    print()

    # 2. Documentation checks
    print("Running documentation checks...")
    _run_documentation_checks()
    print(f"  Documentation: {RESULT['documentation_total']}/{DOC_MAX}")
    for k, v in RESULT["documentation_scores"].items():
        print(f"    {k}: {v}/10")

    print()

    # 3. LLM check
    print("Running LLM documentation consistency check...")
    _run_llm_check()
    print(f"  LLM consistency score: {RESULT['llm_score']}/10")

    # 4. Total
    RESULT["total"] = (
        RESULT["procedural_total"]
        + RESULT["documentation_total"]
        + RESULT["llm_score"]
    )
    max_score = PROCEDURAL_MAX + DOC_MAX + 10
    print(f"\n  TOTAL: {RESULT['total']}/{max_score}")

    if RESULT["failure_reasons"]:
        print("\n  Failures:")
        for reason in RESULT["failure_reasons"]:
            print(f"    - {reason}")

    print()

    # Write JSON output
    output = json.dumps(RESULT, indent=2, default=str)
    Path("grader_output.json").write_text(output)
    print("Results written to grader_output.json")
    return RESULT["total"]


if __name__ == "__main__":
    main()
