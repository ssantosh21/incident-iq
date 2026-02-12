"""
Configuration for Incident Responder PoC
"""
import os

# Similarity Thresholds
SIMILARITY_THRESHOLD = 0.7  # For incident deduplication
RUNBOOK_MATCH_THRESHOLD = 0.7  # For runbook matching

# Severity Levels
DEFAULT_SEVERITY = "MEDIUM"
REGRESSION_SEVERITY = "HIGH"

# Pinecone Configuration
INDEX_NAME = "incident-responder"

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_MAX_TOKENS = 500

# Embedding Model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# AWS Configuration
AWS_PROFILE = "santosh"  # AWS profile name from ~/.aws/credentials
S3_BUCKET = "incident-responder-poc"  # Will be created if doesn't exist
S3_INCIDENTS_PREFIX = "incidents/"
S3_RUNBOOKS_PREFIX = "runbooks/"
