# alt entity and relationship extraction approach

## Overview

Rely on the LLM to identify entities/nodes and relationships and match them to existing nodes and relationships

Note: This is the most important function of the graph manager and only an LLM can do it well.

## Proposal

Create an alternative entity extractor class: alt_entity_extractor.py

### Entity Extraction

Implement this approach:
- Whenever the MemoryManager generates a new conversation entry - with a digest
  - Have the LLM analyze the full text of the entry AND the digest for graph-worthy entities/nodes
    - Using a specialized templates/entity_extraction.prompt
  - The prompt should have the LLM generate a list of CANDIDATE nodes
    - i.e. a proper JSON array of node objects
  - Then for each CANDIDATE node, use RAG to find the most similar ACTUAL nodes that are already in the graph
  - Then make another call to the LLM and, again, have it analyze the full text of the entry AND the digest for graph-worth nodes
    - This time, include in the prompt context the list of existing nodes returned by RAG
    - This time, the output should be a list of the nodes which includes:
      - ONLY existing nodes that are referenced in the new conversation entry
      - AND new nodes that need to be created and added to the graph
  - Add the new nodes to the graph
  - Add any new information from the conversation entry to the existing nodes referenced by the LLM

### Relationship Extraction

Then, during relationship_extraction:
- Have the LLM analyze the full text of the entry AND the digest for relationships between nodes
    - Using a specialized templates/relationship_extraction.prompt
  - Important: Include in the prompt context the list of nodes from the entity_extraction phase
  - The LLM should reference only these nodes
  - The LLM should return a list of relationships
    - i.e. a proper JSON array of relationship objects
  - Add the new relationships to the graph
    - If a relationship already exists (same type and properties) then do not add it
  - Add any new information from the conversation entry to the existing relationships referenced by the LLM


  ### Proposed Improvements to Entity Extraction
  - give the entity extraction prompt the most relevant (RAG) nodes so it can match them to entities referenced in the new conversation entry
    - provide the existing node list WITH unique node ids so the LLM can build a list of referenced nodes using the unique ids
  - all entities/nodes in the graph should maintain a list of conversation history guids in which the nodes were referenced
  - first LLM pass should build a list of node CANDIDATES
  - second LLM pass should match the CANDIDATES to existing nodes - using unique node ids
    - new nodes will have a blank id so the graph manager will know to add them to the graph