"""Test improved query handling after Phase 2 fixes."""

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
    guid = "query_improvements"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "query_improvements.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "query_improvements",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def evaluation_llm_service():
    """Create a separate LLM service for evaluation."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "query_improvements"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "evaluation_improvements.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.1,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "query_evaluation_improvements",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def improved_agent(llm_service):
    """Create an agent with improved query handling."""
    
    # Create temporary files
    temp_memory_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_memory_file.close()
    
    # Create memory manager
    memory_manager = MemoryManager(
        memory_guid="query_improvements_test",
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
    
    yield agent
    
    # Cleanup
    try:
        os.unlink(temp_memory_file.name)
    except:
        pass


def create_improvement_evaluation_prompt(user_query: str, agent_response: str) -> str:
    """Create prompt for evaluating improved query responses."""
    return f"""
You are evaluating whether an AI agent's response shows improvement over previous repetitive patterns.

USER_QUERY: "{user_query}"
AGENT_RESPONSE: "{agent_response}"

EVALUATION CRITERIA:

1. RESPONSE VARIETY (1-10): Does the response avoid starting with repetitive phrases like "Okay, let's investigate"?
2. DIRECTNESS (1-10): Does the response directly address the user's question rather than providing excessive context?
3. CONCISENESS (1-10): Is the response appropriately concise for the question asked?
4. ENGAGEMENT (1-10): Does the response engage the user with specific, actionable information?

Provide response as JSON:
{{
  "scores": {{
    "response_variety": score,
    "directness": score,
    "conciseness": score,
    "engagement": score
  }},
  "overall_improvement_score": average_score,
  "starts_with_repetitive_phrase": true/false,
  "provides_direct_answer": true/false,
  "improvement_notes": "specific observations about the response quality",
  "remaining_issues": ["any remaining problems with the response"]
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
        "overall_improvement_score": 0,
        "starts_with_repetitive_phrase": True,
        "provides_direct_answer": False,
        "improvement_notes": "Evaluation parsing failed",
        "remaining_issues": ["Could not evaluate response"]
    }


def test_improved_response_patterns(improved_agent, evaluation_llm_service):
    """Test that responses no longer follow repetitive patterns."""
    
    agent = improved_agent
    
    print("\n=== Improved Response Pattern Test ===")
    
    # Test the same queries that previously showed repetitive patterns
    test_queries = [
        "are there any goblins nearby?",
        "what do I see in the Whisperwood?", 
        "do I spot any goblin tracks?",
        "what happens when I search for goblins?"
    ]
    
    results = []
    repetitive_count = 0
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        
        # Get agent response (async)
        response = asyncio.run(agent.process_message(query))
        print(f"Agent response: {response}")
        
        # Check for repetitive start patterns
        starts_with_okay = response.lower().startswith("okay,")
        if starts_with_okay:
            repetitive_count += 1
            print("❌ Still starts with 'Okay,'")
        else:
            print("✅ Avoids repetitive opening")
        
        # Evaluate the response
        evaluation_prompt = create_improvement_evaluation_prompt(query, response)
        evaluation_response = evaluation_llm_service.generate(
            evaluation_prompt,
            options={"temperature": 0.1, "stream": False}
        )
        
        evaluation = parse_evaluation_response(evaluation_response)
        
        # Store results
        result = {
            "query": query,
            "response": response,
            "evaluation": evaluation,
            "starts_with_okay": starts_with_okay
        }
        results.append(result)
        
        # Print evaluation summary
        print(f"Improvement Score: {evaluation.get('overall_improvement_score', 'N/A')}/10")
        print(f"Direct Answer: {evaluation.get('provides_direct_answer', 'N/A')}")
        print(f"Remaining Issues: {evaluation.get('remaining_issues', [])}")
    
    # Analyze overall improvements
    print(f"\n=== Improvement Test Summary ===")
    
    total_score = 0
    valid_scores = 0
    
    for result in results:
        score = result["evaluation"].get("overall_improvement_score", 0)
        if score > 0:
            total_score += score
            valid_scores += 1
        
        print(f"'{result['query']}' -> Score: {score}/10")
    
    average_score = total_score / valid_scores if valid_scores > 0 else 0
    print(f"\nAverage Improvement Score: {average_score:.1f}/10")
    print(f"Repetitive responses: {repetitive_count}/{len(test_queries)}")
    
    # Assert improvements
    assert repetitive_count <= 1, f"Too many responses still start with 'Okay,': {repetitive_count}/{len(test_queries)}"
    assert average_score >= 7.0, f"Improvement score too low: {average_score:.1f}/10"
    
    return results


def test_response_variety_across_multiple_queries(improved_agent):
    """Test that multiple similar queries get varied responses."""
    
    agent = improved_agent
    
    print("\n=== Response Variety Test ===")
    
    # Ask the same question multiple times to test variety
    test_query = "are there any goblins nearby?"
    responses = []
    
    for i in range(3):
        print(f"\nQuery {i+1}: '{test_query}'")
        response = asyncio.run(agent.process_message(test_query))
        responses.append(response)
        print(f"Response: {response[:100]}...")
    
    # Check for variety in responses
    unique_starts = set()
    for response in responses:
        # Get first 20 characters to check opening variety
        start = response[:20].lower().strip()
        unique_starts.add(start)
    
    print(f"\nUnique response openings: {len(unique_starts)}")
    print(f"Response starts: {unique_starts}")
    
    # Should have some variety, not identical responses
    assert len(unique_starts) >= 2, f"Responses too similar: only {len(unique_starts)} unique openings"
    
    return responses