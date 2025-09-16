# Task01: Technical Specifications for SRN Implementation

## SRN Format Specification

### Grammar Definition (EBNF)

```ebnf
SRN = version "." workspace "." subject_type "." subject_id [project_segment] [thread_segment] [topic_segment]

version = "1"
workspace = hex_uuid_32
subject_type = "user" | "agent" | "workspace" | "contact" | "project" | "system"
subject_id = identifier
project_segment = ".proj_" identifier
thread_segment = ".thr_" identifier  
topic_segment = ".top_" identifier

hex_uuid_32 = 32 * hex_digit
hex_digit = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "a" | "b" | "c" | "d" | "e" | "f"
identifier = 1*63 ( alphanum | "_" | "-" )
alphanum = "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j" | "k" | "l" | "m" | "n" | "o" | "p" | "q" | "r" | "s" | "t" | "u" | "v" | "w" | "x" | "y" | "z" | "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
```

### Validation Rules

1. **Version**: Must be "1" (reserved for future versions)
2. **Workspace**: Must be exactly 32 lowercase hexadecimal characters
3. **Subject Type**: Must be one of the predefined types
4. **Identifiers**: 1-63 characters, alphanumeric plus underscore and hyphen
5. **Case Sensitivity**: All components are case-insensitive, normalized to lowercase
6. **Unicode**: All text normalized to NFC form

### Examples with Validation

```python
# Valid SRNs
"1.abc12345abcd12345abc1234567890ab.user.johndoe"
"1.def67890cdef67890cdef67890cdef67.agent.chatbot_v2"
"1.123456789012345678901234567890ab.user.alice.proj_research"
"1.fedcba0987654321fedcba0987654321.user.bob.proj_dev.thr_sprint1"
"1.abcdef1234567890abcdef1234567890.user.carol.proj_ai.thr_discussion.top_nlp"

# Invalid SRNs
"2.abc123.user.john"                    # Invalid version
"1.xyz.user.john"                       # Invalid workspace (too short)
"1.abc12345abcd12345abc1234567890ab.customer.john"  # Invalid subject type
"1.abc12345abcd12345abc1234567890ab.user."          # Empty subject_id
"1.abc12345abcd12345abc1234567890ab.user.john@doe"  # Invalid character in identifier
```

## API Specification

### Request/Response Models

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum

class SubjectType(str, Enum):
    USER = "user"
    AGENT = "agent"
    WORKSPACE = "workspace"
    CONTACT = "contact"
    PROJECT = "project"
    SYSTEM = "system"

class SRNComponents(BaseModel):
    version: str = Field("1", description="SRN version")
    workspace: str = Field(..., description="32-character hex workspace UUID")
    subject_type: SubjectType = Field(..., description="Type of subject")
    subject_id: str = Field(..., description="Subject identifier")
    project: Optional[str] = Field(None, description="Project identifier")
    thread: Optional[str] = Field(None, description="Thread identifier")
    topic: Optional[str] = Field(None, description="Topic identifier")
    
    @validator('workspace')
    def validate_workspace(cls, v):
        if not re.match(r'^[a-f0-9]{32}$', v):
            raise ValueError('Workspace must be 32 lowercase hex characters')
        return v
    
    @validator('subject_id', 'project', 'thread', 'topic')
    def validate_identifier(cls, v):
        if v is not None and not re.match(r'^[a-z0-9_-]{1,63}$', v):
            raise ValueError('Identifier must be 1-63 alphanumeric characters, underscore, or hyphen')
        return v

class ScopeQueryRequest(BaseModel):
    query: str = Field(..., description="Query text")
    scope: Optional[str] = Field(None, description="SRN scope string")
    mode: str = Field("hybrid", description="Query mode")
    top_k: int = Field(60, description="Number of results to return")
    response_type: str = Field("Multiple Paragraphs", description="Response format")
    
class ScopeQueryResponse(BaseModel):
    response: str = Field(..., description="Generated response")
    scope_context: Dict[str, Any] = Field(..., description="Scope information used")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")
    
class ScopeDocumentRequest(BaseModel):
    content: str = Field(..., description="Document content")
    scope: Optional[str] = Field(None, description="SRN scope string")
    file_path: Optional[str] = Field(None, description="Original file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
```

### API Endpoints

#### Query Endpoints

```python
@router.post("/query/scoped", response_model=ScopeQueryResponse)
async def scoped_query(request: ScopeQueryRequest):
    """Execute a query within a specific scope context"""
    pass

@router.get("/query/scopes")
async def list_available_scopes(
    workspace: Optional[str] = None,
    subject_type: Optional[str] = None,
    limit: int = 100
):
    """List available scopes matching criteria"""
    pass

@router.post("/query/scope-hierarchy")
async def query_scope_hierarchy(
    base_scope: str,
    depth: int = 3,
    include_data: bool = False
):
    """Query data across a scope hierarchy"""
    pass
```

#### Document Endpoints

```python
@router.post("/documents/scoped")
async def insert_scoped_document(request: ScopeDocumentRequest):
    """Insert a document with scope context"""
    pass

@router.get("/documents/scoped")
async def list_scoped_documents(
    scope: str,
    include_children: bool = False,
    limit: int = 100
):
    """List documents within a scope"""
    pass

@router.delete("/documents/scoped/{document_id}")
async def delete_scoped_document(
    document_id: str,
    scope: str
):
    """Delete a document from a specific scope"""
    pass
```

#### Scope Management Endpoints

```python
@router.post("/scopes/validate")
async def validate_scope(scope: str):
    """Validate an SRN string"""
    pass

@router.post("/scopes/migrate")
async def migrate_workspace_to_scope(
    workspace: str,
    target_scope: str,
    dry_run: bool = True
):
    """Migrate workspace data to scope format"""
    pass

@router.get("/scopes/stats")
async def get_scope_statistics(scope: str):
    """Get statistics for a scope"""
    pass
```

## Storage Backend Specifications

### File-based Storage Implementation

```python
class ScopeAwareFileStorage:
    def __init__(self, working_dir: str, scope_context: Optional[ScopeContext] = None):
        self.working_dir = working_dir
        self.scope_context = scope_context
    
    def get_scope_path(self, scope: ScopeContext) -> str:
        """Generate file path based on scope"""
        path_parts = [
            self.working_dir,
            scope.workspace,
            scope.subject_type,
            scope.subject_id
        ]
        
        if scope.project:
            path_parts.append(f"proj_{scope.project}")
        if scope.thread:
            path_parts.append(f"thr_{scope.thread}")
        if scope.topic:
            path_parts.append(f"top_{scope.topic}")
            
        return os.path.join(*path_parts)
    
    def scope_aware_list(self, scope_pattern: str) -> List[str]:
        """List files matching scope pattern"""
        pass
    
    def migrate_workspace_directory(self, workspace: str, target_scope: ScopeContext) -> bool:
        """Migrate workspace directory to scope structure"""
        pass
```

### Database Storage Implementation

```python
class ScopeAwareDBStorage:
    SCOPE_COLUMNS = [
        'workspace',
        'subject_type', 
        'subject_id',
        'project',
        'thread',
        'topic'
    ]
    
    def add_scope_columns(self, table_name: str):
        """Add scope columns to existing table"""
        pass
    
    def create_scope_indexes(self, table_name: str):
        """Create indexes for efficient scope queries"""
        pass
    
    def build_scope_filter(self, scope: ScopeContext) -> Dict[str, Any]:
        """Build database filter from scope context"""
        filter_dict = {
            'workspace': scope.workspace,
            'subject_type': scope.subject_type,
            'subject_id': scope.subject_id
        }
        
        if scope.project:
            filter_dict['project'] = scope.project
        if scope.thread:
            filter_dict['thread'] = scope.thread
        if scope.topic:
            filter_dict['topic'] = scope.topic
            
        return filter_dict
    
    def scope_aware_query(self, base_query: str, scope: ScopeContext) -> str:
        """Add scope filtering to SQL query"""
        pass
```

### Graph Storage Implementation

```python
class ScopeAwareGraphStorage:
    def add_scope_labels(self, node_id: str, scope: ScopeContext):
        """Add scope-based labels to graph nodes"""
        labels = [
            f"Workspace_{scope.workspace}",
            f"Subject_{scope.subject_type}_{scope.subject_id}"
        ]
        
        if scope.project:
            labels.append(f"Project_{scope.project}")
        if scope.thread:
            labels.append(f"Thread_{scope.thread}")
        if scope.topic:
            labels.append(f"Topic_{scope.topic}")
            
        return labels
    
    def build_scope_cypher_filter(self, scope: ScopeContext) -> str:
        """Build Cypher WHERE clause for scope filtering"""
        conditions = [
            f"n:Workspace_{scope.workspace}",
            f"n:Subject_{scope.subject_type}_{scope.subject_id}"
        ]
        
        if scope.project:
            conditions.append(f"n:Project_{scope.project}")
        if scope.thread:
            conditions.append(f"n:Thread_{scope.thread}")
        if scope.topic:
            conditions.append(f"n:Topic_{scope.topic}")
            
        return " AND ".join(conditions)
```

## Performance Specifications

### Query Performance Targets

- **Scope Parsing**: < 1ms per SRN string
- **Scope Validation**: < 5ms per SRN string
- **Scope-filtered Queries**: < 10% overhead vs. non-scoped queries
- **Scope Migration**: < 1 hour per 1GB of data

### Storage Overhead Targets

- **Metadata Overhead**: < 5% of total storage
- **Index Overhead**: < 10% of data size
- **Memory Overhead**: < 50MB per active scope context

### Scalability Targets

- **Concurrent Scopes**: Support 10,000+ active scopes
- **Scope Depth**: Support 6+ levels of hierarchy
- **Query Throughput**: Maintain 95% of baseline query performance

## Security Specifications

### Input Validation

- All SRN components must pass strict validation
- Prevent path traversal attacks in file-based storage
- Sanitize all identifiers to prevent injection attacks

### Access Control

- Implement scope-based access control
- Validate user permissions for scope access
- Audit all scope-based operations

### Data Isolation

- Ensure complete data isolation between scopes
- Prevent cross-scope data leakage
- Validate scope boundaries in all operations

## Testing Specifications

### Unit Test Coverage

- SRN parsing and validation: 100%
- Scope context management: 95%
- Storage backend integration: 90%
- API endpoint functionality: 95%

### Integration Test Scenarios

- Cross-storage backend compatibility
- Migration from workspace to scope
- Performance under load
- Concurrent scope operations

### Performance Test Criteria

- Baseline performance measurement
- Scope overhead quantification
- Scalability limit identification
- Memory usage profiling
