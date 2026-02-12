"""
Incident Response Agents
"""
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv
import os
import config
import storage

load_dotenv()

model = SentenceTransformer(config.EMBEDDING_MODEL)
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INDEX_NAME = config.INDEX_NAME


class IncidentAnalyzerAgent:
    """
    Agent 1: Analyzes the incident and searches for similar past incidents.
    Implements deduplication and regression detection.
    """
    
    def __init__(self):
        self.index = pc.Index(INDEX_NAME)
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
    
    def execute(self, incident_log: str) -> dict:
        """
        Analyze incident and find similar past incidents.
        Detects: new, existing (OPEN), or regression (RESOLVED).
        """
        print(f"[IncidentAnalyzer] Analyzing: {incident_log[:50]}...")
        
        # Convert incident to embedding
        query_embedding = model.encode(incident_log).tolist()
        
        # Search for similar incidents
        results = self.index.query(
            vector=query_embedding,
            top_k=5,
            filter={"type": "incident"},
            include_metadata=True
        )
        
        # Check for duplicate (similarity > threshold)
        duplicate_found = None
        incident_status = "new"
        
        if results['matches'] and results['matches'][0]['score'] > self.similarity_threshold:
            match = results['matches'][0]
            incident_id = match['metadata'].get('incident_id', match['id'])
            s3_key = match['metadata'].get('s3_key')  # Get S3 key from Pinecone
            
            # Load full incident data from S3 ticket
            incident_data = storage.load_ticket(incident_id)
            
            if incident_data:
                status = incident_data.get('status', 'OPEN')
                
                # Determine if existing or regression
                if status == 'OPEN':
                    incident_status = "existing"
                elif status == 'RESOLVED':
                    incident_status = "regression"
                
                duplicate_found = {
                    "id": incident_id,
                    "text": match['metadata']['text'],
                    "similarity": match['score'],
                    "status": status,
                    "s3_key": s3_key,  # Include S3 key
                    "incident_data": incident_data
                }
                
                print(f"[IncidentAnalyzer] {incident_status.upper()} (similarity: {match['score']:.3f}, status: {status})")
        
        # Collect all similar incidents for context
        similar_incidents = []
        for match in results['matches']:
            similar_incidents.append({
                "id": match['metadata'].get('incident_id', match['id']),
                "text": match['metadata']['text'],
                "similarity": match['score']
            })
        
        print(f"[IncidentAnalyzer] Status: {incident_status}")
        
        return {
            "status": incident_status,
            "incident": incident_log,
            "duplicate_found": duplicate_found,
            "similar_incidents": similar_incidents
        }


class RunbookRetrieverAgent:
    """
    Agent 2: Retrieves relevant runbooks for the incident.
    """
    
    def __init__(self):
        self.index = pc.Index(INDEX_NAME)
    
    def execute(self, incident_log: str, top_k: int = 3) -> dict:
        """
        Find relevant runbooks for this incident.
        """
        print(f"[RunbookRetriever] Searching runbooks...")
        
        # Convert incident to embedding
        query_embedding = model.encode(incident_log).tolist()
        
        # Search for relevant runbooks
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter={"type": "runbook"},  # Only search runbooks
            include_metadata=True
        )
        
        runbooks = []
        for match in results['matches']:
            runbooks.append({
                "title": match['metadata']['title'],
                "text": match['metadata']['text'],
                "tags": match['metadata'].get('tags', []),
                "similarity": match['score']
            })
        
        print(f"[RunbookRetriever] Found {len(runbooks)} relevant runbooks")
        
        return {
            "status": "success",
            "runbooks": runbooks
        }


class RecommendationAgent:
    """
    Agent 3: Analyzes incident + runbooks and recommends actions.
    """
    
    def execute(self, incident_log: str, similar_incidents: list, runbooks: list) -> dict:
        """
        Generate recommendations based on incident and runbooks.
        """
        print(f"[RecommendationAgent] Generating recommendations...")
        
        # Build context from runbooks
        runbook_context = "\n\n".join([
            f"Runbook: {rb['title']}\n{rb['text']}" 
            for rb in runbooks
        ])
        
        # Build context from similar incidents
        similar_context = "\n".join([
            f"- {inc['text']} (similarity: {inc['similarity']:.2f})"
            for inc in similar_incidents[:2]
        ])
        
        # Ask LLM for recommendations
        prompt = f"""You are an incident response expert. Analyze this incident and recommend actions.

Current Incident:
{incident_log}

Similar Past Incidents:
{similar_context}

Relevant Runbooks:
{runbook_context}

Provide:
1. Root cause analysis (1-2 sentences)
2. Immediate actions (2-3 bullet points)
3. Long-term prevention (1-2 bullet points)

Be concise and actionable."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        recommendations = response.choices[0].message.content
        
        print(f"[RecommendationAgent] Recommendations generated")
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "runbooks_used": [rb['title'] for rb in runbooks]
        }
