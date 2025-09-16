# LightRAG with Scope Support

This enhanced version of LightRAG includes a comprehensive **Scope Resource Name (SRN)** system for hierarchical data organization.

## 🎯 Scope System Overview

The scope system enables data organization beyond simple workspace isolation:

```
Format: 1.<workspace>.<subject_type>.<subject_id>[.proj_<project>][.thr_<thread>][.top_<topic>]
Example: 1.abc123...def.user.alice.proj_research.thr_main.top_models
```

### Hierarchy Levels:
- **Workspace**: 32-character hex identifier
- **Subject Type**: `user`, `agent`, or `system`
- **Subject ID**: Unique identifier within subject type
- **Project**: Optional project context (e.g., `research`, `development`)
- **Thread**: Optional thread context (e.g., `main`, `chat`, `workflow`)
- **Topic**: Optional topic context (e.g., `models`, `data`, `analysis`)

## 🚀 API Endpoints

### Scope Management
- `POST /scopes/validate` - Validate SRN format
- `POST /scopes/parse` - Parse SRN into components
- `POST /scopes/list` - List available scopes

### Scope-Aware Queries
- `POST /query/scope_aware` - Perform queries within scope context
- `POST /insert/scope_aware` - Insert data with scope context

### Migration Tools
- `POST /scopes/migrations/validate` - Validate migration plan
- `POST /scopes/migrations/migrate` - Migrate workspace to scope
- `GET /scopes/migrations/{id}` - Check migration status

## 🔧 Usage Examples

### Python API
```python
from lightrag import ScopeAwareLightRAG

# Create scope-aware instance
rag = ScopeAwareLightRAG(working_dir="./data")

# Set scope context
rag.set_scope("1.abc123...def.user.alice.proj_research")

# Query within scope
result = rag.query("What are the latest findings?")
```

### REST API
```bash
# Validate SRN
curl -X POST http://localhost:9621/scopes/validate \
  -H "Content-Type: application/json" \
  -d '{"srn": "1.abc123...def.user.alice.proj_research"}'

# Scope-aware query
curl -X POST http://localhost:9621/query/scope_aware \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest findings?",
    "scope": "1.abc123...def.user.alice.proj_research"
  }'
```

## 🌐 WebUI Features

The WebUI includes scope-aware features (requires building from source):

### Available Features:
1. **Scope Selector Component** - Real-time SRN validation
2. **Scope Management Page** - Browse, create, and validate scopes
3. **Migration Tools Interface** - Workspace-to-scope migration
4. **Scope-Aware Queries** - Query interface with scope filtering
5. **Graph Visualization** - Filter knowledge graphs by scope

### To Build WebUI with Scope Features:
```bash
cd lightrag_webui
npm install --legacy-peer-deps
npm run build-no-bun
```

This builds the enhanced WebUI to `lightrag/api/webui/` with all scope features.

## 🐳 Deployment

### Docker (Scope-Enabled)
```bash
# Using docker-compose with full stack
docker-compose -f docker-compose.scope.yml up -d

# Or simple container
docker build -f Dockerfile -t lightrag-scope .
docker run -p 9621:9621 lightrag-scope
```

### DigitalOcean App Platform
- Repository: Your GitHub repo
- Build Command: `pip install -e .`
- Run Command: `python -m lightrag.api.lightrag_server --host 0.0.0.0 --port 9621`
- Port: 9621

## 🔄 Migration from Workspace

To migrate existing workspace data to scope-based organization:

```python
from lightrag.scope.migration import ScopeMigrationTool

migration_tool = ScopeMigrationTool("./data")

# Validate migration
plan = await migration_tool.validate_migration(
    workspace="old_workspace_id",
    target_scope="1.abc123...def.user.migrated.proj_main"
)

# Execute migration
result = await migration_tool.start_migration(
    workspace="old_workspace_id",
    target_scope="1.abc123...def.user.migrated.proj_main"
)
```

## 🏗️ Architecture

### Backend Components:
- **SRN Parser/Validator** - Parse and validate scope strings
- **Scope Context** - Hierarchical scope resolution
- **Scope-Aware Storage** - JSON, PostgreSQL, NetworkX with scope support
- **Migration Tools** - Workspace-to-scope conversion
- **FastAPI Integration** - Complete REST API

### Storage Implementations:
- `ScopeAwareJsonKVStorage` - File-based storage with scope directories
- `ScopeAwarePGKVStorage` - PostgreSQL with scope-partitioned tables
- `ScopeAwareNetworkXStorage` - Graph storage with scope metadata

## 📊 Benefits

1. **Hierarchical Organization** - Multi-level data partitioning
2. **User Isolation** - Perfect for multi-tenant environments
3. **Project Management** - Organize by projects and workflows
4. **Backward Compatibility** - Existing workspace data still works
5. **Enterprise Ready** - Scalable architecture for large deployments

## 🔗 Version

Current version: **1.4.9** with full scope support

For more details, see the comprehensive implementation in `/lightrag/scope/` and `/lightrag_webui/src/`.