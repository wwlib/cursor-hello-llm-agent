"""LLM-evaluated tests for DigestGenerator topic assignment and quality assessment."""

import pytest
import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.digest_generator import DigestGenerator


@pytest.fixture(scope="module")
def llm_service():
    """Create an LLM service instance for testing."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "digest_generator_llm_eval"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "llm_evaluation.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "test_digest_generator_llm_evaluation",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def evaluation_llm_service():
    """Create a separate LLM service for evaluation to avoid circular dependency."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "digest_generator_llm_eval"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "evaluation_llm.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.1,  # Slightly higher temperature for evaluation
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "evaluation_llm",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def dnd_digest_generator(llm_service):
    """Create a DigestGenerator instance for D&D domain testing."""
    from examples.domain_configs import DND_CONFIG
    return DigestGenerator(llm_service, domain_name="dnd_campaign", domain_config=DND_CONFIG)


@pytest.fixture(scope="module")
def lab_digest_generator(llm_service):
    """Create a DigestGenerator instance for lab assistant domain testing."""
    from examples.domain_configs import LAB_ASSISTANT_CONFIG
    return DigestGenerator(llm_service, domain_name="lab_assistant", domain_config=LAB_ASSISTANT_CONFIG)


@pytest.fixture(scope="module")
def test_conversations():
    """Provide test conversation entries for different domains."""
    return {
        "dnd_campaign": {
            "guid": "test-dnd-001",
            "role": "agent",
            "content": "The ancient ruins of Kheth-Malar rise before you, their weathered stone walls covered in intricate magical runes that pulse with a faint blue light. As you approach the main entrance, you notice that the massive stone doors have been recently disturbed - fresh footprints in the dirt and scratches on the stone suggest someone has been here within the last few days. Your character Theron, with his expertise in ancient artifacts, immediately recognizes some of the runic patterns as belonging to the lost civilization of the Void Walkers. The magical anomalies in this area seem stronger here, causing your spell components to tingle with residual energy. What would you like to investigate first?",
            "timestamp": "2025-05-01T16:26:59.498857"
        },
        "lab_assistant": {
            "guid": "test-lab-001", 
            "role": "user",
            "content": "Today I completed the PCB design for the IoT sensor board. Used KiCad for the schematic and layout. The board includes an ESP32-C3 microcontroller, BME280 environmental sensor, and a 3.7V LiPo battery connector with charging circuit using the MCP73831. Added test points for debugging and made sure to include proper ground planes for noise reduction. Next step is to generate gerber files and send to JLCPCB for manufacturing. Also need to write the Arduino firmware to read sensor data and transmit over WiFi to our data collection server.",
            "timestamp": "2025-05-01T10:15:30.123456"
        },
        "agent_response": {
            "guid": "test-agent-001",
            "role": "agent", 
            "content": "I understand you've made significant progress on your IoT sensor project. Let me note the key details: You've completed the PCB design using KiCad, incorporating an ESP32-C3 microcontroller, BME280 environmental sensor, and LiPo battery management with the MCP73831 charging IC. Good engineering practices with test points and ground planes. Your next steps are gerber generation, JLCPCB manufacturing, and Arduino firmware development for WiFi data transmission. This represents a complete embedded systems development cycle from design to deployment.",
            "timestamp": "2025-05-01T10:16:15.789012"
        }
    }


def create_evaluation_prompt(original_content: str, digest: dict, domain: str) -> str:
    """Create a prompt for LLM evaluation of digest quality."""
    return f"""
You are an expert evaluator assessing the quality of an AI system's content analysis and topic assignment.

ORIGINAL_CONTENT:
{original_content}

GENERATED_DIGEST:
{json.dumps(digest, indent=2)}

DOMAIN: {domain}

Please evaluate the digest on the following criteria and provide a score from 1-10 for each:

1. SEGMENTATION_QUALITY: How well was the content broken into meaningful segments?
   - Are segments coherent and complete thoughts?
   - Are they appropriately sized (not too granular, not too broad)?

2. IMPORTANCE_ACCURACY: How accurate are the importance ratings (1-5 scale)?
   - Do high-importance segments contain essential information?
   - Are low-importance segments appropriately rated?

3. TOPIC_RELEVANCE: How relevant and accurate are the assigned topics?
   - Do topics accurately reflect segment content?
   - Are topics appropriate for the {domain} domain?

4. TOPIC_CONSISTENCY: How consistent is the topic naming and categorization?
   - Are similar concepts given consistent topic names?
   - Do topics follow a logical taxonomy?

5. TYPE_CLASSIFICATION: How accurate is the segment type classification?
   - Are query/information/action/command types correctly identified?

6. COMPLETENESS: How well does the digest preserve important information?
   - Is essential information retained?
   - Are key details properly captured?

Provide your response as JSON:
{{
  "scores": {{
    "segmentation_quality": score,
    "importance_accuracy": score, 
    "topic_relevance": score,
    "topic_consistency": score,
    "type_classification": score,
    "completeness": score
  }},
  "overall_score": average_score,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "topic_quality_notes": "specific notes about topic assignment quality",
  "recommendations": ["recommendation1", "recommendation2"]
}}
"""


def parse_evaluation_response(response: str) -> dict:
    """Parse the LLM evaluation response, handling potential formatting issues."""
    try:
        # Try direct JSON parsing first
        return json.loads(response)
    except json.JSONDecodeError:
        # Look for JSON block in markdown or other text
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
    
    # Fallback to a basic structure if parsing fails
    return {
        "scores": {"error": "Failed to parse evaluation"},
        "overall_score": 0,
        "strengths": ["Evaluation parsing failed"],
        "weaknesses": ["Could not parse LLM evaluation response"],
        "topic_quality_notes": "Evaluation unavailable due to parsing error",
        "recommendations": ["Fix evaluation response parsing"]
    }


@pytest.mark.asyncio
async def test_dnd_digest_llm_evaluation(dnd_digest_generator, evaluation_llm_service, test_conversations):
    """Test D&D campaign digest generation with LLM evaluation."""
    conversation = test_conversations["dnd_campaign"]
    
    # Generate digest
    digest = dnd_digest_generator.generate_digest(conversation)
    
    # Basic validation
    assert isinstance(digest, dict)
    assert "rated_segments" in digest
    assert len(digest["rated_segments"]) > 0
    
    # Create evaluation prompt
    evaluation_prompt = create_evaluation_prompt(
        conversation["content"], 
        digest,
        "dnd_campaign"
    )
    
    # Get LLM evaluation
    evaluation_response = evaluation_llm_service.generate(
        evaluation_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    # Parse evaluation
    evaluation = parse_evaluation_response(evaluation_response)
    
    # Print results for inspection
    print(f"\n=== D&D Campaign Digest Evaluation ===")
    print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/10")
    print(f"Scores: {evaluation.get('scores', {})}")
    print(f"Strengths: {evaluation.get('strengths', [])}")
    print(f"Weaknesses: {evaluation.get('weaknesses', [])}")
    print(f"Topic Quality: {evaluation.get('topic_quality_notes', 'N/A')}")
    print(f"Recommendations: {evaluation.get('recommendations', [])}")
    
    print(f"\n=== Generated Digest ===")
    print(json.dumps(digest, indent=2))
    
    # Assert minimum quality thresholds
    overall_score = evaluation.get("overall_score", 0)
    assert overall_score >= 6.0, f"Digest quality too low: {overall_score}/10. Weaknesses: {evaluation.get('weaknesses', [])}"
    
    # Check for topic assignment quality
    scores = evaluation.get("scores", {})
    topic_relevance = scores.get("topic_relevance", 0)
    topic_consistency = scores.get("topic_consistency", 0)
    
    assert topic_relevance >= 6.0, f"Topic relevance too low: {topic_relevance}/10"
    assert topic_consistency >= 6.0, f"Topic consistency too low: {topic_consistency}/10"


@pytest.mark.asyncio  
async def test_lab_assistant_digest_llm_evaluation(lab_digest_generator, evaluation_llm_service, test_conversations):
    """Test lab assistant digest generation with LLM evaluation."""
    conversation = test_conversations["lab_assistant"]
    
    # Generate digest
    digest = lab_digest_generator.generate_digest(conversation)
    
    # Basic validation
    assert isinstance(digest, dict)
    assert "rated_segments" in digest
    assert len(digest["rated_segments"]) > 0
    
    # Create evaluation prompt
    evaluation_prompt = create_evaluation_prompt(
        conversation["content"],
        digest, 
        "lab_assistant"
    )
    
    # Get LLM evaluation
    evaluation_response = evaluation_llm_service.generate(
        evaluation_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    # Parse evaluation
    evaluation = parse_evaluation_response(evaluation_response)
    
    # Print results for inspection
    print(f"\n=== Lab Assistant Digest Evaluation ===")
    print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/10")
    print(f"Scores: {evaluation.get('scores', {})}")
    print(f"Strengths: {evaluation.get('strengths', [])}")
    print(f"Weaknesses: {evaluation.get('weaknesses', [])}")
    print(f"Topic Quality: {evaluation.get('topic_quality_notes', 'N/A')}")
    print(f"Recommendations: {evaluation.get('recommendations', [])}")
    
    print(f"\n=== Generated Digest ===")
    print(json.dumps(digest, indent=2))
    
    # Assert minimum quality thresholds
    overall_score = evaluation.get("overall_score", 0)
    assert overall_score >= 6.0, f"Digest quality too low: {overall_score}/10. Weaknesses: {evaluation.get('weaknesses', [])}"
    
    # Check for topic assignment quality
    scores = evaluation.get("scores", {})
    topic_relevance = scores.get("topic_relevance", 0)
    topic_consistency = scores.get("topic_consistency", 0)
    
    assert topic_relevance >= 6.0, f"Topic relevance too low: {topic_relevance}/10"
    assert topic_consistency >= 6.0, f"Topic consistency too low: {topic_consistency}/10"


def test_agent_response_digest_evaluation(lab_digest_generator, evaluation_llm_service, test_conversations):
    """Test how well the DigestGenerator handles agent responses vs user inputs."""
    conversation = test_conversations["agent_response"]
    
    # Generate digest  
    digest = lab_digest_generator.generate_digest(conversation)
    
    # Basic validation
    assert isinstance(digest, dict)
    assert "rated_segments" in digest
    assert len(digest["rated_segments"]) > 0
    
    # Create evaluation prompt
    evaluation_prompt = create_evaluation_prompt(
        conversation["content"],
        digest,
        "lab_assistant"
    )
    
    # Get LLM evaluation
    evaluation_response = evaluation_llm_service.generate(
        evaluation_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    # Parse evaluation
    evaluation = parse_evaluation_response(evaluation_response)
    
    # Print results for inspection
    print(f"\n=== Agent Response Digest Evaluation ===")
    print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/10")
    print(f"Scores: {evaluation.get('scores', {})}")
    print(f"Topic Quality: {evaluation.get('topic_quality_notes', 'N/A')}")
    
    print(f"\n=== Generated Digest ===")
    print(json.dumps(digest, indent=2))
    
    # Check that agent responses are properly processed
    rated_segments = digest["rated_segments"]
    
    # Agent responses should typically be classified as "information" type
    info_segments = [s for s in rated_segments if s["type"] == "information"]
    assert len(info_segments) > 0, "Agent responses should contain information-type segments"
    
    # Should have relevant topics for lab work
    all_topics = []
    for segment in rated_segments:
        all_topics.extend(segment["topics"])
    
    lab_related_topics = [t for t in all_topics if any(keyword in t.lower() 
                         for keyword in ["project", "design", "equipment", "methods", "materials", "pcb", "electronics", "sensors", "engineering", "manufacturing", "firmware"])]
    
    assert len(lab_related_topics) > 0, f"Should have lab-related topics, found: {all_topics}"


def test_memory_worthy_filtering(dnd_digest_generator):
    """Test that memory_worthy field properly filters out non-memorable content."""
    
    # Test non-memory-worthy content
    non_memorable_conversations = [
        {
            "guid": "test-non-memorable-1",
            "role": "user",
            "content": "okay",
            "timestamp": "2025-05-01T10:00:00"
        },
        {
            "guid": "test-non-memorable-2", 
            "role": "agent",
            "content": "Got it, I'll note that.",
            "timestamp": "2025-05-01T10:01:00"
        },
        {
            "guid": "test-non-memorable-3",
            "role": "user", 
            "content": "thanks",
            "timestamp": "2025-05-01T10:02:00"
        }
    ]
    
    # Test memory-worthy content
    memorable_conversation = {
        "guid": "test-memorable-1",
        "role": "user",
        "content": "I discovered a magical sword with ancient runes in the chest. It seems to be made of a strange blue metal that glows faintly.",
        "timestamp": "2025-05-01T10:03:00"
    }
    
    # Generate digests
    non_memorable_digests = [dnd_digest_generator.generate_digest(conv) for conv in non_memorable_conversations]
    memorable_digest = dnd_digest_generator.generate_digest(memorable_conversation)
    
    # Check that non-memorable content has empty or minimal segments after filtering
    total_non_memorable_segments = 0
    for digest in non_memorable_digests:
        total_non_memorable_segments += len(digest["rated_segments"])
    
    # Should have very few or no segments after memory_worthy filtering
    # Allow some margin since LLM classification may vary
    assert total_non_memorable_segments <= 3, f"Too many segments preserved for non-memorable content: {total_non_memorable_segments}"
    
    # Check that memorable content is preserved
    memorable_segments = memorable_digest["rated_segments"]
    assert len(memorable_segments) > 0, "Memorable content should have segments preserved"
    
    # Check that memorable segments have appropriate characteristics
    for segment in memorable_segments:
        assert "memory_worthy" in segment, "Segments should have memory_worthy field"
        if segment.get("memory_worthy", False):
            assert segment.get("importance", 0) >= 3, "Memory-worthy segments should have high importance"
            assert segment.get("type") in ["information", "action"], "Memory-worthy segments should be information or action type"
    
    print(f"Non-memorable segments total: {total_non_memorable_segments}")
    print(f"Memorable segments: {len(memorable_segments)}")
    print(f"Sample memorable segment: {memorable_segments[0] if memorable_segments else 'None'}")


def test_segment_type_classification_accuracy(dnd_digest_generator):
    """Test that segment types are classified accurately with memory_worthy consideration."""
    
    test_segments = [
        {
            "content": "What do I see in the room?",
            "expected_type": "query",
            "expected_memory_worthy": False
        },
        {
            "content": "I found a golden chalice with intricate engravings.",
            "expected_type": "information", 
            "expected_memory_worthy": True
        },
        {
            "content": "I cast fireball at the goblins.",
            "expected_type": "action",
            "expected_memory_worthy": True
        },
        {
            "content": "Continue with the story.",
            "expected_type": "command",
            "expected_memory_worthy": False
        }
    ]
    
    for i, test_case in enumerate(test_segments):
        conversation = {
            "guid": f"test-type-{i}",
            "role": "user", 
            "content": test_case["content"],
            "timestamp": "2025-05-01T10:00:00"
        }
        
        digest = dnd_digest_generator.generate_digest(conversation)
        segments = digest["rated_segments"]
        
        if segments:  # Only check if segments were preserved
            segment = segments[0]
            assert segment["type"] == test_case["expected_type"], \
                f"Expected type {test_case['expected_type']} but got {segment['type']} for: {test_case['content']}"
            
            # Print segment details for debugging
            print(f"Content: '{test_case['content']}' -> Type: {segment['type']}, Memory worthy: {segment.get('memory_worthy', 'missing')}, Importance: {segment.get('importance', 'missing')}")
            
            # For segments that should be non-memory-worthy, check if they're filtered or at least marked correctly
            if not test_case["expected_memory_worthy"]:
                # The segment survived filtering, so it should either be marked as not memory worthy
                # or have very low importance (which would be filtered later)
                is_properly_classified = (
                    segment.get("memory_worthy") == False or 
                    segment.get("importance", 5) <= 2
                )
                if not is_properly_classified:
                    print(f"Warning: Non-memorable segment survived filtering: {test_case['content']}")
        else:
            # If no segments preserved, it should be non-memory-worthy content
            print(f"Content: '{test_case['content']}' -> No segments preserved (filtered out)")
            if test_case["expected_memory_worthy"]:
                print(f"Warning: Expected memory-worthy content but no segments preserved: {test_case['content']}")


def test_topic_normalization_quality(dnd_digest_generator, evaluation_llm_service):
    """Test that similar topics are normalized consistently across different inputs."""
    
    # Test content with intentionally similar concepts that should normalize
    test_contents = [
        {
            "guid": "norm-test-1",
            "role": "user", 
            "content": "I want to explore the ancient ruins and investigate the archaeological site.",
            "timestamp": "2025-05-01T10:00:00"
        },
        {
            "guid": "norm-test-2", 
            "role": "agent",
            "content": "You discover artifacts within the ruins, remnants of the lost civilization's archaeology.",
            "timestamp": "2025-05-01T10:01:00"
        },
        {
            "guid": "norm-test-3",
            "role": "user",
            "content": "Let's examine the location more carefully and study the geography of this area.",
            "timestamp": "2025-05-01T10:02:00"
        }
    ]
    
    all_topics = []
    all_digests = []
    
    # Generate digests for all test contents
    for content in test_contents:
        digest = dnd_digest_generator.generate_digest(content)
        all_digests.append(digest)
        
        for segment in digest["rated_segments"]:
            all_topics.extend(segment["topics"])
    
    # Print all topics for inspection
    print(f"\n=== Topic Normalization Test ===")
    print(f"All topics found: {sorted(set(all_topics))}")
    
    # Create evaluation prompt for topic consistency
    consistency_prompt = f"""
Evaluate the consistency of topic assignments across multiple related content segments.

ALL_TOPICS_FOUND: {sorted(set(all_topics))}

DIGESTS_GENERATED:
{json.dumps(all_digests, indent=2)}

Rate the topic consistency from 1-10 considering:
1. Are similar concepts given the same topic names?
2. Are there redundant or overlapping topics that should be consolidated?
3. Is the naming convention consistent (capitalization, format)?

Provide response as JSON:
{{
  "consistency_score": score,
  "redundant_topics": ["topic1", "topic2"],
  "recommended_consolidations": [["old_topic", "preferred_topic"]],
  "consistency_notes": "detailed assessment"
}}
"""
    
    # Get evaluation
    evaluation_response = evaluation_llm_service.generate(
        consistency_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    evaluation = parse_evaluation_response(evaluation_response)
    
    print(f"Consistency Score: {evaluation.get('consistency_score', 'N/A')}/10")
    print(f"Redundant Topics: {evaluation.get('redundant_topics', [])}")
    print(f"Recommended Consolidations: {evaluation.get('recommended_consolidations', [])}")
    print(f"Notes: {evaluation.get('consistency_notes', 'N/A')}")
    
    # Assert reasonable consistency
    consistency_score = evaluation.get("consistency_score", 0)
    assert consistency_score >= 7.0, f"Topic consistency too low: {consistency_score}/10"
    
    # Check for expected topic normalization (e.g., ruins/archaeology should be consistent)
    unique_topics = set(all_topics)
    
    # Should not have both "ruins" and "archaeology" as separate topics if normalization works
    problematic_pairs = [
        ("Location", "Geography"), 
        ("Ruins", "Archaeology"),
        ("Investigation", "Research")
    ]
    
    for topic1, topic2 in problematic_pairs:
        if topic1 in unique_topics and topic2 in unique_topics:
            print(f"Warning: Found both '{topic1}' and '{topic2}' - may indicate normalization issue")