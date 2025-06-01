"""LLM-evaluated tests for memory compression redundancy reduction effectiveness."""

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
from src.memory.memory_manager import MemoryManager
from examples.domain_configs import DND_CONFIG


@pytest.fixture(scope="module")
def llm_service():
    """Create an LLM service instance for testing."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "memory_redundancy_eval"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "memory_redundancy.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "test_memory_redundancy_reduction",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def evaluation_llm_service():
    """Create a separate LLM service for evaluation."""
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    guid = "memory_redundancy_eval"
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    debug_file = os.path.join(guid_logs_dir, "evaluation_llm.log")
    
    service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.1,
        "stream": False,
        "debug": True,
        "debug_file": debug_file,
        "debug_scope": "redundancy_evaluation_llm",
        "console_output": False
    })
    return service


@pytest.fixture(scope="module")
def memory_manager(llm_service):
    """Create a MemoryManager instance for testing."""
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    
    manager = MemoryManager(
        memory_guid="redundancy_test",
        memory_file=temp_file.name,
        domain_config=DND_CONFIG,
        llm_service=llm_service,
        digest_llm_service=llm_service,
        max_recent_conversation_entries=4,  # Force compression quickly
        importance_threshold=3,
        logger=None
    )
    
    # Initialize with basic data
    manager.create_initial_memory(DND_CONFIG["initial_data"])
    
    yield manager
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture(scope="module")
def redundant_conversation_data():
    """Create test conversation data with deliberate redundancy for testing."""
    return [
        {
            "role": "user",
            "content": "Tell me about Mayor Elena and what quests she might have"
        },
        {
            "role": "agent", 
            "content": "Mayor Elena is the Mayor of Haven, the central settlement in The Lost Valley. She's currently focused on protecting the valley's inhabitants and coordinating efforts to address the disrupted trade routes. She's likely to offer quests related to protecting merchants and investigating the strange occurrences affecting the trade between settlements."
        },
        {
            "role": "user",
            "content": "What kind of quest does Elena have for me?"
        },
        {
            "role": "agent",
            "content": "Mayor Elena, being the Mayor of Haven and responsible for protecting the inhabitants, would offer you a quest to help protect the merchants traveling the disrupted trade routes. She's coordinating the defense efforts and needs adventurers to investigate the strange occurrences and provide protection for the trade caravans."
        },
        {
            "role": "user", 
            "content": "I want to accept Elena's quest to protect the trade routes"
        },
        {
            "role": "agent",
            "content": "Excellent! Mayor Elena welcomes your assistance. She explains that the trade routes between Haven, Riverwatch, and Mountainkeep have been disrupted by unusual activity. Merchants are seeking protection, and there have been strange occurrences along the roads. Your quest is to investigate these disruptions and ensure safe passage for the trade caravans. The reward is generous - 500 gold pieces upon successful completion."
        },
        {
            "role": "user",
            "content": "Tell me more about this trade route protection quest"
        },
        {
            "role": "agent", 
            "content": "The trade route protection quest from Mayor Elena involves safeguarding the merchants who travel between the three settlements - Haven, Riverwatch, and Mountainkeep. The main road has been disrupted, and merchants are encountering strange occurrences and increased danger. Elena is coordinating protective efforts and needs you to patrol the routes, investigate the source of the disruptions, and ensure the merchants can travel safely. The quest offers 500 gold as compensation."
        }
    ]


def create_redundancy_evaluation_prompt(static_memory: str, context_before: list, context_after: list) -> str:
    """Create a prompt for LLM evaluation of redundancy reduction effectiveness."""
    return f"""
You are an expert evaluator assessing the effectiveness of a memory compression system designed to reduce redundancy while preserving important information.

STATIC_MEMORY (Foundation Knowledge):
{static_memory}

MEMORY_CONTEXT_BEFORE_IMPROVEMENTS:
{json.dumps(context_before, indent=2)}

MEMORY_CONTEXT_AFTER_IMPROVEMENTS:
{json.dumps(context_after, indent=2)}

Please evaluate the memory compression improvements on the following criteria and provide a score from 1-10 for each:

1. REDUNDANCY_REDUCTION: How effectively were redundant statements eliminated?
   - Are similar facts stated multiple times in BEFORE but consolidated in AFTER?
   - Does AFTER avoid repeating information already in STATIC_MEMORY?

2. INFORMATION_PRESERVATION: How well was important information preserved?
   - Are key facts, decisions, and developments still captured in AFTER?
   - Is essential quest and character information maintained?

3. CONSOLIDATION_QUALITY: How well were similar concepts merged?
   - Are related pieces of information effectively combined?
   - Do the consolidated statements capture the essence of multiple inputs?

4. CLARITY_IMPROVEMENT: Is the AFTER version clearer and more organized?
   - Are the statements more concise and focused?
   - Is the information easier to understand and use?

5. CONTEXT_EFFICIENCY: How much more efficient is the AFTER version?
   - Does AFTER contain fewer context entries while preserving value?
   - Is the information density higher in AFTER?

6. ACTIONABLE_CONTENT: How well does AFTER focus on actionable information?
   - Does AFTER prioritize decisions, actions, and new developments?
   - Are vague restatements of known facts eliminated?

Provide your response as JSON:
{{
  "scores": {{
    "redundancy_reduction": score,
    "information_preservation": score,
    "consolidation_quality": score,
    "clarity_improvement": score,
    "context_efficiency": score,
    "actionable_content": score
  }},
  "overall_score": average_score,
  "redundancy_examples": ["example of redundancy eliminated"],
  "preserved_information": ["example of important info preserved"],
  "improvement_highlights": ["key improvement observed"],
  "remaining_issues": ["any remaining problems"],
  "effectiveness_summary": "Overall assessment of the redundancy reduction effectiveness"
}}
"""


def parse_evaluation_response(response: str) -> dict:
    """Parse the LLM evaluation response, handling potential formatting issues."""
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
        "scores": {"error": "Failed to parse evaluation"},
        "overall_score": 0,
        "redundancy_examples": ["Evaluation parsing failed"],
        "preserved_information": ["Could not parse evaluation"],
        "improvement_highlights": ["Evaluation unavailable"],
        "remaining_issues": ["Fix evaluation response parsing"],
        "effectiveness_summary": "Evaluation unavailable due to parsing error"
    }


def test_memory_redundancy_reduction_effectiveness(memory_manager, evaluation_llm_service, redundant_conversation_data):
    """Test the effectiveness of memory compression redundancy reduction using LLM evaluation."""
    
    # Capture initial state
    initial_memory = memory_manager.get_memory()
    static_memory = initial_memory.get("static_memory", "")
    initial_context = initial_memory.get("context", [])
    
    print(f"\n=== Initial State ===")
    print(f"Static memory length: {len(static_memory)} chars")
    print(f"Initial context entries: {len(initial_context)}")
    
    # Add the redundant conversation data to trigger compression
    for i, entry in enumerate(redundant_conversation_data):
        response = memory_manager.add_conversation_entry({
            "role": entry["role"],
            "content": entry["content"]
        })
        print(f"Added entry {i+1}: {entry['role']} - {entry['content'][:50]}...")
    
    # Get the final memory state
    final_memory = memory_manager.get_memory()
    final_context = final_memory.get("context", [])
    
    print(f"\n=== Final State ===")
    print(f"Final context entries: {len(final_context)}")
    print(f"Context entries added: {len(final_context) - len(initial_context)}")
    
    # Print the final context for inspection
    print(f"\n=== Final Context Entries ===")
    for i, entry in enumerate(final_context):
        print(f"{i+1}. {entry.get('text', '')[:100]}...")
        print(f"   GUIDs: {entry.get('guids', [])}")
    
    # Create evaluation prompt
    evaluation_prompt = create_redundancy_evaluation_prompt(
        static_memory,
        initial_context,
        final_context
    )
    
    # Get LLM evaluation
    evaluation_response = evaluation_llm_service.generate(
        evaluation_prompt,
        options={"temperature": 0.1, "stream": False}
    )
    
    # Parse evaluation
    evaluation = parse_evaluation_response(evaluation_response)
    
    # Print detailed results
    print(f"\n=== Redundancy Reduction Evaluation ===")
    print(f"Overall Score: {evaluation.get('overall_score', 'N/A')}/10")
    print(f"\nDetailed Scores:")
    scores = evaluation.get('scores', {})
    for criterion, score in scores.items():
        print(f"  {criterion.replace('_', ' ').title()}: {score}/10")
    
    print(f"\nRedundancy Examples Eliminated:")
    for example in evaluation.get('redundancy_examples', []):
        print(f"  - {example}")
    
    print(f"\nImportant Information Preserved:")
    for info in evaluation.get('preserved_information', []):
        print(f"  - {info}")
    
    print(f"\nImprovement Highlights:")
    for highlight in evaluation.get('improvement_highlights', []):
        print(f"  - {highlight}")
    
    print(f"\nRemaining Issues:")
    for issue in evaluation.get('remaining_issues', []):
        print(f"  - {issue}")
    
    print(f"\nEffectiveness Summary:")
    print(f"  {evaluation.get('effectiveness_summary', 'N/A')}")
    
    # Assert quality thresholds
    overall_score = evaluation.get("overall_score", 0)
    assert overall_score >= 7.0, f"Redundancy reduction effectiveness too low: {overall_score}/10"
    
    # Check specific criteria
    redundancy_reduction = scores.get("redundancy_reduction", 0)
    information_preservation = scores.get("information_preservation", 0)
    context_efficiency = scores.get("context_efficiency", 0)
    
    assert redundancy_reduction >= 7.0, f"Redundancy reduction score too low: {redundancy_reduction}/10"
    assert information_preservation >= 7.0, f"Information preservation score too low: {information_preservation}/10"
    assert context_efficiency >= 6.0, f"Context efficiency score too low: {context_efficiency}/10"
    
    # Additional quantitative checks
    context_growth_ratio = len(final_context) / max(len(initial_context), 1)
    print(f"\nQuantitative Metrics:")
    print(f"  Context growth ratio: {context_growth_ratio:.2f}")
    print(f"  Conversations processed: {len(redundant_conversation_data)}")
    print(f"  Context entries per conversation: {(len(final_context) - len(initial_context)) / len(redundant_conversation_data):.2f}")
    
    # The context should not grow linearly with conversation entries due to redundancy reduction
    assert context_growth_ratio < 2.0, f"Context grew too much despite redundancy reduction: {context_growth_ratio:.2f}x"


def test_no_new_information_detection(memory_manager, evaluation_llm_service):
    """Test that the system correctly detects when no new information is present."""
    
    # Get initial state
    initial_memory = memory_manager.get_memory()
    initial_context_count = len(initial_memory.get("context", []))
    
    # Add conversations that just restate existing information
    restating_conversations = [
        {
            "role": "user",
            "content": "Tell me about The Lost Valley"
        },
        {
            "role": "agent",
            "content": "The Lost Valley is a hidden valley surrounded by impassable mountains. It contains ancient ruins and mysterious magical anomalies. There are three main settlements: Haven in the center, Riverwatch to the east, and Mountainkeep to the west."
        },
        {
            "role": "user", 
            "content": "What settlements are in the valley?"
        },
        {
            "role": "agent",
            "content": "The Lost Valley has three main settlements: Haven, which is centrally located, Riverwatch in the eastern part, and Mountainkeep to the west."
        }
    ]
    
    # Process these conversations
    for entry in restating_conversations:
        memory_manager.add_conversation_entry({
            "role": entry["role"],
            "content": entry["content"]
        })
    
    # Get final state
    final_memory = memory_manager.get_memory()
    final_context_count = len(final_memory.get("context", []))
    
    # Check that no new context entries were created (or very few)
    new_entries = final_context_count - initial_context_count
    print(f"\n=== No New Information Test ===")
    print(f"Initial context entries: {initial_context_count}")
    print(f"Final context entries: {final_context_count}")
    print(f"New context entries created: {new_entries}")
    
    # Should create very few or no new context entries since information is redundant
    assert new_entries <= 1, f"Too many context entries created for redundant information: {new_entries}"


def test_context_consolidation_effectiveness(memory_manager, evaluation_llm_service):
    """Test that similar context entries are effectively consolidated."""
    
    # Create multiple similar conversation turns about the same topic
    similar_conversations = [
        {
            "role": "user",
            "content": "I want to explore the ancient ruins"
        },
        {
            "role": "agent",
            "content": "The ancient ruins in The Lost Valley are scattered throughout the area. Recent discoveries include new chambers with strange energy emanations and valuable artifacts."
        },
        {
            "role": "user",
            "content": "What can I find in the ruins?"
        },
        {
            "role": "agent", 
            "content": "In the ancient ruins, explorers have discovered new chambers containing strange energy emanations and valuable artifacts. The ruins may be connected to the magical anomalies affecting the valley."
        },
        {
            "role": "user",
            "content": "Are the ruins worth exploring?"
        },
        {
            "role": "agent",
            "content": "Yes, the ancient ruins are definitely worth exploring. They contain valuable artifacts and new chambers with strange energy. The ruins might also help explain the magical anomalies in the valley."
        }
    ]
    
    # Get initial context count
    initial_memory = memory_manager.get_memory()
    initial_context_count = len(initial_memory.get("context", []))
    
    # Process conversations
    for entry in similar_conversations:
        memory_manager.add_conversation_entry({
            "role": entry["role"],
            "content": entry["content"]
        })
    
    # Get final state
    final_memory = memory_manager.get_memory()
    final_context = final_memory.get("context", [])
    final_context_count = len(final_context)
    
    print(f"\n=== Context Consolidation Test ===")
    print(f"Conversations about ruins: {len(similar_conversations)}")
    print(f"Initial context entries: {initial_context_count}")
    print(f"Final context entries: {final_context_count}")
    print(f"New context entries: {final_context_count - initial_context_count}")
    
    # Print the new context entries to inspect consolidation
    print(f"\nNew context entries (last {final_context_count - initial_context_count}):")
    for i, entry in enumerate(final_context[initial_context_count:]):
        print(f"{i+1}. {entry.get('text', '')[:150]}...")
        print(f"   GUIDs: {len(entry.get('guids', []))} conversation GUIDs")
    
    # Should create fewer context entries than conversation pairs due to consolidation
    conversation_pairs = len(similar_conversations) // 2
    new_entries = final_context_count - initial_context_count
    
    assert new_entries < conversation_pairs, f"Expected consolidation but got {new_entries} entries for {conversation_pairs} conversation pairs"
    
    # Check that some context entries have multiple GUIDs (indicating consolidation)
    consolidated_entries = [entry for entry in final_context[initial_context_count:] 
                          if len(entry.get('guids', [])) > 2]
    
    print(f"Context entries with multiple GUIDs (consolidated): {len(consolidated_entries)}")
    
    # Note: This may fail if redundancy detection is working too well
    # In which case, we should verify that genuinely new information still gets stored
    if len(consolidated_entries) == 0:
        print("Warning: No consolidation occurred - redundancy detection may be too aggressive")


def test_genuinely_new_information_storage(memory_manager, evaluation_llm_service):
    """Test that genuinely new information not in static memory gets properly stored."""
    
    # Get initial state
    initial_memory = memory_manager.get_memory()
    initial_context_count = len(initial_memory.get("context", []))
    static_memory = initial_memory.get("static_memory", "")
    
    print(f"\n=== New Information Storage Test ===")
    print(f"Initial context entries: {initial_context_count}")
    
    # Create conversations with CLEARLY NEW information not mentioned in static memory
    new_discoveries = [
        {
            "role": "user",
            "content": "I discovered a hidden chamber beneath the town fountain with glowing crystals"
        },
        {
            "role": "agent", 
            "content": "You found a secret chamber beneath Haven's central fountain. The chamber contains glowing blue crystals that pulse with magical energy, and there are ancient inscriptions on the walls written in an unknown language. This discovery is completely new - no one in the valley has ever reported finding anything like this before."
        },
        {
            "role": "user",
            "content": "What do the crystal inscriptions reveal?"
        },
        {
            "role": "agent", 
            "content": "The crystal chamber inscriptions reveal warnings about 'The Void Keeper' - an ancient entity sleeping beneath the valley. The glowing crystals are binding seals preventing its awakening. This is crucial new information that explains the source of the magical anomalies."
        }
    ]
    
    # Add conversations with major plot developments
    plot_developments = [
        {
            "role": "user",
            "content": "I accepted a new quest from the blacksmith to forge a magical weapon"
        },
        {
            "role": "agent",
            "content": "The blacksmith Jonas has given you a quest to forge the Sunblade, a legendary weapon capable of piercing the Void Keeper's defenses. He provides you with rare star-metal and instructs you to use the crystal chamber's energy to empower the forging process."
        },
        {
            "role": "user", 
            "content": "I completed the Sunblade forging and it's now glowing with power"
        },
        {
            "role": "agent",
            "content": "You have successfully forged the Sunblade using the crystal chamber's energy! The weapon now glows with brilliant light and pulses with power capable of harming entities from the void. This is a major achievement that changes the balance of power in the valley."
        }
    ]
    
    all_new_conversations = new_discoveries + plot_developments
    
    # Process these genuinely new conversations
    for i, entry in enumerate(all_new_conversations):
        response = memory_manager.add_conversation_entry({
            "role": entry["role"],
            "content": entry["content"]
        })
        print(f"Added NEW info {i+1}: {entry['role']} - {entry['content'][:60]}...")
    
    # Get final state
    final_memory = memory_manager.get_memory()
    final_context = final_memory.get("context", [])
    final_context_count = len(final_context)
    
    print(f"\nFinal context entries: {final_context_count}")
    print(f"New context entries created: {final_context_count - initial_context_count}")
    
    # Print any new context entries
    if final_context_count > initial_context_count:
        print(f"\nNew context entries:")
        for i, entry in enumerate(final_context[initial_context_count:]):
            print(f"{i+1}. {entry.get('text', '')[:150]}...")
            print(f"   GUIDs: {len(entry.get('guids', []))} conversation entries")
    else:
        print("\nWARNING: No new context entries were created!")
        print("This suggests redundancy detection may be too aggressive.")
        
        # Create evaluation prompt for assessing if the system is too aggressive
        evaluation_prompt = f"""
You are evaluating whether a memory system's redundancy detection is too aggressive.

STATIC_MEMORY:
{static_memory}

NEW_CONVERSATIONS_PROCESSED:
{json.dumps(all_new_conversations, indent=2)}

RESULT: 0 context entries were created from these conversations.

Please evaluate whether this is appropriate:

1. Do the conversations contain genuinely NEW information not in static memory?
2. Should some of this information have been stored as context?
3. Is the redundancy detection working correctly or being too aggressive?

Provide response as JSON:
{{
  "contains_new_info": true/false,
  "should_store_context": true/false,
  "redundancy_too_aggressive": true/false,
  "key_new_information": ["list of new info that should be stored"],
  "assessment": "detailed assessment"
}}
"""
        
        # Get LLM evaluation of whether we're being too aggressive
        evaluation_response = evaluation_llm_service.generate(
            evaluation_prompt,
            options={"temperature": 0.1, "stream": False}
        )
        
        evaluation = parse_evaluation_response(evaluation_response)
        
        print(f"\nLLM Assessment of Redundancy Detection:")
        print(f"Contains new info: {evaluation.get('contains_new_info', 'N/A')}")
        print(f"Should store context: {evaluation.get('should_store_context', 'N/A')}")
        print(f"Redundancy too aggressive: {evaluation.get('redundancy_too_aggressive', 'N/A')}")
        print(f"Key new information: {evaluation.get('key_new_information', [])}")
        print(f"Assessment: {evaluation.get('assessment', 'N/A')}")
        
        # If LLM says we should have stored context but didn't, that's a problem
        if evaluation.get('should_store_context', False) and evaluation.get('redundancy_too_aggressive', False):
            print("\n❌ ISSUE DETECTED: Redundancy detection appears too aggressive")
            print("The system should store genuinely new information but is not doing so.")
        else:
            print("\n✅ Redundancy detection working appropriately")
    
    # Assert that we should create at least some context for genuinely new information
    # This is a reasonable expectation - if we have major plot developments like discovering
    # hidden chambers and forging legendary weapons, some context should be created
    assert final_context_count > initial_context_count, \
        f"Expected some context creation for genuinely new information, but got {final_context_count - initial_context_count} new entries"


def test_balanced_redundancy_filtering(memory_manager, evaluation_llm_service):
    """Test that the system correctly distinguishes between redundant and new information."""
    
    initial_memory = memory_manager.get_memory()
    initial_context_count = len(initial_memory.get("context", []))
    
    print(f"\n=== Balanced Redundancy Filtering Test ===")
    print(f"Initial context entries: {initial_context_count}")
    
    # Mix of redundant and new information
    mixed_conversations = [
        # REDUNDANT: Restating known information
        {
            "role": "user",
            "content": "Tell me about the settlements in The Lost Valley"
        },
        {
            "role": "agent",
            "content": "The Lost Valley has three main settlements: Haven in the center, Riverwatch to the east, and Mountainkeep to the west. This is the basic layout of the valley."
        },
        # NEW: Specific character interaction
        {
            "role": "user", 
            "content": "I spoke with Captain Sara and she promoted me to Lieutenant"
        },
        {
            "role": "agent",
            "content": "Captain Sara has promoted you to Lieutenant of the Riverwatch Guard! This new rank gives you authority over patrols and access to the guard armory. Sara trusts you with defending the eastern approaches to the valley."
        },
        # REDUNDANT: Known quest information
        {
            "role": "user",
            "content": "What's the trade route situation?"
        },
        {
            "role": "agent", 
            "content": "The main trade routes between settlements are disrupted, merchants need protection, and alternative routes are being sought. This has been an ongoing concern."
        },
        # NEW: Specific quest completion
        {
            "role": "user",
            "content": "I successfully cleared the goblin camp threatening the western route"
        },
        {
            "role": "agent",
            "content": "Excellent work! You have cleared the goblin camp that was threatening the western trade route to Mountainkeep. The merchants can now travel safely, and Mayor Elena has authorized a reward of 200 gold pieces for your success."
        }
    ]
    
    # Process mixed conversations
    for i, entry in enumerate(mixed_conversations):
        memory_manager.add_conversation_entry({
            "role": entry["role"], 
            "content": entry["content"]
        })
        print(f"Added mixed {i+1}: {entry['role']} - {entry['content'][:50]}...")
    
    # Check results
    final_memory = memory_manager.get_memory()
    final_context = final_memory.get("context", [])
    final_context_count = len(final_context)
    
    new_entries = final_context_count - initial_context_count
    
    print(f"\nResults:")
    print(f"Total conversations: {len(mixed_conversations)}")
    print(f"New context entries: {new_entries}")
    print(f"Expected: Should create context for promotions and quest completions")
    print(f"Expected: Should NOT create context for restating known settlements/trade info")
    
    if new_entries > 0:
        print(f"\nCreated context entries:")
        for i, entry in enumerate(final_context[initial_context_count:]):
            print(f"{i+1}. {entry.get('text', '')[:120]}...")
    
    # We should have some context creation (for promotions and quest completions)
    # but less than the total number of conversation pairs
    conversation_pairs = len(mixed_conversations) // 2
    
    assert new_entries > 0, "Should create some context for new information (promotions, quest completions)"
    assert new_entries < conversation_pairs, f"Should filter out redundant info, but got {new_entries} entries for {conversation_pairs} pairs"
    
    print(f"\n✅ Balanced filtering working: {new_entries}/{conversation_pairs} conversation pairs created context")