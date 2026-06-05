# AI Script Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP demo for the PRD core chain: enter product information, generate an AI script, display results, save records, and export a CSV.

**Architecture:** Use a Python standard-library HTTP server for API and static-file serving. Keep reusable business logic in `src/demo_core.py`, AI client logic in `src/ai_client.py`, and browser UI in `web/`.

**Tech Stack:** Python 3 standard library, vanilla HTML/CSS/JavaScript, DeepSeek Chat Completions API via HTTPS, JSONL persistence, CSV export.

---

### Task 1: Core Domain Behavior

**Files:**
- Create: `tests/test_demo_core.py`
- Create: `src/demo_core.py`

- [ ] Write tests for product validation, demo script generation, risk scanning, and CSV export.
- [ ] Run `python -m unittest discover -s tests -v` and confirm tests fail because `src.demo_core` does not exist.
- [ ] Implement `ProductBrief`, `validate_product_brief`, `generate_demo_script`, `scan_risks`, and `scripts_to_csv`.
- [ ] Run tests and confirm they pass.

### Task 2: AI Client

**Files:**
- Create: `tests/test_ai_client.py`
- Create: `src/ai_client.py`

- [ ] Write tests for extracting text from DeepSeek Chat Completions payloads and JSON parsing.
- [ ] Run tests and confirm they fail because `src.ai_client` does not exist.
- [ ] Implement prompt building, response text extraction, JSON repair parsing, and optional real DeepSeek call when `DEEPSEEK_API_KEY` exists.
- [ ] Run tests and confirm they pass.

### Task 3: Web Server

**Files:**
- Create: `server.py`
- Create: `data/.gitkeep`

- [ ] Implement static serving for `web/`.
- [ ] Implement `POST /api/generate`, `POST /api/save`, `GET /api/scripts`, and `GET /api/export.csv`.
- [ ] Persist saved scripts as JSONL in `data/saved_scripts.jsonl`.
- [ ] Keep no-key environments usable through explicit demo mode.

### Task 4: Browser UI

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`

- [ ] Build a simple operational page with product input form, generation button, result area, saved table, and export link.
- [ ] Show whether generation used real AI or demo mode.

### Task 5: Verification

**Files:**
- Modify: none

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Start `python server.py`.
- [ ] Call `/api/generate`, `/api/save`, `/api/scripts`, and `/api/export.csv`.
- [ ] Open the browser page and verify the core chain can run end-to-end.
