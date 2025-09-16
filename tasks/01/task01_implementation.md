# Task01: Scope Resource Name (SRN) System Implementation

## Task Overview

Implement a comprehensive Scope Resource Name (SRN) system for LightRAG to enable sophisticated data partitioning beyond the current workspace-based approach. The SRN system will provide hierarchical organization of data by workspace, user, project, thread, and topic.

## Objectives

1. **Design and implement SRN format**: Create a versioned, hierarchical naming system
2. **Extend storage backends**: Adapt all storage implementations to support scope-based partitioning
3. **Update API endpoints**: Modify existing APIs to accept and process scope parameters
4. **Maintain backward compatibility**: Ensure existing workspace-based functionality continues to work
5. **Provide migration tools**: Enable smooth transition from workspace to SRN system

## SRN Format

```
1.<ws32>.<subject_type>.<subject_id>[.proj_<project>][.thr_<thread>][.top_<topic>]
```

**Example**: `1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_research.thr_discussion1.top_ai_models`

## Implementation Tasks

### Phase 1: Core Infrastructure

#### Task 1.1: SRN Parser and Validator
- **File**: `lightrag/scope/srn.py`
- **Components**:
  - `SRNComponents` dataclass
  - `SRNParser` class with parsing, validation, canonicalization
  - `SRNValidator` class with comprehensive validation rules
  - Unicode NFC normalization
  - Detailed error messages

#### Task 1.2: Scope Context Manager
- **File**: `lightrag/scope/context.py`
- **Components**:
  - `ScopeContext` class for scope representation
  - `ScopeResolver` class for inheritance and matching
  - Scope hierarchy navigation
  - Filter dictionary generation

#### Task 1.3: Exception Handling
- **File**: `lightrag/scope/exceptions.py`
- **Components**:
  - Custom exception hierarchy
  - Detailed error messages
  - Error code system

### Phase 2: Storage Backend Integration

#### Task 2.1: Base Storage Interface Extensions
- **Files**: All storage implementation files
- **Components**:
  - Add scope-aware methods to base classes
  - Implement scope filtering
  - Add migration utilities

#### Task 2.2: File-based Storage Updates
- **Files**: `lightrag/kg/json_impl.py`, `lightrag/kg/nano_vectordb_impl.py`, etc.
- **Components**:
  - Scope-based directory structure
  - Path resolution utilities
  - Migration from workspace directories

#### Task 2.3: Database Storage Updates
- **Files**: `lightrag/kg/pg_impl.py`, `lightrag/kg/redis_impl.py`, etc.
- **Components**:
  - Add scope columns/fields
  - Create scope-based indexes
  - Update query methods

#### Task 2.4: Graph Storage Updates
- **Files**: `lightrag/kg/neo4j_impl.py`, `lightrag/kg/memgraph_impl.py`
- **Components**:
  - Scope-based labels and properties
  - Cypher query modifications
  - Graph traversal updates

### Phase 3: API Integration

#### Task 3.1: Query API Enhancements
- **File**: `lightrag/api/routers/query_routes.py`
- **Components**:
  - Add scope parameter to existing endpoints
  - Create new scoped query endpoints
  - Implement scope-based filtering
  - Update request/response models

#### Task 3.2: Document API Updates
- **File**: `lightrag/api/routers/document_routes.py`
- **Components**:
  - Scope-aware document insertion
  - Scope-based document retrieval
  - Scope filtering for document operations

#### Task 3.3: Graph API Extensions
- **File**: `lightrag/api/routers/graph_routes.py`
- **Components**:
  - Scope-based graph queries
  - Hierarchical graph visualization
  - Scope-aware entity/relationship operations

#### Task 3.4: Scope Management API
- **File**: `lightrag/api/routers/scope_routes.py` (new)
- **Components**:
  - Scope validation endpoints
  - Migration management endpoints
  - Scope statistics and monitoring

### Phase 4: Migration and Compatibility

#### Task 4.1: Migration Tools
- **File**: `lightrag/scope/migration.py`
- **Components**:
  - Workspace to SRN migration utilities
  - Data validation tools
  - Rollback mechanisms
  - Progress tracking

#### Task 4.2: Backward Compatibility Layer
- **File**: `lightrag/scope/compatibility.py`
- **Components**:
  - Workspace to SRN conversion
  - Legacy API support
  - Automatic scope detection

### Phase 5: Advanced Features

#### Task 5.1: Scope Inheritance
- **Components**:
  - Hierarchical scope resolution
  - Partial scope matching
  - Scope aggregation queries

#### Task 5.2: Performance Optimization
- **Components**:
  - Scope-based caching
  - Query optimization
  - Index strategy refinement

## Implementation Details

### Core SRN Parser Implementation

```python
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class SubjectType(str, Enum):
    USER = "user"
    AGENT = "agent"
    WORKSPACE = "workspace"
    CONTACT = "contact"
    PROJECT = "project"
    SYSTEM = "system"

@dataclass
class SRNComponents:
    version: str
    workspace: str
    subject_type: SubjectType
    subject_id: str
    project: Optional[str] = None
    thread: Optional[str] = None
    topic: Optional[str] = None

class SRNParser:
    SRN_PATTERN = re.compile(
        r'^(?P<version>\d+)\.'
        r'(?P<workspace>[a-f0-9]{32})\.'
        r'(?P<subject_type>user|agent|workspace|contact|project|system)\.'
        r'(?P<subject_id>[a-z0-9_-]{1,63})'
        r'(?:\.proj_(?P<project>[a-z0-9_-]{1,63}))?'
        r'(?:\.thr_(?P<thread>[a-z0-9_-]{1,63}))?'
        r'(?:\.top_(?P<topic>[a-z0-9_-]{1,63}))?$'
    )
    
    def parse(self, srn_string: str) -> SRNComponents:
        """Parse SRN string into components"""
        normalized = self.canonicalize(srn_string)
        match = self.SRN_PATTERN.match(normalized)
        
        if not match:
            raise InvalidSRNFormatError(f"Invalid SRN format: {srn_string}")
        
        groups = match.groupdict()
        return SRNComponents(
            version=groups['version'],
            workspace=groups['workspace'],
            subject_type=SubjectType(groups['subject_type']),
            subject_id=groups['subject_id'],
            project=groups.get('project'),
            thread=groups.get('thread'),
            topic=groups.get('topic')
        )
    
    def canonicalize(self, srn_string: str) -> str:
        """Canonicalize SRN string"""
        # Normalize Unicode to NFC
        normalized = unicodedata.normalize('NFC', srn_string)
        # Convert to lowercase
        return normalized.lower().strip()
    
    def to_string(self, components: SRNComponents) -> str:
        """Convert components back to SRN string"""
        srn = f"{components.version}.{components.workspace}.{components.subject_type}.{components.subject_id}"
        
        if components.project:
            srn += f".proj_{components.project}"
        if components.thread:
            srn += f".thr_{components.thread}"
        if components.topic:
            srn += f".top_{components.topic}"
            
        return srn
```

### Storage Backend Integration Example

```python
class ScopeAwareKVStorage:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_context: Optional[ScopeContext] = None
    
    def set_scope_context(self, scope: ScopeContext):
        """Set the current scope context"""
        self.scope_context = scope
    
    def get_scoped_key(self, key: str) -> str:
        """Generate scope-aware key"""
        if not self.scope_context:
            return key
        
        scope_prefix = f"{self.scope_context.workspace}:{self.scope_context.subject_type}:{self.scope_context.subject_id}"
        
        if self.scope_context.project:
            scope_prefix += f":proj_{self.scope_context.project}"
        if self.scope_context.thread:
            scope_prefix += f":thr_{self.scope_context.thread}"
        if self.scope_context.topic:
            scope_prefix += f":top_{self.scope_context.topic}"
            
        return f"{scope_prefix}:{key}"
    
    async def scope_aware_get(self, key: str) -> Any:
        """Get value with scope awareness"""
        scoped_key = self.get_scoped_key(key)
        return await self.get(scoped_key)
    
    async def scope_aware_set(self, key: str, value: Any):
        """Set value with scope awareness"""
        scoped_key = self.get_scoped_key(key)
        await self.set(scoped_key, value)
```

### API Integration Example

```python
@router.post("/query/scoped", response_model=ScopeQueryResponse)
async def scoped_query(request: ScopeQueryRequest):
    """Execute a query within a specific scope context"""
    try:
        # Parse and validate scope
        if request.scope:
            parser = SRNParser()
            scope_components = parser.parse(request.scope)
            scope_context = ScopeContext(scope_components)
        else:
            scope_context = None
        
        # Set scope context in RAG instance
        if scope_context:
            await rag.set_scope_context(scope_context)
        
        # Execute query
        result = await rag.aquery(
            request.query,
            param=QueryParam(
                mode=request.mode,
                top_k=request.top_k,
                response_type=request.response_type
            )
        )
        
        return ScopeQueryResponse(
            response=result,
            scope_context=scope_context.to_dict() if scope_context else {},
            metadata={"query_mode": request.mode, "scope_applied": bool(scope_context)}
        )
        
    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
```

## Testing Strategy

### Unit Tests
- SRN parsing and validation
- Scope context management
- Storage backend scope integration
- API endpoint functionality

### Integration Tests
- End-to-end scope-based queries
- Cross-storage backend compatibility
- Migration from workspace to scope
- Performance impact assessment

### Performance Tests
- Query response time with scope filtering
- Storage overhead measurement
- Concurrent scope operation handling
- Memory usage profiling

## Success Criteria

1. **Functional Requirements**:
   - SRN parsing works correctly for all valid formats
   - All storage backends support scope-based operations
   - API endpoints accept and process scope parameters
   - Migration tools successfully convert workspace data
   - Backward compatibility maintained

2. **Performance Requirements**:
   - Query response time increase < 10%
   - Storage overhead increase < 5%
   - System stability under scope-based load

3. **Quality Requirements**:
   - Test coverage > 90%
   - Comprehensive documentation
   - Error handling for all edge cases

## Deliverables

1. **Code Implementation**:
   - Core SRN infrastructure modules
   - Updated storage backend implementations
   - Enhanced API endpoints
   - Migration and compatibility tools

2. **Documentation**:
   - API documentation updates
   - User guide for SRN usage
   - Migration procedures
   - Performance considerations

3. **Testing**:
   - Comprehensive test suite
   - Performance benchmarks
   - Migration validation tools

4. **Examples**:
   - SRN usage examples
   - Migration scripts
   - Performance optimization guides

## Timeline

- **Week 1-2**: Core SRN infrastructure
- **Week 3-4**: Storage backend integration
- **Week 5-6**: API integration and backward compatibility
- **Week 7-8**: Advanced features and optimization
- **Week 9**: Testing, documentation, and deployment preparation

This implementation will provide LightRAG with a powerful, flexible scope-based partitioning system while maintaining full backward compatibility with the existing workspace approach.
