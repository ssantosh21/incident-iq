# Incident Responder - PoC Scope

## Goal
Build a **production-ready PoC** that demonstrates the core value proposition without full production complexity.

---

## What We're Building

### Core Features
1. **Incident Deduplication**: Vector similarity search (>0.7 = duplicate)
2. **Runbook Matching**: Automatic runbook recommendations (>0.7 = matched)
3. **Regression Detection**: Flags when RESOLVED incidents recur
4. **Incident Lifecycle**: OPEN → RESOLVED
5. **Local Storage**: JSON files (simulates S3/Jira)
6. **REST API**: FastAPI endpoints

### Flow

```
Incident Reported
    ↓
Search Pinecone (similarity > 0.7)
    ↓
    ├─→ Found & OPEN
    │   └─→ Update occurrences, add comment
    │
    ├─→ Found & RESOLVED
    │   └─→ Create NEW incident (REGRESSION!)
    │       Severity = HIGH
    │
    └─→ Not Found
        └─→ Search runbooks (>0.7)
            ├─→ Matched: Store with runbook solution
            └─→ No match: Store with "No runbook found"
```

---

## Architecture (Simplified)

```
┌─────────────────────────────────────┐
│   Manual Incident Reporting         │
│   (POST /incident)                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Incident Responder API          │
│         (FastAPI)                    │
│                                      │
│  Endpoints:                          │
│  • POST /incident                    │
│  • POST /resolve                     │
│  • GET  /incidents                   │
│  • GET  /incidents/{id}              │
└──────┬──────────────┬────────────────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────────┐
│  Pinecone   │  │ Local JSON   │
│             │  │              │
│ Vector      │  │ ./data/      │
│ Search      │  │  incidents/  │
│             │  │  runbooks/   │
└─────────────┘  └──────────────┘
```

---

## Data Storage

### Local JSON Structure
```
ai-learning/project8/data/
  incidents/
    inc_abc123.json
    inc_def456.json
  runbooks/
    rb_lambda_timeout.json
    rb_dynamodb_throttle.json
```

### Incident JSON
```json
{
  "incident_id": "inc_abc123",
  "error_message": "Lambda function timeout after 30 seconds...",
  "service": "payment-processor",
  "severity": "MEDIUM",
  "status": "OPEN",
  "runbook_matched": true,
  "runbook_similarity": 0.89,
  "recommended_runbooks": [
    {
      "title": "Lambda Timeout",
      "similarity": 0.89
    }
  ],
  "created_at": "2024-02-12T10:30:00Z",
  "last_seen": "2024-02-12T10:30:00Z",
  "occurrences": 1,
  "history": [
    {
      "timestamp": "2024-02-12T10:30:00Z",
      "event": "created"
    }
  ],
  "resolution": null,
  "resolved_at": null
}
```

---

## Configuration

### Thresholds (configurable)
```python
SIMILARITY_THRESHOLD = 0.7  # For deduplication
RUNBOOK_MATCH_THRESHOLD = 0.7  # For runbook matching
DEFAULT_SEVERITY = "MEDIUM"
REGRESSION_SEVERITY = "HIGH"
```

---

## API Endpoints

### 1. Report Incident
```bash
POST /incident
{
  "error": "Lambda timeout after 30s...",
  "service": "payment-processor"
}

Response:
{
  "status": "new" | "existing" | "regression",
  "incident_id": "inc_abc123",
  "runbook_matched": true,
  "recommendations": "...",
  "severity": "MEDIUM"
}
```

### 2. Resolve Incident
```bash
POST /resolve
{
  "incident_id": "inc_abc123",
  "resolution": "Increased timeout to 60s"
}

Response:
{
  "status": "success",
  "incident_id": "inc_abc123"
}
```

### 3. List Incidents
```bash
GET /incidents?status=OPEN

Response:
{
  "incidents": [
    {
      "incident_id": "inc_abc123",
      "error_message": "...",
      "status": "OPEN",
      "occurrences": 3
    }
  ]
}
```

### 4. Get Incident Details
```bash
GET /incidents/inc_abc123

Response:
{
  "incident_id": "inc_abc123",
  "error_message": "...",
  "status": "OPEN",
  "history": [...]
}
```

---

## What's Missing (Future Production Features)

### Not in PoC:
1. **CloudWatch Integration**: Manual POST instead of auto-ingestion
2. **Jira Integration**: JSON files instead of real tickets
3. **Multi-tenant**: Single namespace (easy to add later)
4. **Authentication**: No API keys (add later)
5. **Analytics Dashboard**: No UI (API only)
6. **Slack Notifications**: No integrations
7. **AWS Deployment**: Local only (deploy later)

### Easy to Add Later:
- CloudWatch → Lambda → POST /incident (just add Lambda)
- JSON files → S3 (change storage layer)
- Single tenant → Multi-tenant (add namespace parameter)
- No auth → API keys (add middleware)

---

## Success Criteria

### PoC is successful if:
1. ✅ Deduplicates incidents correctly (>0.7 similarity)
2. ✅ Matches runbooks accurately (>0.7 similarity)
3. ✅ Detects regressions (RESOLVED → recurs → HIGH severity)
4. ✅ Stores incident history in JSON
5. ✅ API works end-to-end
6. ✅ Test suite passes

---

## Timeline

**Phase 1 (Today)**: Core implementation
- Update agents with new flow
- Add JSON storage layer
- Implement regression detection
- Update API endpoints

**Phase 2 (Next)**: Testing & Polish
- Test suite
- Error handling
- Documentation
- Demo script

---

## Portfolio Value

This PoC demonstrates:
- **AI/ML**: Vector embeddings, semantic search, RAG
- **System Design**: Incident management, deduplication, state machine
- **Production Patterns**: Proper error handling, logging, data models
- **AWS Knowledge**: Designed for CloudWatch, S3, Lambda (even if not deployed)
- **API Design**: RESTful, clean endpoints
- **Python**: FastAPI, Pydantic, async patterns

---

## Next Steps

1. Implement JSON storage layer
2. Update incident flow with regression detection
3. Add new API endpoints (list, get details)
4. Create test suite
5. Write demo script

Ready to build?
