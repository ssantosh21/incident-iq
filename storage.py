"""
Storage Layer: Pinecone (incidents + runbooks) + S3 (ticket tracking)

Architecture:
- Pinecone: Stores incidents and runbooks with full details (for search/deduplication)
- S3: Stores ticket-like tracking (status, comments, resolution) - replaces Jira

Flow:
1. Incident reported → Store in Pinecone (full error log)
2. Create ticket in S3 (status, comments, resolution tracking)
3. Search/deduplicate → Query Pinecone
4. Update status/resolution → Update S3 ticket
"""
import json
from datetime import datetime
from typing import Optional, List, Dict
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import config

load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
model = SentenceTransformer(config.EMBEDDING_MODEL)
pinecone_index = pc.Index(config.INDEX_NAME)

# Initialize S3 with profile
session = boto3.Session(profile_name=config.AWS_PROFILE)
s3_client = session.client('s3')


def ensure_s3_bucket():
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=config.S3_BUCKET)
        print(f"[S3] Bucket {config.S3_BUCKET} exists")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            try:
                s3_client.create_bucket(Bucket=config.S3_BUCKET)
                print(f"[S3] Created bucket: {config.S3_BUCKET}")
            except ClientError as create_error:
                print(f"[S3] Error creating bucket: {create_error}")
        else:
            print(f"[S3] Error checking bucket: {e}")


def create_incident(incident_id: str, error_message: str, service: str, severity: str, 
                   runbook_matched: bool, recommended_runbooks: list, recommendations: str) -> dict:
    """
    Create a new incident: S3 ticket first, then Pinecone entry.
    This ensures Pinecone always has a valid S3 key.
    
    Args:
        incident_id: Incident ID
        error_message: Full error message
        service: Service name
        severity: Severity level
        runbook_matched: Whether runbook was matched
        recommended_runbooks: List of recommended runbooks
        recommendations: AI-generated recommendations
        
    Returns:
        dict with incident_id and s3_key
    """
    ensure_s3_bucket()
    
    # Step 1: Create S3 ticket first
    ticket = {
        "incident_id": incident_id,
        "status": "OPEN",
        "severity": severity,
        "service": service,
        "error_message": error_message,
        "runbook_matched": runbook_matched,
        "recommended_runbooks": recommended_runbooks,
        "recommendations": recommendations,
        "created_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "occurrences": 1,
        "history": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "created",
                "comment": "Incident created"
            }
        ],
        "resolution": None,
        "resolved_at": None,
        "resolved_by": None
    }
    
    s3_key = f"{config.S3_INCIDENTS_PREFIX}{incident_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(ticket, indent=2),
            ContentType='application/json'
        )
        print(f"[S3] Created ticket: {s3_key}")
    except ClientError as e:
        print(f"[S3] Error creating ticket: {e}")
        raise
    
    # Step 2: Store in Pinecone with S3 key reference
    embedding = model.encode(error_message).tolist()
    
    metadata = {
        "type": "incident",
        "incident_id": incident_id,
        "text": error_message,  # Full error message for search
        "service": service,
        "severity": severity,
        "status": "OPEN",
        "s3_key": s3_key,  # Link to S3 ticket
        "created_at": datetime.utcnow().isoformat()
    }
    
    pinecone_index.upsert(vectors=[{
        "id": incident_id,
        "values": embedding,
        "metadata": metadata
    }])
    
    print(f"[Pinecone] Stored incident: {incident_id}")
    
    return {
        "incident_id": incident_id,
        "s3_key": s3_key
    }


def load_ticket(incident_id: str) -> Optional[dict]:
    """
    Load ticket from S3.
    
    Args:
        incident_id: Incident ID
        
    Returns:
        Ticket dict or None if not found
    """
    ensure_s3_bucket()  # Ensure bucket exists
    
    s3_key = f"{config.S3_INCIDENTS_PREFIX}{incident_id}.json"
    
    try:
        response = s3_client.get_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key
        )
        
        ticket = json.loads(response['Body'].read().decode('utf-8'))
        return ticket
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            return None
        else:
            print(f"[S3] Error loading ticket: {e}")
            return None


def update_ticket(incident_id: str, updates: dict) -> bool:
    """
    Update ticket in S3.
    
    Args:
        incident_id: Incident ID
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False if not found
    """
    ticket = load_ticket(incident_id)
    
    if ticket is None:
        return False
    
    # Merge updates
    ticket.update(updates)
    
    # Save back
    s3_key = f"{config.S3_INCIDENTS_PREFIX}{incident_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(ticket, indent=2),
            ContentType='application/json'
        )
        return True
    except ClientError as e:
        print(f"[S3] Error updating ticket: {e}")
        return False


def add_ticket_comment(incident_id: str, event: str, comment: Optional[str] = None, s3_key: Optional[str] = None) -> bool:
    """
    Add comment/event to ticket history.
    Can accept either incident_id or s3_key.
    
    Args:
        incident_id: Incident ID (optional if s3_key provided)
        event: Event type (recurred, resolved, etc.)
        comment: Optional comment
        s3_key: S3 key (optional, will be constructed from incident_id if not provided)
        
    Returns:
        True if successful
    """
    if s3_key is None:
        s3_key = f"{config.S3_INCIDENTS_PREFIX}{incident_id}.json"
    
    ticket = load_ticket_by_key(s3_key)
    
    if ticket is None:
        return False
    
    # Add history entry
    history_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event
    }
    
    if comment:
        history_entry["comment"] = comment
    
    if "history" not in ticket:
        ticket["history"] = []
    
    ticket["history"].append(history_entry)
    
    # Update last_seen
    ticket["last_seen"] = datetime.utcnow().isoformat()
    
    # If recurred, increment occurrences
    if event == "recurred":
        ticket["occurrences"] = ticket.get("occurrences", 1) + 1
    
    # Save back
    try:
        s3_client.put_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(ticket, indent=2),
            ContentType='application/json'
        )
        print(f"[S3] Added comment to ticket: {s3_key}")
        return True
    except ClientError as e:
        print(f"[S3] Error updating ticket: {e}")
        return False


def load_ticket_by_key(s3_key: str) -> Optional[dict]:
    """
    Load ticket from S3 using S3 key directly.
    
    Args:
        s3_key: S3 key (e.g., "incidents/inc_abc123.json")
        
    Returns:
        Ticket dict or None if not found
    """
    ensure_s3_bucket()  # Ensure bucket exists
    
    try:
        response = s3_client.get_object(
            Bucket=config.S3_BUCKET,
            Key=s3_key
        )
        
        ticket = json.loads(response['Body'].read().decode('utf-8'))
        return ticket
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            return None
        else:
            print(f"[S3] Error loading ticket: {e}")
            return None


def list_tickets(status: Optional[str] = None) -> List[dict]:
    """
    List all tickets from S3, optionally filtered by status.
    
    Args:
        status: Filter by status (OPEN, RESOLVED) or None for all
        
    Returns:
        List of ticket dictionaries
    """
    ensure_s3_bucket()
    
    tickets = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=config.S3_BUCKET,
            Prefix=config.S3_INCIDENTS_PREFIX
        )
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                s3_key = obj['Key']
                
                if not s3_key.endswith('.json'):
                    continue
                
                response = s3_client.get_object(
                    Bucket=config.S3_BUCKET,
                    Key=s3_key
                )
                
                ticket = json.loads(response['Body'].read().decode('utf-8'))
                
                # Filter by status if provided
                if status is None or ticket.get('status') == status:
                    tickets.append(ticket)
        
        # Sort by created_at descending
        tickets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return tickets
        
    except ClientError as e:
        print(f"[S3] Error listing tickets: {e}")
        return []


def resolve_ticket(incident_id: str, resolution: str, resolved_by: str = "system") -> bool:
    """
    Mark ticket as resolved.
    
    Args:
        incident_id: Incident ID
        resolution: Resolution description
        resolved_by: Who resolved it
        
    Returns:
        True if successful
    """
    ticket = load_ticket(incident_id)
    
    if ticket is None:
        return False
    
    # Update ticket
    ticket["status"] = "RESOLVED"
    ticket["resolution"] = resolution
    ticket["resolved_at"] = datetime.utcnow().isoformat()
    ticket["resolved_by"] = resolved_by
    
    # Add history entry
    if "history" not in ticket:
        ticket["history"] = []
    
    ticket["history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "event": "resolved",
        "comment": f"Resolved by {resolved_by}: {resolution}"
    })
    
    # Save back
    return update_ticket(incident_id, ticket)






def store_incident_in_pinecone(incident_id: str, error_message: str, service: str = "unknown") -> str:
    """
    DEPRECATED: Use create_incident() instead.
    This function is kept for backward compatibility but should not be used.
    """
    raise NotImplementedError("Use create_incident() instead - it creates S3 ticket first, then Pinecone entry")


def load_incident(incident_id: str) -> Optional[dict]:
    """
    Load incident ticket from S3.
    This is an alias for load_ticket() for backward compatibility.
    
    Args:
        incident_id: Incident ID
        
    Returns:
        Ticket dict or None if not found
    """
    return load_ticket(incident_id)
