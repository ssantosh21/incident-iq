"""
Ingestion system for logs and runbooks into Pinecone
"""
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from datetime import datetime
import os
import uuid

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "incident-responder"


def setup_index():
    """Create Pinecone index if it doesn't exist"""
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
        print(f"Created index: {INDEX_NAME}")
    else:
        print(f"Index {INDEX_NAME} already exists")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
    """Simple chunking - split by size with overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if chunk.strip():
            chunks.append(chunk)
        
        start = end - chunk_overlap
    
    return chunks


def ingest_resolved_incident(incident_text: str, resolution: str, runbooks_used: list = None) -> dict:
    """
    Ingest a resolved incident into Pinecone.
    Only resolved incidents are stored to control costs.
    
    Args:
        incident_text: The incident/error message
        resolution: How it was resolved
        runbooks_used: List of runbook titles that helped
    """
    index = pc.Index(INDEX_NAME)
    
    # Generate embedding
    embedding = model.encode(incident_text).tolist()
    
    # Create unique ID
    incident_id = f"incident_{uuid.uuid4().hex[:8]}"
    
    # Store in Pinecone
    index.upsert(vectors=[{
        "id": incident_id,
        "values": embedding,
        "metadata": {
            "type": "incident",
            "text": incident_text,
            "status": "resolved",
            "resolution": resolution,
            "runbooks_used": runbooks_used or [],
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": datetime.utcnow().isoformat()
        }
    }])
    
    print(f"Ingested resolved incident: {incident_id}")
    
    return {
        "status": "success",
        "incident_id": incident_id
    }


def ingest_runbook(title: str, content: str, tags: list = None) -> dict:
    """
    Ingest a runbook into Pinecone.
    Chunks the runbook and stores each chunk separately.
    
    Args:
        title: Runbook title
        content: Runbook content (markdown)
        tags: Optional tags (e.g., ["lambda", "timeout"])
    """
    index = pc.Index(INDEX_NAME)
    
    # Chunk the runbook
    chunks = chunk_text(content)
    
    vectors_to_upsert = []
    
    for i, chunk in enumerate(chunks):
        # Generate embedding
        embedding = model.encode(chunk).tolist()
        
        # Create unique ID
        chunk_id = f"runbook_{uuid.uuid4().hex[:8]}_{i}"
        
        vectors_to_upsert.append({
            "id": chunk_id,
            "values": embedding,
            "metadata": {
                "type": "runbook",
                "title": title,
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "tags": tags or [],
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    # Batch upsert
    index.upsert(vectors=vectors_to_upsert)
    
    print(f"Ingested runbook: {title} ({len(chunks)} chunks)")
    
    return {
        "status": "success",
        "title": title,
        "chunks_stored": len(chunks)
    }


if __name__ == "__main__":
    from sample_runbooks import RUNBOOKS
    
    # Setup index
    setup_index()
    
    # Example: Ingest sample resolved incidents (for demo purposes)
    # In production, these would be created via the /resolve endpoint
    sample_resolved_incidents = [
        {
            "text": "Lambda function timeout after 30 seconds. Function: process-orders. Error: Task timed out after 30.00 seconds",
            "resolution": "Increased Lambda timeout from 30s to 60s and optimized database query. Issue resolved.",
            "runbooks_used": ["Lambda Timeout"]
        },
        {
            "text": "DynamoDB throttling exception. Table: orders. ProvisionedThroughputExceededException",
            "resolution": "Enabled auto-scaling on orders table. Set min RCU=5, max RCU=100. Throttling stopped.",
            "runbooks_used": ["DynamoDB Throttling"]
        }
    ]
    
    print("Ingesting sample resolved incidents...")
    for incident in sample_resolved_incidents:
        ingest_resolved_incident(
            incident["text"],
            incident["resolution"],
            incident["runbooks_used"]
        )
    
    print("\nIngesting runbooks...")
    for runbook in RUNBOOKS:
        ingest_runbook(
            title=runbook["title"],
            content=runbook["content"],
            tags=runbook["tags"]
        )
    
    print("\nIngestion complete!")
    print("\nNote: Only resolved incidents are stored to control costs.")
    print("New incidents are stored as 'pending' via the /incident endpoint.")
