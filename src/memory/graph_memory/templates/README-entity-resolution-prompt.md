# README-entity-resolution-prompt

A knowledge graph is made up of nodes (entities) and relationships (links). LLMs can be used to analyze unstructured text and identify the entities and relationships in the text. Then the entities and relationship can be added to the graph as nodes and links. This approach can be used to automatically populate a knowledge graph - something that previously required time-consuming, expensive, human effort. The key to making this approach work well is "entity resolution", the process of matching new "candidate" nodes to existing nodes, so that the graph does not get filled with duplicate nodes. Once the nodes are added, links can be added with little chance of producing duplicate links. So entity resolution is the key.

Entity resolution can be accomplished using 2-pass process:
- Make a call to an LLM to identify candidate nodes
  - OUTPUT: A list of candidate node objects
- Make a second call to determine which of the candidate nodes map to existing nodes
  - Provide the LLM with a list of existing nodes
    - Use RAG to select the most relevant set of existing nodes to include
  - Have the LLM match the candidate nodes to existing nodes
  - Add any unmatched nodes the the graph as new nodes

  LLMs are good at matching candidate nodes with existing nodes and in many cases can match many nodes at once. But the most accuracte approach is to have the LLM consider only one candidate at a time:
    - Choose a list of existing nodes using RAG
      - Compare the candidate node's description to the descriptions of all exisiting nodes and take the top n results
    - Ask the LLM to resolve the candidate node (match it with an existing node)
    - If there is no match, add the candidate as a new node
    - If there is a match, add the candidate to the RAG list for all subsequent candidate resolutions
    - when nodes are added to the graph their metadata should include a list of conversation history guids in which the nodes were referenced
    - Repeat the process for all candidate nodes


### Entity Resolution Prompt Example

```
You are a Node ID Resolver for knowledge graph construction. Your task is to analyze a set of Existing Node Data and a set of Candidate Nodes, and determine the corresponding existing node IDs for the candidates.

**Instructions:**

1.  **Existing Node Data:** You will be provided with existing node data. This data will include ‘existing_node_id‘, ‘type‘, and ‘description’ fields

2.  **Candidate Nodes:** You will also be provided with a JSON array of candidate node objects.

3.  **Resolution:** For each candidate node object in the array, carefully examine the existing node data to determine if a matching node exists. If an existing match is found, set the resolved_node_id of the candidate node to the id of the matching existing node. If there is no good mach, set the resolved_node_id of the candidate nodd to "<NEW>"

4.  **Match Justification:** For each resolved node, provide a resolution_justification, explaining why the nodes are a valid match

5.  **Resolution Confidence:** A number from 0 to 1 indicating the likelyhood that a match with an existing node is correct. For new, non-resolved nodes, this value should be 0 

6.  **Output Format:**  For each candidate node, respond with the following JSON array "tuple":

    [candidate_id, existing_node_id, resolution_justification]

7. **Handling No Match:** If a candidate node does not have a corresponding existing node in the provided data, the value for "existing_node_id" should be set to "<NEW>" and the resolution_justification should be left empty.

8. **Matching Strictness:** Pay close attention to the provided existing node data and ensure that you match based on the description AND type fields. Be strict. Only match nodes if their descriptions truly describe the same entity AND the node types match. Set the resolved_node_id to "<NEW"> if the nodes are not an exact match.

9. **Resolved Nodes:** Output a JSON array of array tuples in the specified Output Format with the existing_node_id element populated with either an existing node id or "<NEW>"


**Existing Node Data:**

  existing_node_id: "location_adbb186c"
  type: "location"
  description: "The Lost Valley: A settlement experiencing increased monster activity"

  existing_node_id: "location_305bed4d"
  type: "location"
  description: "mountains: Impassable mountains forming a barrier around The Lost Valley"

  existing_node_id: "concept_90c36e8e"
  type: "concept"
  description: "magical anomalies: Strange magical energy discharges"

  existing_node_id: "character_c96e26d8"
  type: "character"
  description: "character: Elena, The Mayor of a settlement"

  existing_node_id: "character_f6b1a5e6"
  type: "character"
  description: "character: Theron, A character focused on decoding inscriptions"

  existing_node_id: "concept_f7d6fe2f"
  type: "concept"
  description: "ruins: Ruins of a past civilization, a common subject of study"

  existing_node_id: "location_1b4c6d95"
  type: "location"
  description: "ruins: "Ancient structures built by past civilizations"

  existing_node_id: "object_0754e0ce"
  type: "object"
  description: "inscriptions: Texts carved on ancient ruins, requiring interpretation"

  existing_node_id: "location_14c9a579"
  type: "location"
  description: "trade route: The established path for commercial goods between settlements"

  existing_node_id: "character_2d049f36"
  type: "character"
  description: "merchants: Individuals involved in trade and commerce"

  existing_node_id: "object_264f03a2"
  type: "object"
  description: "artifacts: Valuable and potentially magical objects found within the ruins"

  existing_node_id: "concept_bcff3a0e"
  type: "concept"
  description: "magical effects: Random occurrences of magic"

  existing_node_id: "location_5b6b6a90"
  type: "location"
  description: "settlements: Groups of people living together"

**Candidate Nodes:**

candidate_nodes = [
    {
        "candidate_id": "candidate_06",
        "type": "concept",
        "description": "Magical Anomalies, Random magical effects impacting local wildlife, possibly connected to the ancient ruins."
    }
]

REMEMBER: Your task is to look at the Existing Node Data and then add an appropriate resolved_node_id to the Candidate Nodes - if there is reasonably good match.

REMEMBER: Be strict. Only match nodes if their descriptions truly describe the same entity AND the node types match. Set the resolved_node_id to "<NEW"> if the nodes are not an exact match.

REMEMBER: For each resolved node, provide a resolution_justification, explaining why the nodes are a valid match

You should output a JSON array of array tuples.

**Resolved Nodes:**
```


