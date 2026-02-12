# Incident Responder PoC - Implementation Tasks

## Overview
Build production-ready PoC with local JSON storage, deduplication, regression detection, and runbook matching.

---

## Task 1: Configuration & Constants
**Status**: ⏳ Pending

**Goal**: Create centralized configuration file

**Files to create**:
- `config.py`

**Requirements**:
```python
# Thresholds
SIMILARITY_THRESHOLD = 0.7
RUNBOOK_MATCH_THRESHOLD = 0.7

# Severity levels
DEFAULT_SEVERITY = "MEDIUM"
REGRESSION_SEVERITY = "HIGH"

# Storage paths
DATA_DIR = "./data"
INCIDENTS_DIR = "./data/incidents"
RUNBOOKS_DIR = "./data/runbooks"

# Pinecone
INDEX_NAME = "incident-responder"
```

**Acceptance Criteria**:
- ✅ All thresholds configurable in one place
- ✅ Directory paths defined
- ✅ Easy to change values

---

## Task 2: JSON Storage Layer
**Status**: ⏳ Pending

**Goal**: Create storage module for reading/writing incident and runbook JSON files

**Files to create**:
- `storage.py`

**Requirements**:

### Functions needed:
1. `save_incident(incident_data: dict) -> str`
   - Save incident to `data/incidents/{incident_id}.json`
   - Create directory if not exists
   - Return incident_id

2. `load_incident(incident_id: str) -> dict`
   - Load incident from JSON
   - Return dict or None if not found

3. `update_incident(incident_id: str, updates: dict) -> bool`
   - Update specific fields in incident JSON
   - Preserve existing data
   - Return success/failure

4. `list_incidents(status: str = None) -> list`
   - List all incidents
   - Filter by status if provided (OPEN, RESOLVED)
   - Return list of incident dicts

5. `add_incident_history(incident_id: str, event: str, comment: str = None)`
   - Append to history array
   - Include timestamp

**Acceptance Criteria**:
- ✅ Creates data directories automatically
- ✅ Handles file not found gracefully
- ✅ Atomic writes (write to temp, then rename)
- ✅ Pretty-printed JSON (indent=2)

---

## Task 3: Update Incident Analyzer Agent
**Status**: ⏳ Pending

**Goal**: Enhance IncidentAnalyzerAgent to support regression detection

**Files to modify**:
- `agents.py`

**Requirements**:

### Update `IncidentAnalyzerAgent.execute()`:
1. Search Pinecone for similar incidents (>0.7)
2. If found:
   - Load full incident from JSON (via storage.py)
   - Check status:
     - If OPEN: Return as "existing"
     - If RESOLVED: Return as "regression"
3. If not found: Return as "new"

**Return format**:
```python
{
  "status": "new" | "existing" | "regression",
  "incident": incident_log,
  "duplicate_found": {
    "id": "inc_abc123",
    "text": "...",
    "similarity": 0.89,
    "status": "OPEN" | "RESOLVED",
    "incident_data": {...}  # Full JSON data
  } if found else None,
  "similar_incidents": [...]
}
```

**Acceptance Criteria**:
- ✅ Correctly identifies existing incidents
- ✅ Detects regressions (RESOLVED → recurs)
- ✅ Returns full incident data from JSON

---

## Task 4: Update Incident Responder Orchestrator
**Status**: ⏳ Pending

**Goal**: Implement complete incident flow with JSON storage

**Files to modify**:
- `main.py`

**Requirements**:

### Update `IncidentResponder.respond()`:

**Case 1: Existing incident (OPEN)**
```python
- Load incident from JSON
- Increment occurrences
- Update last_seen timestamp
- Add history entry: "recurred"
- Save back to JSON
- Update Pinecone metadata (occurrences, last_seen)
- Return existing incident + runbooks
```

**Case 2: Regression (RESOLVED)**
```python
- Create NEW incident
- Set severity = HIGH
- Add note: "Regression of incident {old_id}"
- Run through runbooks
- Save to JSON
- Store in Pinecone
- Return as "regression"
```

**Case 3: New incident**
```python
- Search runbooks (>0.7 = matched)
- Generate recommendations
- Create incident JSON:
  {
    "incident_id": "inc_...",
    "error_message": "...",
    "service": "...",
    "severity": "MEDIUM",
    "status": "OPEN",
    "runbook_matched": true/false,
    "runbook_similarity": 0.89,
    "recommended_runbooks": [...],
    "created_at": "...",
    "last_seen": "...",
    "occurrences": 1,
    "history": [{"timestamp": "...", "event": "created"}],
    "resolution": null,
    "resolved_at": null
  }
- Save to JSON
- Store in Pinecone
- Return as "new"
```

**Acceptance Criteria**:
- ✅ All three cases handled correctly
- ✅ JSON files created/updated properly
- ✅ Pinecone metadata stays in sync with JSON
- ✅ History tracking works

---

## Task 5: Update API Endpoints
**Status**: ⏳ Pending

**Goal**: Add new endpoints and update existing ones

**Files to modify**:
- `main.py`

**Requirements**:

### 1. Update `POST /incident`
- Return enhanced response with status (new/existing/regression)
- Include runbook_matched boolean
- Include severity

### 2. Update `POST /resolve`
- Load incident from JSON
- Update status = "RESOLVED"
- Add resolution text
- Add resolved_at timestamp
- Add history entry: "resolved"
- Save to JSON
- Update Pinecone metadata

### 3. Add `GET /incidents`
- Query params: `?status=OPEN` (optional)
- Use `storage.list_incidents()`
- Return list of incidents

### 4. Add `GET /incidents/{incident_id}`
- Use `storage.load_incident()`
- Return full incident details
- 404 if not found

**Acceptance Criteria**:
- ✅ All endpoints work correctly
- ✅ Proper error handling (404, 500)
- ✅ Response formats consistent

---

## Task 6: Update Ingestion Script
**Status**: ⏳ Pending

**Goal**: Remove log ingestion, keep only runbooks and sample resolved incidents

**Files to modify**:
- `ingestion.py`

**Requirements**:
1. Remove `ingest_log()` function
2. Keep `ingest_runbook()` function
3. Keep `ingest_resolved_incident()` function
4. Update main block to only ingest:
   - 5 runbooks (from sample_runbooks.py)
   - 2 sample resolved incidents (for demo)

**Acceptance Criteria**:
- ✅ No log ingestion
- ✅ Only runbooks and resolved incidents
- ✅ Clean, simple script

---

## Task 7: Create Test Suite
**Status**: ⏳ Pending

**Goal**: Comprehensive test script demonstrating all flows

**Files to create**:
- `test_complete_flow.py`

**Requirements**:

### Test Cases:
1. **Test: New Incident**
   - Report incident not in Pinecone
   - Verify: status="new", JSON created, runbook matched

2. **Test: Existing Incident (OPEN)**
   - Report same incident again
   - Verify: status="existing", occurrences incremented, history updated

3. **Test: Resolve Incident**
   - Mark incident as resolved
   - Verify: status="RESOLVED", resolution saved

4. **Test: Regression**
   - Report same incident after resolution
   - Verify: status="regression", severity="HIGH", new incident created

5. **Test: No Runbook Match**
   - Report incident with no matching runbook (<0.7)
   - Verify: runbook_matched=false, generic recommendations

6. **Test: List Incidents**
   - GET /incidents?status=OPEN
   - Verify: Returns only OPEN incidents

7. **Test: Get Incident Details**
   - GET /incidents/{id}
   - Verify: Returns full incident data

**Acceptance Criteria**:
- ✅ All test cases pass
- ✅ Clear output showing each test
- ✅ Demonstrates complete flow

---

## Task 8: Documentation & Demo
**Status**: ⏳ Pending

**Goal**: Create README and demo script

**Files to create**:
- `README.md` (update existing)
- `DEMO.md`

**Requirements**:

### README.md:
- Project overview
- Architecture diagram (ASCII)
- Setup instructions
- API documentation
- Configuration options

### DEMO.md:
- Step-by-step demo script
- Example curl commands
- Expected outputs
- Screenshots of JSON files

**Acceptance Criteria**:
- ✅ Clear, professional documentation
- ✅ Easy for someone else to run
- ✅ Shows all features

---

## Task 9: Error Handling & Logging
**Status**: ⏳ Pending

**Goal**: Add proper error handling and logging throughout

**Files to modify**:
- All files

**Requirements**:
1. Add try-except blocks in all functions
2. Use Python logging module
3. Log levels:
   - INFO: Normal operations
   - WARNING: Recoverable issues
   - ERROR: Failures
4. Return proper error responses from API

**Acceptance Criteria**:
- ✅ No unhandled exceptions
- ✅ Clear error messages
- ✅ Logs help with debugging

---

## Task 10: Cleanup & Polish
**Status**: ⏳ Pending

**Goal**: Final cleanup and polish

**Requirements**:
1. Remove old/unused code
2. Add docstrings to all functions
3. Format code (black, isort)
4. Update requirements.txt
5. Add .gitignore for data/ directory
6. Final testing

**Acceptance Criteria**:
- ✅ Clean, professional code
- ✅ No dead code
- ✅ Consistent formatting
- ✅ Ready for portfolio

---

## Execution Order

1. Task 1: Configuration (5 min)
2. Task 2: Storage Layer (15 min)
3. Task 3: Update Analyzer (10 min)
4. Task 4: Update Orchestrator (20 min)
5. Task 5: Update API (15 min)
6. Task 6: Update Ingestion (5 min)
7. Task 7: Test Suite (20 min)
8. Task 8: Documentation (15 min)
9. Task 9: Error Handling (10 min)
10. Task 10: Cleanup (10 min)

**Total Estimated Time**: ~2 hours

---

## Success Criteria (Overall)

PoC is complete when:
- ✅ All 10 tasks completed
- ✅ Test suite passes 100%
- ✅ Documentation clear and complete
- ✅ Demo runs smoothly
- ✅ Code is portfolio-ready
- ✅ Easy to extend to production later

---

Ready to start with Task 1?
