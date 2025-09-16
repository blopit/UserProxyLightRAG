# Task01: Scope Resource Name (SRN) Implementation - Research Context

## Executive Summary

This document provides comprehensive research and context for implementing a Scope Resource Name (SRN) system in LightRAG to enable sophisticated data partitioning beyond the current workspace-based approach. The SRN system will allow hierarchical organization of data by workspace, user, project, thread, and topic.

## Current State Analysis

### Existing Workspace System

LightRAG currently implements workspace-based data isolation through several mechanisms:

1. **File-based Storage**: Uses workspace subdirectories
   - `JsonKVStorage`, `JsonDocStatusStorage`, `NetworkXStorage`, `NanoVectorDBStorage`, `FaissVectorDBStorage`

2. **Collection-based Storage**: Adds workspace prefix to collection names
   - `RedisKVStorage`, `MilvusVectorDBStorage`, `QdrantVectorDBStorage`, `MongoKVStorage`, etc.

3. **Relational Storage**: Uses workspace field for logical separation
   - `PGKVStorage`, `PGVectorStorage`, `PGDocStatusStorage`

4. **Graph Storage**: Uses labels for data isolation
   - `Neo4JStorage`, `MemgraphStorage`

### Current API Structure

The LightRAG API consists of three main router modules:
- `document_routes.py`: Document management and indexing
- `query_routes.py`: RAG query processing
- `graph_routes.py`: Knowledge graph operations

### Storage Architecture

LightRAG uses four storage types:
- **KV_STORAGE**: LLM response cache, text chunks, document information
- **VECTOR_STORAGE**: Entity vectors, relation vectors, chunk vectors
- **GRAPH_STORAGE**: Entity relation graph
- **DOC_STATUS_STORAGE**: Document indexing status

## SRN System Design

### SRN Format Specification

```
1.<ws32>.<subject_type>.<subject_id>[.proj_<project>][.thr_<thread>][.top_<topic>]
```

**Components**:
- `1.`: Version prefix for backward compatibility
- `<ws32>`: 32-character lowercase hex UUID (workspace identifier)
- `<subject_type>`: Subject type (`user`, `agent`, `workspace`, `contact`, `project`, `system`)
- `<subject_id>`: Unique identifier (alphanumeric, underscore, hyphen; max 63 chars)
- Optional segments:
  - `.proj_<project>`: Project-specific context
  - `.thr_<thread>`: Thread-specific context
  - `.top_<topic>`: Topic-specific context

### Canonicalization Rules

1. Convert to lowercase
2. Normalize Unicode to NFC (Canonical Composition)
3. Validate workspace UUID format (32-char hex)
4. Enforce 63-character limit per segment
5. Validate character sets: `[a-z0-9_-]`

### Examples

```
1.abc12345abcd12345abc1234567890ab.user.johndoe
1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projecta
1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projecta.thr_discussion1
1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projecta.thr_discussion1.top_ai_research
```

## Implementation Strategy

### Phase 1: Core SRN Infrastructure

1. **SRN Parser and Validator**
   - Create `lightrag/scope/srn.py` module
   - Implement parsing, validation, and canonicalization
   - Add comprehensive error handling

2. **Scope Context Manager**
   - Create `lightrag/scope/context.py` module
   - Manage scope resolution and inheritance
   - Handle scope-based filtering

### Phase 2: Storage Adaptations

1. **Storage Interface Extensions**
   - Extend storage interfaces to support SRN-based partitioning
   - Maintain backward compatibility with workspace system
   - Add scope-aware query methods

2. **Migration Strategy**
   - Provide migration tools for existing workspace data
   - Support hybrid workspace/SRN operation during transition

### Phase 3: API Integration

1. **Query API Enhancements**
   - Add SRN parameter to query endpoints
   - Implement scope-based filtering
   - Maintain backward compatibility

2. **Document API Updates**
   - Support SRN-based document insertion
   - Enable scope-aware document management

### Phase 4: Advanced Features

1. **Scope Inheritance**
   - Implement hierarchical scope resolution
   - Support partial scope queries

2. **Performance Optimization**
   - Add scope-based indexing
   - Optimize query performance for hierarchical scopes

## Technical Considerations

### Performance Impact

1. **Query Performance**: Additional scope filtering may impact query speed
2. **Storage Overhead**: SRN metadata will increase storage requirements
3. **Index Strategy**: Need efficient indexing for scope-based queries

### Backward Compatibility

1. **Workspace Migration**: Existing workspace data should map to SRN format
2. **API Compatibility**: Existing API calls should continue working
3. **Storage Compatibility**: Support both workspace and SRN storage formats

### Security Considerations

1. **Scope Validation**: Prevent scope injection attacks
2. **Access Control**: Ensure proper scope-based access restrictions
3. **Data Isolation**: Maintain strict data separation between scopes

## Multi-Tenant Architecture Patterns

### Research Findings

Based on industry research, successful multi-tenant data partitioning strategies include:

1. **Hierarchical Namespaces**: Azure Storage's path-based tenant identification
2. **Scope-based Partitioning**: Grafana Loki's tenant ID partitioning
3. **Resource Naming**: Unity Catalog's unified governance approach

### Best Practices

1. **Consistent Naming**: Use consistent, predictable naming patterns
2. **Efficient Indexing**: Design indexes to support scope-based queries
3. **Graceful Degradation**: Handle partial scope information gracefully
4. **Audit Trail**: Maintain scope-based audit logs

## Implementation Challenges

### Technical Challenges

1. **Storage Backend Variations**: Different storage backends require different SRN implementations
2. **Query Complexity**: Scope-based queries may become complex
3. **Performance Optimization**: Maintaining query performance with additional scope filtering

### Operational Challenges

1. **Migration Complexity**: Moving from workspace to SRN system
2. **Training Requirements**: Users need to understand SRN format
3. **Debugging Complexity**: Troubleshooting scope-related issues

## Success Metrics

1. **Functional Metrics**:
   - Successful SRN parsing and validation
   - Correct scope-based data isolation
   - Backward compatibility maintenance

2. **Performance Metrics**:
   - Query response time impact < 10%
   - Storage overhead < 5%
   - Index efficiency maintenance

3. **Usability Metrics**:
   - API adoption rate
   - Error rate reduction
   - User satisfaction scores

## Next Steps

1. Create detailed implementation specifications
2. Develop SRN core modules
3. Implement storage backend adaptations
4. Create comprehensive test suite
5. Develop migration tools
6. Update documentation and examples

## References

- LightRAG codebase analysis
- Multi-tenant architecture patterns
- Azure Storage partitioning strategies
- Industry best practices for scope-based systems
