"""Diagnostic tests to isolate user query handling issues."""

import pytest
import json
import sys
import os
import tempfile
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.agent.agent import Agent
from examples.domain_configs import DND_CONFIG


@pytest.fixture(scope="module")
def llm_service():
    """Create an LLM service instance for testing."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "query_diagnosis"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "query_diagnosis.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "query_diagnosis",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def evaluation_llm_service():
    """Create a separate LLM service for evaluation."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "query_diagnosis"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "evaluation.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.1,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "query_evaluation",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def agent_with_redundant_context(llm_service):
    """Create an agent with deliberately redundant context to reproduce the issue."""
    
    # Create temporary files
    temp_memory_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_memory_file.close()
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_guid="query_diagnosis_test",
        memory_file=temp_memory_file.name,
        domain_config=DND_CONFIG,
        llm_service=llm_service,
        max_recent_conversation_entries=10,
        importance_threshold=2
    )
    
    # Create agent
    agent = Agent(
        llm_service=llm_service,
        memory_manager=memory_manager,
        domain_name="dnd_campaign",
        logger=None
    )
    
    # Initialize with campaign data
    agent.memory.create_initial_memory(DND_CONFIG["initial_data"])
    
    # Add repetitive context that reproduces the problem
    redundant_conversations = [
        ("user", "I need to find goblins in the Whisperwood"),
        ("agent", "Captain Sara suspects goblin activity within the Whisperwood, driven by recent magical anomalies emanating from the ruins. The goblins utilize trickery and ambushes."),
        ("user", "actively look for goblins"),
        ("agent", "Okay, let's get to work! The party needs to actively look for goblins. Captain Sara suspects goblin activity within the Whisperwood, driven by recent magical anomalies emanating from the ruins. The goblins utilize trickery and ambushes. Let's proceed with caution!"),
        ("user", "look for goblins"),
        ("agent", "Okay, let's get to work! The party needs to actively look for goblins. Captain Sara suspects goblin activity within the Whisperwood, driven by recent magical anomalies emanating from the ruins. The goblins utilize trickery and ambushes. Let's proceed with caution!")
    ]
    
    # Add conversations to create redundant context
    for role, content in redundant_conversations:
        memory_manager.add_conversation_entry({
            "role": role,
            "content": content
        })
    
    yield agent
    
    # Cleanup
    try:
        os.unlink(temp_memory_file.name)
    except:
        pass


def create_query_evaluation_prompt(user_query: str, agent_response: str, context_info: dict) -> str:
    """Create prompt for evaluating agent query responses."""
    return f"""
You are an expert evaluator assessing an AI agent's response to a user query in a D&D campaign context.

USER_QUERY: "{user_query}"

AGENT_RESPONSE: "{agent_response}"

CONTEXT_PROVIDED_TO_AGENT:
- Static Memory: {len(context_info.get('static_memory', ''))} characters
- Previous Context Entries: {len(context_info.get('previous_context', []))}
- Semantically Relevant Context Entries: {len(context_info.get('semantic_context', []))}
- Recent Conversation History Entries: {len(context_info.get('recent_history', []))}

Context Details:
{json.dumps(context_info, indent=2)[:1000]}...

Evaluate the agent's response on the following criteria (1-10 scale):

1. RELEVANCE: Does the response directly address the user's query?
2. ACTIONABILITY: Does the response provide actionable information or advance the narrative?
3. SPECIFICITY: Does the response give specific details rather than vague generalities?
4. FRESHNESS: Does the response avoid repeating recent conversation content?
5. ENGAGEMENT: Would this response engage the user and encourage continued interaction?
6. APPROPRIATENESS: Is the response appropriate for a D&D DM in this situation?

Provide response as JSON:
{{
  "scores": {{
    "relevance": score,
    "actionability": score,
    "specificity": score,
    "freshness": score,
    "engagement": score,
    "appropriateness": score
  }},
  "overall_score": average_score,
  "issues_identified": ["list of specific problems with the response"],
  "expected_response_type": "what type of response would be better",
  "diagnosis": "assessment of why the agent gave this response",
  "improvement_suggestions": ["specific suggestions for improvement"]
}}
"""


def parse_evaluation_response(response: str) -> dict:
    """Parse LLM evaluation response."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
    
    return {
        "scores": {"error": "Failed to parse"},
        "overall_score": 0,
        "issues_identified": ["Evaluation parsing failed"],
        "expected_response_type": "Unknown",
        "diagnosis": "Could not parse evaluation",
        "improvement_suggestions": ["Fix evaluation parsing"]
    }


def test_direct_question_handling(agent_with_redundant_context, evaluation_llm_service):
    """Test how the agent handles direct questions that require specific answers."""
    
    agent = agent_with_redundant_context
    
    print("\n=== Direct Question Handling Test ===")
    
    # Test direct questions that should get specific answers
    test_queries = [
        "are there any goblins nearby?",
        "what do I see in the Whisperwood?", 
        "do I spot any goblin tracks?",
        "what happens when I search for goblins?"
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        
        # Get agent response (async)
        response = asyncio.run(agent.process_message(query))
        print(f"Agent response: {response[:100]}...")
        
        # Get memory context for analysis
        memory = agent.memory.get_memory()
        context_info = {
            "static_memory": memory.get("static_memory", ""),
            "previous_context": memory.get("context", []),
            "semantic_context": [],  # Would need to extract from RAG if available
            "recent_history": []  # Would need to extract recent conversations
        }
        
        # Evaluate the response
        evaluation_prompt = create_query_evaluation_prompt(query, response, context_info)
        evaluation_response = evaluation_llm_service.generate(
            evaluation_prompt,
            options={"temperature": 0.1, "stream": False}
        )
        
        evaluation = parse_evaluation_response(evaluation_response)
        
        # Store results
        result = {
            "query": query,
            "response": response,
            "evaluation": evaluation
        }
        results.append(result)
        
        # Print evaluation summary
        print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/10")
        print(f"Issues: {evaluation.get('issues_identified', [])}")
        print(f"Expected: {evaluation.get('expected_response_type', 'N/A')}")
    
    # Analyze overall performance
    print(f"\n=== Direct Question Test Summary ===")
    
    total_score = 0
    valid_scores = 0
    
    for result in results:
        score = result["evaluation"].get("overall_score", 0)
        if score > 0:
            total_score += score
            valid_scores += 1
        
        print(f"'{result['query']}' -> Score: {score}/10")
    
    average_score = total_score / valid_scores if valid_scores > 0 else 0
    print(f"\nAverage Score: {average_score:.1f}/10")
    
    # Assert that direct questions should get reasonable scores
    assert average_score >= 5.0, f"Direct question handling too poor: {average_score:.1f}/10"
    
    return results


def test_context_redundancy_impact(agent_with_redundant_context, evaluation_llm_service):
    """Test how redundant context affects response quality."""
    
    agent = agent_with_redundant_context
    
    print("\n=== Context Redundancy Impact Test ===")
    
    # Get current memory state
    memory = agent.memory.get_memory()
    context_entries = memory.get("context", [])
    
    print(f"Context entries: {len(context_entries)}")
    
    # Analyze context for redundancy
    context_texts = [entry.get("text", "") for entry in context_entries]
    
    # Count similar entries
    similar_pairs = 0
    for i, text1 in enumerate(context_texts):
        for j, text2 in enumerate(context_texts[i+1:], start=i+1):
            # Simple similarity check
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if words1 and words2:
                similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                if similarity > 0.5:  # 50% similarity threshold
                    similar_pairs += 1
    
    print(f"Similar context pairs found: {similar_pairs}")
    
    # Test query with redundant context
    test_query = "are there any goblins nearby?"
    response = asyncio.run(agent.process_message(test_query))
    
    print(f"Query: {test_query}")
    print(f"Response: {response}")
    
    # Create evaluation for redundancy impact
    redundancy_prompt = f"""
Analyze how redundant context affects an AI agent's response quality.

CONTEXT_ENTRIES: {len(context_entries)}
SIMILAR_CONTEXT_PAIRS: {similar_pairs}

CONTEXT_CONTENT:
{json.dumps(context_texts, indent=2)[:2000]}...

USER_QUERY: "{test_query}"
AGENT_RESPONSE: "{response}"

Assess the impact of redundant context:

1. Does the agent response show signs of being overwhelmed by redundant information?
2. Is the agent just repeating information instead of providing new content?
3. Would reducing redundant context likely improve the response?

Provide response as JSON:
{{
  "redundancy_score": "1-10 scale of how redundant the context is",
  "response_quality_score": "1-10 scale of response quality", 
  "redundancy_impact": "how redundancy affected the response",
  "signs_of_overwhelm": ["specific signs the agent is overwhelmed"],
  "recommendations": ["how to reduce redundancy impact"]
}}
"""
    
    redundancy_evaluation = evaluation_llm_service.generate(
        redundancy_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    redundancy_analysis = parse_evaluation_response(redundancy_evaluation)
    
    print(f"\nRedundancy Analysis:")
    print(f"Redundancy Score: {redundancy_analysis.get('redundancy_score', 'N/A')}/10")
    print(f"Response Quality: {redundancy_analysis.get('response_quality_score', 'N/A')}/10")
    print(f"Impact: {redundancy_analysis.get('redundancy_impact', 'N/A')}")
    print(f"Signs of Overwhelm: {redundancy_analysis.get('signs_of_overwhelm', [])}")
    
    return redundancy_analysis


def test_query_type_classification(agent_with_redundant_context, evaluation_llm_service):
    """Test how different types of user inputs are handled."""
    
    agent = agent_with_redundant_context
    
    print("\n=== Query Type Classification Test ===")
    
    # Different types of user inputs
    test_inputs = [
        # Direct questions
        ("question", "are there any goblins nearby?"),
        ("question", "what do I see?"),
        ("question", "where should I go next?"),
        
        # Commands/Actions  
        ("command", "attack the goblins"),
        ("command", "search for tracks"),
        ("command", "move into the forest"),
        
        # Statements/Information
        ("statement", "I found goblin tracks"),
        ("statement", "the forest looks dangerous"),
        ("statement", "I have a sword")
    ]
    
    results = []
    
    for expected_type, user_input in test_inputs:
        print(f"\nTesting {expected_type}: '{user_input}'")
        
        response = asyncio.run(agent.process_message(user_input))
        print(f"Response: {response[:80]}...")
        
        # Evaluate response appropriateness for input type
        type_evaluation_prompt = f"""
Evaluate how well an AI agent handles different types of user input.

USER_INPUT: "{user_input}"
EXPECTED_TYPE: {expected_type}
AGENT_RESPONSE: "{response}"

For each input type, evaluate appropriateness (1-10):

QUESTIONS should get:
- Specific answers to what was asked
- New information or description
- Narrative advancement

COMMANDS should get:
- Action results or outcomes
- Environmental responses
- Story progression

STATEMENTS should get:
- Acknowledgment without repetition
- Building on the new information
- Incorporating into ongoing narrative

Rate the response appropriateness: {{
  "type_handling_score": score,
  "response_type_match": "does response match expected type handling",
  "issues": ["problems with how this input type was handled"],
  "ideal_response": "what type of response would be better"
}}
"""
        
        type_evaluation = evaluation_llm_service.generate(
            type_evaluation_prompt,
            options={"temperature": 0.1, "stream": False}
        )
        
        evaluation = parse_evaluation_response(type_evaluation)
        
        result = {
            "input": user_input,
            "expected_type": expected_type,
            "response": response,
            "evaluation": evaluation
        }
        results.append(result)
        
        print(f"Type Handling Score: {evaluation.get('type_handling_score', 'N/A')}/10")
    
    # Summary by type
    print(f"\n=== Query Type Summary ===")
    
    type_scores = {}
    for result in results:
        expected_type = result["expected_type"]
        score = result["evaluation"].get("type_handling_score", 0)
        
        if expected_type not in type_scores:
            type_scores[expected_type] = []
        type_scores[expected_type].append(score)
    
    for query_type, scores in type_scores.items():
        avg_score = sum(scores) / len(scores) if scores else 0
        print(f"{query_type.title()} handling: {avg_score:.1f}/10 (from {len(scores)} tests)")
    
    return results