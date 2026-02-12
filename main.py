from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import IncidentAnalyzerAgent, RunbookRetrieverAgent, RecommendationAgent
from datetime import timedelta
import storage
import config
import time
import uuid
import auth

load_dotenv()

app = FastAPI(title="Incident Responder API", version="2.0.0")


class IncidentRequest(BaseModel):
    log: str
    service: str = "unknown"


class ResolveIncidentRequest(BaseModel):
    incident_id: str
    resolution: str
    resolved_by: str = "system"


class IncidentResponder:
    """
    Orchestrates the three agents to respond to incidents.
    
    Flow:
    1. Search Pinecone for similar incident
    2. If found (OPEN): Add comment to S3 ticket
    3. If found (RESOLVED): Create new incident (regression)
    4. If not found: Create S3 ticket + Pinecone entry
    """
    
    def __init__(self):
        self.analyzer = IncidentAnalyzerAgent()
        self.retriever = RunbookRetrieverAgent()
        self.recommender = RecommendationAgent()
    
    def respond(self, incident_log: str, service: str = "unknown") -> dict:
        """
        Handle incident with deduplication and regression detection.
        """
        start_time = time.time()
        
        try:
            # Step 1: Search for similar incident in Pinecone
            print("\n=== STEP 1: SEARCH PINECONE ===")
            analysis_result = self.analyzer.execute(incident_log)
            incident_status = analysis_result["status"]  # new, existing, or regression
            
            # Step 2: Get runbooks (always needed)
            print("\n=== STEP 2: GET RUNBOOKS ===")
            runbook_result = self.retriever.execute(incident_log)
            runbook_matched = len(runbook_result["runbooks"]) > 0 and runbook_result["runbooks"][0]["similarity"] > config.RUNBOOK_MATCH_THRESHOLD
            
            # Case 1: Existing incident (OPEN)
            if incident_status == "existing":
                duplicate = analysis_result["duplicate_found"]
                s3_key = duplicate.get("s3_key")  # Get S3 key from duplicate (from Pinecone metadata)
                
                # Add comment to S3 ticket
                if s3_key:
                    storage.add_ticket_comment(
                        incident_id=duplicate["id"],
                        event="recurred",
                        comment=f"Same incident reported again (similarity: {duplicate['similarity']:.3f})",
                        s3_key=s3_key
                    )
                    print(f"[Orchestrator] Added comment to S3 ticket: {s3_key}")
                else:
                    print(f"[Orchestrator] WARNING: No S3 key found for incident {duplicate['id']}")
                
                print(f"EXISTING INCIDENT - Added comment to S3")
                
                total_time = time.time() - start_time
                
                return {
                    "status": "existing",
                    "incident_id": duplicate["id"],
                    "incident": incident_log,
                    "similarity": duplicate["similarity"],
                    "ticket_status": duplicate["incident_data"].get("status"),
                    "occurrences": duplicate["incident_data"].get("occurrences", 1) + 1,
                    "runbooks": runbook_result["runbooks"],
                    "recommendations": duplicate["incident_data"].get("recommendations"),
                    "response_time_seconds": round(total_time, 2)
                }
            
            # Case 2: Regression (RESOLVED incident recurring)
            elif incident_status == "regression":
                duplicate = analysis_result["duplicate_found"]
                
                print(f"REGRESSION DETECTED - Creating new incident with HIGH severity")
                
                # Generate recommendations
                recommendation_result = self.recommender.execute(
                    incident_log,
                    analysis_result["similar_incidents"],
                    runbook_result["runbooks"]
                )
                
                # Create new incident with HIGH severity
                incident_id = f"inc_{uuid.uuid4().hex[:8]}"
                
                result = storage.create_incident(
                    incident_id=incident_id,
                    error_message=incident_log,
                    service=service,
                    severity=config.REGRESSION_SEVERITY,  # HIGH
                    runbook_matched=runbook_matched,
                    recommended_runbooks=[{"title": rb["title"], "similarity": rb["similarity"]} for rb in runbook_result["runbooks"]],
                    recommendations=f"REGRESSION of {duplicate['id']}\n\n{recommendation_result['recommendations']}"
                )
                
                total_time = time.time() - start_time
                
                return {
                    "status": "regression",
                    "incident_id": incident_id,
                    "incident": incident_log,
                    "severity": config.REGRESSION_SEVERITY,
                    "regression_of": duplicate["id"],
                    "similarity": duplicate["similarity"],
                    "runbooks": runbook_result["runbooks"],
                    "recommendations": recommendation_result["recommendations"],
                    "response_time_seconds": round(total_time, 2)
                }
            
            # Case 3: New incident
            else:
                print("NEW INCIDENT - Creating S3 ticket + Pinecone entry")
                
                # Generate recommendations
                recommendation_result = self.recommender.execute(
                    incident_log,
                    analysis_result["similar_incidents"],
                    runbook_result["runbooks"]
                )
                
                # Create incident (S3 first, then Pinecone)
                incident_id = f"inc_{uuid.uuid4().hex[:8]}"
                
                result = storage.create_incident(
                    incident_id=incident_id,
                    error_message=incident_log,
                    service=service,
                    severity=config.DEFAULT_SEVERITY,
                    runbook_matched=runbook_matched,
                    recommended_runbooks=[{"title": rb["title"], "similarity": rb["similarity"]} for rb in runbook_result["runbooks"]],
                    recommendations=recommendation_result["recommendations"]
                )
                
                total_time = time.time() - start_time
                
                print(f"COMPLETE in {total_time:.2f}s\n")
                
                return {
                    "status": "new",
                    "incident_id": incident_id,
                    "incident": incident_log,
                    "severity": config.DEFAULT_SEVERITY,
                    "service": service,
                    "runbook_matched": runbook_matched,
                    "runbooks": runbook_result["runbooks"],
                    "recommendations": recommendation_result["recommendations"],
                    "response_time_seconds": round(total_time, 2)
                }
            
        except Exception as e:
            print(f"ERROR: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Initialize responder
responder = IncidentResponder()


@app.get("/")
def read_root():
    return {
        "message": "Intelligent Incident Responder - PoC",
        "version": "2.0.0",
        "architecture": {
            "pinecone": "Incident search & deduplication (with full error logs)",
            "s3": "Ticket tracking (status, comments, resolution)"
        },
        "authentication": "JWT Bearer token required for protected endpoints",
        "flow": [
            "1. POST /login to get JWT token",
            "2. Include token in Authorization header: Bearer <token>",
            "3. Search Pinecone for similar incident",
            "4. If found (OPEN): Add comment to S3 ticket",
            "5. If found (RESOLVED): Create new incident (regression, HIGH severity)",
            "6. If not found: Create S3 ticket + Pinecone entry"
        ],
        "endpoints": {
            "/login": "POST - Login and get JWT token (public)",
            "/me": "GET - Get current user info (protected)",
            "/incident": "POST - Report an incident (protected)",
            "/resolve": "POST - Mark incident as resolved (protected)",
            "/incidents": "GET - List all incidents (protected)",
            "/incidents/{id}": "GET - Get incident details (protected)",
            "/health": "GET - Health check (public)"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/login", response_model=auth.Token)
def login(login_request: auth.LoginRequest):
    """
    Login with username and password to get JWT token.
    
    Example:
    ```
    POST /login
    {
        "username": "admin",
        "password": "secret"
    }
    ```
    
    Returns JWT token that expires in 1 hour.
    """
    # Authenticate user
    user = auth.authenticate_user(login_request.username, login_request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/me")
def read_users_me(current_user: auth.User = Depends(auth.get_current_active_user)):
    """
    Get current user information.
    Requires JWT token in Authorization header.
    
    Example:
    ```
    GET /me
    Authorization: Bearer <your-jwt-token>
    ```
    """
    return {
        "username": current_user.username,
        "email": current_user.email,
        "disabled": current_user.disabled
    }


# ============================================
# Protected Incident Endpoints
# ============================================

@app.post("/incident")
def handle_incident(
    request: IncidentRequest,
    current_user: auth.User = Depends(auth.get_current_active_user)
):
    """
    Handle an incident with deduplication and regression detection.
    
    🔒 Protected: Requires JWT token
    
    Flow:
    - Search Pinecone for similar incident (>0.7 similarity)
    - If found (OPEN): Add comment to S3, return existing
    - If found (RESOLVED): Create new incident (regression)
    - If new: Create S3 ticket + Pinecone entry
    
    Example:
    ```
    POST /incident
    Authorization: Bearer <your-jwt-token>
    {
        "log": "Lambda timeout after 30s",
        "service": "payment-service"
    }
    ```
    """
    print(f"[API] Incident reported by user: {current_user.username}")
    result = responder.respond(request.log, request.service)
    return result


@app.post("/resolve")
def resolve_incident(
    request: ResolveIncidentRequest,
    current_user: auth.User = Depends(auth.get_current_active_user)
):
    """
    Mark an incident as resolved.
    
    🔒 Protected: Requires JWT token
    
    Updates S3 ticket with resolution details.
    """
    print(f"[API] Incident resolved by user: {current_user.username}")
    
    success = storage.resolve_ticket(
        incident_id=request.incident_id,
        resolution=request.resolution,
        resolved_by=current_user.username  # Use actual username
    )
    
    if success:
        return {
            "status": "success",
            "incident_id": request.incident_id,
            "resolution": request.resolution,
            "resolved_by": current_user.username
        }
    else:
        return {
            "status": "error",
            "error": f"Incident {request.incident_id} not found"
        }


@app.get("/incidents")
def list_incidents(
    status: str = None,
    current_user: auth.User = Depends(auth.get_current_active_user)
):
    """
    List all incidents from S3.
    
    🔒 Protected: Requires JWT token
    
    Optional query param: ?status=OPEN or ?status=RESOLVED
    """
    tickets = storage.list_tickets(status=status)
    
    return {
        "status": "success",
        "count": len(tickets),
        "incidents": tickets
    }


@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    current_user: auth.User = Depends(auth.get_current_active_user)
):
    """
    Get full incident details from S3.
    
    🔒 Protected: Requires JWT token
    """
    ticket = storage.load_ticket(incident_id)
    
    if ticket:
        return {
            "status": "success",
            "incident": ticket
        }
    else:
        return {
            "status": "error",
            "error": f"Incident {incident_id} not found"
        }
