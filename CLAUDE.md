# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LightRAG is a Simple and Fast Retrieval-Augmented Generation system that implements a graph-based RAG approach. It's a Python library with optional API server capabilities for document indexing, knowledge graph exploration, and query interfaces.

## Development Commands

### Installation and Setup
```bash
# Install from source (recommended for development)
pip install -e .

# Install with API support
pip install -e ".[api]"

# Set up environment
cp env.example .env
```

### Code Quality and Testing
```bash
# Run pre-commit hooks (linting and formatting)
pre-commit run --all-files

# Run Ruff formatter
ruff format

# Run Ruff linter with fixes
ruff check --fix

# Run tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_lightrag_ollama_chat.py
python -m pytest tests/test_aquery_data_endpoint.py
```

### Running the Application
```bash
# Start LightRAG server
lightrag-server

# Start with Gunicorn (production)
lightrag-gunicorn

# Run demo examples
python examples/lightrag_openai_demo.py
python examples/lightrag_ollama_demo.py
```

### Docker Operations
```bash
# Start with Docker Compose
docker compose up

# Build Docker image
docker build -t lightrag .
```

## Core Architecture

### Main Components

1. **LightRAG Core** (`lightrag/lightrag.py`)
   - Main RAG engine implementing graph-based retrieval
   - Handles document indexing, entity/relation extraction, and querying
   - Supports multiple query modes: local, global, hybrid, naive, mix

2. **Storage Backends** (`lightrag/kg/`)
   - **KV Storage**: Document chunks, LLM cache (JSON, PostgreSQL, Redis, MongoDB)
   - **Vector Storage**: Embeddings (NanoVectorDB, PostgreSQL, Milvus, Faiss, Qdrant, MongoDB)
   - **Graph Storage**: Entities and relations (NetworkX, Neo4J, PostgreSQL AGE, Memgraph)
   - **Doc Status Storage**: Processing status (JSON, PostgreSQL, MongoDB)

3. **LLM Integration** (`lightrag/llm/`)
   - Support for OpenAI, Ollama, Hugging Face, Azure OpenAI, Gemini
   - LlamaIndex integration for broader model compatibility
   - Configurable embedding and completion functions

4. **API Server** (`lightrag/api/`)
   - FastAPI-based REST API and Web UI
   - Ollama-compatible chat interface
   - Authentication and configuration management
   - Routes for documents, queries, and graph operations

### Key Data Flow

1. **Document Indexing**: Text → Chunks → Entity/Relation Extraction → Knowledge Graph + Vector Embeddings
2. **Query Processing**: Query → Multi-mode Retrieval (graph + vector) → Context Assembly → LLM Generation
3. **Storage**: Synchronized updates across KV, Vector, Graph, and Doc Status stores

## Configuration

### Environment Variables
- Model configuration via `.env` file (API keys, base URLs)
- Storage connection strings (database URLs, credentials)
- Performance tuning (batch sizes, token limits, concurrency)

### Storage Configuration
- Workspace isolation for multi-tenant deployments
- Configurable storage backends per component type
- Connection pooling and retry mechanisms

## Development Guidelines

### Initialization Pattern
Always follow this pattern when using LightRAG programmatically:
```python
rag = LightRAG(...)
await rag.initialize_storages()  # Required for async storage backends
await initialize_pipeline_status()  # Required for processing pipeline
```

### Testing Strategy
- Integration tests in `tests/` directory
- Example scripts in `examples/` serve as functional tests
- Use pytest for test execution

### Code Quality
- Ruff for linting and formatting (configured in pyproject.toml)
- Pre-commit hooks enforce code standards
- Type hints where applicable

### Module Structure
- Core logic in `lightrag/` package
- Storage abstractions in `lightrag/kg/`
- LLM integrations in `lightrag/llm/`
- API components in `lightrag/api/`
- Utilities in `lightrag/utils.py` and `lightrag/operate.py`

## Common Development Patterns

### Adding New Storage Backends
1. Implement storage interface in appropriate `lightrag/kg/` module
2. Add connection configuration to environment handling
3. Update storage factory methods
4. Add example usage and tests

### Adding New LLM Providers
1. Create provider module in `lightrag/llm/`
2. Implement completion and embedding functions
3. Add configuration examples
4. Document API key requirements

### Extending Query Modes
1. Modify query processing in core LightRAG class
2. Update prompt templates if needed
3. Add corresponding API endpoints
4. Document usage patterns