# 🔧 API Documentation

## Overview

This document describes the internal API structure of the Customer Support Copilot's AI pipeline components.

## Core Components

### 1. Ticket Classifier

The `TicketClassifier` class handles multi-dimensional classification of support tickets.

#### Class: `TicketClassifier`

```python
from src.classifier import TicketClassifier

classifier = TicketClassifier(api_key="your_google_api_key")
```

#### Methods

##### `classify_ticket(ticket_text: str) -> dict`

Classifies a support ticket across multiple dimensions.

**Parameters:**
- `ticket_text` (str): The raw ticket content to classify

**Returns:**
- `dict`: Classification results with the following structure:
```json
{
    "topic": "Product",
    "sentiment": "Frustrated", 
    "priority": "P1",
    "confidence_scores": {
        "topic": 0.95,
        "sentiment": 0.87,
        "priority": 0.92
    },
    "reasoning": "User is asking about product functionality with frustrated tone..."
}
```

**Example:**
```python
result = classifier.classify_ticket(
    "I can't figure out how to set up lineage tracking in Atlan. The documentation is confusing!"
)
print(result["topic"])      # "Lineage"
print(result["sentiment"])  # "Frustrated"
print(result["priority"])   # "P1"
```

### 2. RAG Pipeline

The `RAGPipeline` class handles knowledge retrieval and response generation.

#### Class: `RAGPipeline`

```python
from src.rag_pipeline import RAGPipeline

rag = RAGPipeline(
    vector_store_path="./data/vector_store",
    api_key="your_google_api_key"
)
```

#### Methods

##### `generate_response(query: str, context: dict = None) -> dict`

Generates a response using retrieval-augmented generation.

**Parameters:**
- `query` (str): The user's question or ticket content
- `context` (dict, optional): Additional context from classification

**Returns:**
- `dict`: Response with sources and metadata:
```json
{
    "answer": "To set up lineage tracking in Atlan...",
    "sources": [
        "https://docs.atlan.com/lineage/setup",
        "https://docs.atlan.com/lineage/best-practices"
    ],
    "confidence": 0.94,
    "retrieved_chunks": 5,
    "response_type": "direct_answer"
}
```

##### `retrieve_documents(query: str, k: int = 10) -> list`

Retrieves relevant documents from the knowledge base.

**Parameters:**
- `query` (str): Search query
- `k` (int): Number of documents to retrieve

**Returns:**
- `list`: List of relevant document chunks with metadata

### 3. Knowledge Base Manager

#### Class: `KnowledgeBaseManager`

Manages the vector store and document retrieval.

```python
from src.knowledge_base import KnowledgeBaseManager

kb = KnowledgeBaseManager(store_path="./data/vector_store")
```

#### Methods

##### `add_documents(documents: list) -> None`

Adds new documents to the knowledge base.

##### `search(query: str, k: int = 10) -> list`

Performs semantic search in the knowledge base.

##### `update_index() -> None`

Updates the vector index with new documents.

## Error Handling

All components implement consistent error handling:

```python
try:
    result = classifier.classify_ticket(ticket_text)
except ClassificationError as e:
    # Handle classification-specific errors
    print(f"Classification failed: {e}")
except APIError as e:
    # Handle API-related errors
    print(f"API error: {e}")
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
VECTOR_STORE_PATH=./data/vector_store
EMBEDDING_MODEL=all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
MAX_CONTEXT_LENGTH=4000
SIMILARITY_THRESHOLD=0.7
```

### Model Configuration

```python
# Classifier configuration
CLASSIFIER_CONFIG = {
    "model": "gemini-1.5-flash",
    "temperature": 0.1,
    "max_output_tokens": 1000
}

# RAG configuration  
RAG_CONFIG = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "retrieval_k": 10,
    "rerank_top_k": 3
}
```

## Rate Limiting

The API implements intelligent rate limiting:

- **Gemini API**: 60 requests/minute (free tier)
- **Batch processing**: Automatic retry with exponential backoff
- **Caching**: Responses cached for 1 hour to reduce API calls

## Performance Metrics

### Latency Targets

| Operation | Target | Typical |
|-----------|---------|---------|
| Classification | <2s | 1.2s |
| RAG Response | <5s | 3.4s |
| Document Retrieval | <1s | 0.6s |

### Accuracy Metrics

| Metric | Target | Current |
|--------|---------|---------|
| Topic Classification | >90% | 95.2% |
| Sentiment Analysis | >85% | 92.1% |
| Answer Relevance | >4.0/5 | 4.2/5 |

## Usage Examples

### Complete Pipeline Example

```python
from src.classifier import TicketClassifier
from src.rag_pipeline import RAGPipeline

# Initialize components
classifier = TicketClassifier(api_key=api_key)
rag = RAGPipeline(vector_store_path="./data/vector_store", api_key=api_key)

# Process a ticket
ticket = "How do I configure SSO with SAML in Atlan?"

# Step 1: Classify
classification = classifier.classify_ticket(ticket)
print(f"Topic: {classification['topic']}")  # "SSO"

# Step 2: Generate response (if appropriate topic)
if classification['topic'] in ['How-to', 'Product', 'API/SDK', 'SSO']:
    response = rag.generate_response(ticket, context=classification)
    print(f"Answer: {response['answer']}")
    print(f"Sources: {response['sources']}")
else:
    print(f"Ticket routed to {classification['topic']} team")
```

### Batch Processing Example

```python
import json
from src.utils import batch_process_tickets

# Load tickets
with open('data/sample_tickets.json', 'r') as f:
    tickets = json.load(f)

# Process in batches
results = batch_process_tickets(
    tickets=tickets,
    batch_size=5,
    classifier=classifier,
    rag=rag
)

# Save results
with open('data/processed_tickets.json', 'w') as f:
    json.dump(results, f, indent=2)
```
