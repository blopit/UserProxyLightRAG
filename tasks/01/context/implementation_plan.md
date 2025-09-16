# Task01: SRN Implementation Plan

## Overview

This document outlines the detailed implementation plan for the Scope Resource Name (SRN) system in LightRAG. The implementation will be done in phases to ensure stability and backward compatibility.

## Phase 1: Core SRN Infrastructure (Week 1-2)

### 1.1 SRN Parser Module (`lightrag/scope/srn.py`)

**Components to implement**:

```python
class SRNComponents:
    version: str
    workspace: str
    subject_type: str
    subject_id: str
    project: Optional[str]
    thread: Optional[str]
    topic: Optional[str]

class SRNParser:
    def parse(self, srn_string: str) -> SRNComponents
    def validate(self, components: SRNComponents) -> bool
    def canonicalize(self, srn_string: str) -> str
    def to_string(self, components: SRNComponents) -> str

class SRNValidator:
    def validate_workspace_uuid(self, workspace: str) -> bool
    def validate_subject_type(self, subject_type: str) -> bool
    def validate_identifier(self, identifier: str) -> bool
    def validate_segment_length(self, segment: str) -> bool
```

**Key Features**:
- Unicode NFC normalization
- Comprehensive validation with detailed error messages
- Support for partial SRN parsing
- Efficient string operations

### 1.2 Scope Context Manager (`lightrag/scope/context.py`)

**Components to implement**:

```python
class ScopeContext:
    def __init__(self, srn: str)
    def get_workspace(self) -> str
    def get_subject_type(self) -> str
    def get_subject_id(self) -> str
    def get_project(self) -> Optional[str]
    def get_thread(self) -> Optional[str]
    def get_topic(self) -> Optional[str]
    def to_filter_dict(self) -> Dict[str, str]
    def matches_scope(self, other_scope: 'ScopeContext') -> bool
    def is_parent_of(self, child_scope: 'ScopeContext') -> bool

class ScopeResolver:
    def resolve_inheritance(self, scope: ScopeContext) -> List[ScopeContext]
    def find_matching_scopes(self, pattern: str) -> List[ScopeContext]
    def merge_scopes(self, scopes: List[ScopeContext]) -> ScopeContext
```

### 1.3 Exception Handling (`lightrag/scope/exceptions.py`)

```python
class SRNError(Exception): pass
class InvalidSRNFormatError(SRNError): pass
class InvalidWorkspaceError(SRNError): pass
class InvalidSubjectTypeError(SRNError): pass
class InvalidIdentifierError(SRNError): pass
class ScopeResolutionError(SRNError): pass
```

## Phase 2: Storage Backend Integration (Week 3-4)

### 2.1 Storage Interface Extensions

**Base Storage Interface Updates**:

```python
# Add to base storage classes
class BaseScopeStorage:
    def set_scope_context(self, scope: ScopeContext) -> None
    def get_scope_filter(self) -> Dict[str, Any]
    def scope_aware_query(self, query: Dict, scope: ScopeContext) -> Any
    def migrate_workspace_to_scope(self, workspace: str, scope: ScopeContext) -> bool
```

### 2.2 Storage Implementation Updates

**File-based Storage** (`JsonKVStorage`, `NetworkXStorage`, etc.):
- Create scope-based directory structure: `{working_dir}/{workspace}/{subject_type}/{subject_id}/...`
- Implement scope-aware file path resolution
- Add migration utilities for existing workspace directories

**Collection-based Storage** (`RedisKVStorage`, `MongoKVStorage`, etc.):
- Extend collection naming: `{workspace}_{subject_type}_{subject_id}_{collection_type}`
- Add scope-based collection filtering
- Implement scope-aware query methods

**Relational Storage** (`PGKVStorage`, `PGVectorStorage`, etc.):
- Add scope columns: `workspace`, `subject_type`, `subject_id`, `project`, `thread`, `topic`
- Create scope-based indexes for performance
- Update all queries to include scope filtering

**Graph Storage** (`Neo4JStorage`, `MemgraphStorage`):
- Add scope labels and properties to nodes
- Implement scope-based graph traversal
- Update Cypher queries for scope filtering

### 2.3 Migration Tools

```python
class ScopeMigrationTool:
    def migrate_workspace_data(self, workspace: str, target_scope: ScopeContext) -> bool
    def validate_migration(self, workspace: str, target_scope: ScopeContext) -> List[str]
    def rollback_migration(self, migration_id: str) -> bool
    def get_migration_status(self, migration_id: str) -> Dict[str, Any]
```

## Phase 3: API Integration (Week 5-6)

### 3.1 Query API Enhancements (`lightrag/api/routers/query_routes.py`)

**New Request Models**:

```python
class ScopeQueryRequest(BaseModel):
    query: str
    scope: Optional[str] = None  # SRN string
    mode: str = "hybrid"
    # ... existing fields

class ScopeQueryResponse(BaseModel):
    response: str
    scope_context: Dict[str, str]
    # ... existing fields
```

**Updated Endpoints**:
- Add scope parameter to existing `/query` endpoint
- Create new `/query/scoped` endpoint for explicit scope queries
- Implement scope-based result filtering

### 3.2 Document API Updates (`lightrag/api/routers/document_routes.py`)

**Enhanced Document Operations**:
- Add scope parameter to document insertion
- Implement scope-aware document retrieval
- Support scope-based document deletion

### 3.3 Graph API Extensions (`lightrag/api/routers/graph_routes.py`)

**Scope-aware Graph Operations**:
- Filter knowledge graph by scope
- Support scope-based entity and relationship queries
- Implement scope hierarchy visualization

### 3.4 Backward Compatibility Layer

```python
class WorkspaceToScopeAdapter:
    def convert_workspace_to_srn(self, workspace: str) -> str
    def extract_workspace_from_srn(self, srn: str) -> str
    def is_legacy_workspace_request(self, request: Dict) -> bool
    def adapt_legacy_request(self, request: Dict) -> Dict
```

## Phase 4: Advanced Features (Week 7-8)

### 4.1 Scope Inheritance and Resolution

**Hierarchical Scope Queries**:
- Support partial scope matching
- Implement scope inheritance rules
- Enable scope-based aggregation

### 4.2 Performance Optimization

**Indexing Strategy**:
- Create composite indexes for scope fields
- Implement scope-based query optimization
- Add caching for frequently accessed scopes

**Query Optimization**:
- Optimize scope filtering algorithms
- Implement scope-based result caching
- Add performance monitoring for scope queries

### 4.3 Advanced Query Features

```python
class AdvancedScopeQuery:
    def query_scope_hierarchy(self, base_scope: str, depth: int) -> List[Dict]
    def aggregate_across_scopes(self, scope_pattern: str, aggregation: str) -> Dict
    def find_related_scopes(self, scope: str, relation_type: str) -> List[str]
```

## Implementation Guidelines

### Code Quality Standards

1. **Type Hints**: All functions must have complete type annotations
2. **Documentation**: Comprehensive docstrings for all public methods
3. **Testing**: Minimum 90% test coverage for all new code
4. **Error Handling**: Graceful error handling with informative messages

### Testing Strategy

1. **Unit Tests**: Test each SRN component in isolation
2. **Integration Tests**: Test storage backend integration
3. **API Tests**: Test all API endpoints with scope parameters
4. **Performance Tests**: Benchmark scope-based queries
5. **Migration Tests**: Test workspace-to-scope migration

### Documentation Requirements

1. **API Documentation**: Update OpenAPI specifications
2. **User Guide**: Create SRN usage examples
3. **Migration Guide**: Document migration procedures
4. **Performance Guide**: Document performance considerations

## Risk Mitigation

### Technical Risks

1. **Performance Degradation**: Implement comprehensive benchmarking
2. **Storage Compatibility**: Extensive testing across all storage backends
3. **Migration Failures**: Robust rollback mechanisms

### Operational Risks

1. **User Adoption**: Provide clear migration path and documentation
2. **Backward Compatibility**: Maintain support for existing workspace API
3. **Data Loss**: Implement comprehensive backup and validation procedures

## Success Criteria

### Functional Requirements

- [ ] SRN parsing and validation working correctly
- [ ] All storage backends support scope-based operations
- [ ] API endpoints accept and process scope parameters
- [ ] Migration tools successfully convert workspace data
- [ ] Backward compatibility maintained

### Performance Requirements

- [ ] Query response time increase < 10%
- [ ] Storage overhead increase < 5%
- [ ] Migration completes within acceptable timeframes
- [ ] System remains stable under scope-based load

### Quality Requirements

- [ ] Test coverage > 90%
- [ ] Documentation complete and accurate
- [ ] Error handling comprehensive
- [ ] Code review approval from team

## Timeline Summary

- **Week 1-2**: Core SRN infrastructure
- **Week 3-4**: Storage backend integration
- **Week 5-6**: API integration and backward compatibility
- **Week 7-8**: Advanced features and optimization
- **Week 9**: Testing, documentation, and deployment preparation

## Resource Requirements

- **Development**: 1-2 senior developers
- **Testing**: 1 QA engineer
- **Documentation**: Technical writer support
- **Infrastructure**: Test environments for all storage backends
