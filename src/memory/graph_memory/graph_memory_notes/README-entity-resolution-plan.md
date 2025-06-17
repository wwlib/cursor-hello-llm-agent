# README-entity-resolution-plan

Based on analysis of the README-entity-resolution-prompt.md document, here's a comprehensive TODO list for implementing the recommended improvements to the entity extraction process:

# Entity Resolution Implementation TODO List

## Phase 1: Core Infrastructure Updates

### 1.1 Update Entity Resolution Output Format
- [ ] **Fix entity resolution prompt output format inconsistency**
  - Current format: `[candidate_id, existing_node_id, resolution_justification]`
  - Missing: confidence score mentioned in instruction #5
  - **Action**: Update prompt to include confidence in output tuple: `[candidate_id, existing_node_id, resolution_justification, confidence]`

### 1.2 Implement One-at-a-Time Processing Option
- [ ] **Add iterative single-candidate resolution mode**
  - Current: Processes all candidates in batch
  - Recommended: Process one candidate at a time for higher accuracy
  - **Action**: Add `process_individually` parameter to `EntityExtractor`
  - **Action**: Implement `_resolve_single_candidate()` method

### 1.3 Conversation History GUID Tracking
- [ ] **Add conversation_history_guids to node metadata**
  - **Action**: Update node schema to include `conversation_history_guids: List[str]`
  - **Action**: Pass conversation GUID to entity extraction methods
  - **Action**: Update graph manager to track conversation references per node

## Phase 2: Enhanced RAG Integration

### 2.1 Improve RAG-Based Candidate Resolution
- [ ] **Implement proper RAG pipeline for each candidate**
  - **Action**: Create `_get_rag_candidates_for_entity()` method
  - **Action**: Use semantic similarity on candidate description vs existing node descriptions
  - **Action**: Filter RAG results by entity type before LLM resolution

### 2.2 Dynamic RAG List Updates
- [ ] **Add resolved candidates to RAG context for subsequent resolutions**
  - Current: Static RAG context per batch
  - Recommended: Add newly matched entities to RAG pool for next candidates
  - **Action**: Implement `_update_rag_context_with_resolved()` method

## Phase 3: Resolution Pipeline Overhaul

### 3.1 Implement Structured Resolution Process
- [ ] **Create dedicated resolution pipeline using entity_resolution.prompt**
  - **Action**: Create `EntityResolver` class separate from `EntityExtractor`
  - **Action**: Use structured prompt format with proper existing node data formatting
  - **Action**: Parse tuple array responses: `[candidate_id, existing_node_id, justification, confidence]`

### 3.2 Add Resolution Quality Controls
- [ ] **Implement confidence-based decision making**
  - **Action**: Add configurable confidence thresholds (e.g., 0.8 for auto-match)
  - **Action**: Flag low-confidence matches for review
  - **Action**: Add resolution metrics tracking

## Phase 4: Enhanced Entity Management

### 4.1 Improve Duplicate Detection
- [ ] **Better semantic matching for existing duplicates**
  - Example duplicates found: "ruins" vs "ancient ruins", "Sara" vs "Captain Sara"
  - **Action**: Add alias-aware matching in RAG selection
  - **Action**: Implement fuzzy name matching for character entities
  - **Action**: Add post-resolution duplicate cleanup

### 4.2 Add Entity Metadata Enrichment
- [ ] **Track entity mention statistics and context**
  - **Action**: Update `mention_count` when entities are referenced
  - **Action**: Add `last_conversation_guid` to track recent usage
  - **Action**: Store resolution confidence scores in entity metadata

## Phase 5: Template and Prompt Improvements

### 5.1 Update Entity Resolution Prompt Template
- [ ] **Fix inconsistencies in entity_resolution.prompt**
  - **Action**: Add confidence score to output format specification
  - **Action**: Fix typos ("mach" → "match", "nodd" → "node")
  - **Action**: Clarify tuple array format with confidence score

### 5.2 Enhance Entity Extraction Prompt
- [ ] **Improve entity_extraction.prompt for better candidate generation**
  - **Action**: Add more specific guidance for candidate quality
  - **Action**: Include domain-specific entity extraction examples
  - **Action**: Add instructions for handling ambiguous entities

## Phase 6: Integration and Testing

### 6.1 Update EntityExtractor Class
- [ ] **Refactor to use new resolution pipeline**
  - **Action**: Replace current `_resolve_entities_with_rag()` with structured resolver
  - **Action**: Add conversation GUID parameter to extraction methods
  - **Action**: Implement both batch and individual processing modes

### 6.2 Add Comprehensive Testing
- [ ] **Create test cases for resolution scenarios**
  - **Action**: Test exact matches, partial matches, no matches
  - **Action**: Test confidence thresholds and decision making
  - **Action**: Test conversation GUID tracking
  - **Action**: Test duplicate detection improvements

## Phase 7: Configuration and Monitoring

### 7.1 Add Resolution Configuration Options
- [ ] **Make resolution behavior configurable**
  - **Action**: Add config for individual vs batch processing
  - **Action**: Add confidence threshold settings
  - **Action**: Add RAG result limits and similarity thresholds

### 7.2 Add Resolution Analytics
- [ ] **Track resolution performance metrics**
  - **Action**: Log resolution success rates
  - **Action**: Track confidence score distributions
  - **Action**: Monitor duplicate detection effectiveness

## Priority Implementation Order

1. **High Priority**: Phase 1 (Core Infrastructure) - Fix fundamental issues
2. **High Priority**: Phase 3 (Resolution Pipeline) - Implement proper resolution
3. **Medium Priority**: Phase 2 (RAG Integration) - Improve accuracy
4. **Medium Priority**: Phase 4 (Entity Management) - Handle duplicates
5. **Low Priority**: Phase 5-7 (Polish and Monitoring) - Quality improvements

## Key Improvements from Current Implementation

### Current Issues Addressed:
- **Output Format Inconsistency**: Standardize resolution prompt output with confidence scores
- **Batch vs Individual Processing**: Add option for one-at-a-time processing for higher accuracy
- **Missing Conversation Tracking**: Implement GUID tracking as specified in requirements
- **Incomplete RAG Integration**: Proper use of RAG with dynamic context updates
- **Duplicate Entity Problem**: Better detection and handling of entity duplicates

### Architecture Changes:
- **Separate EntityResolver Class**: Dedicated resolution logic using structured prompts
- **Enhanced Metadata**: Conversation GUID tracking and resolution confidence storage
- **Configurable Processing**: Support both batch and individual candidate processing
- **Quality Controls**: Confidence thresholds and resolution analytics

This implementation plan addresses all the key recommendations from the README-entity-resolution-prompt.md document, particularly focusing on the one-at-a-time processing approach, conversation GUID tracking, and proper use of the structured entity resolution prompt format.



