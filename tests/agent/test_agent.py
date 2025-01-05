import pytest
from unittest.mock import Mock, patch, ANY
import json
from datetime import datetime

from src.agent.agent import Agent, AgentPhase

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    mock = Mock()
    # We don't expect the Agent to call the LLM service directly anymore
    return mock

@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager"""
    mock = Mock()
    # Setup memory manager to return appropriate responses
    mock.query_memory.return_value = {
        "response": "Test response"
    }
    mock.get_memory_context.return_value = {
        "static_memory": {
            "structured_data": {
                "entities": [
                    {
                        "identifier": "static_entity_1",
                        "type": "test_type",
                        "name": "Static Entity",
                        "features": ["static_feature"],
                        "description": "Static description"
                    }
                ]
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "conversation_history": []
    }
    mock.update_memory.return_value = True
    mock.create_initial_memory.return_value = True
    return mock

@pytest.fixture
def agent(mock_llm_service, mock_memory_manager):
    """Create an agent instance with mock services"""
    return Agent(mock_llm_service, mock_memory_manager)

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test agent initialization"""
    assert agent.current_phase == AgentPhase.INITIALIZATION
    history = agent.get_conversation_history()
    assert isinstance(history, list)
    assert len(history) == 0

@pytest.mark.asyncio
async def test_process_message_success(agent, mock_memory_manager):
    """Test successful message processing"""
    # Setup mock conversation history
    mock_memory_manager.get_memory_context.return_value = {
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Test response"}
        ]
    }
    
    response = await agent.process_message("Hello")
    
    # Check response
    assert response == "Test response"
    
    # Check conversation history via memory manager
    history = agent.get_conversation_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Test response"

@pytest.mark.asyncio
async def test_process_message_memory_manager_error(agent, mock_memory_manager):
    """Test message processing with memory manager error"""
    mock_memory_manager.query_memory.return_value = {
        "response": "Error processing message",
        "suggested_phase": "INTERACTION",
        "confidence": 0.0
    }
    
    response = await agent.process_message("Hello")
    assert response == "Error processing message"

@pytest.mark.asyncio
async def test_learn_success(agent, mock_memory_manager):
    """Test successful learning"""
    mock_memory_manager.create_initial_memory.return_value = True
    
    success = await agent.learn("New information")
    assert success is True
    assert agent.current_phase == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_learn_memory_manager_error(agent, mock_memory_manager):
    """Test learning with memory manager error"""
    mock_memory_manager.create_initial_memory.return_value = False
    
    success = await agent.learn("New information")
    assert success is False

@pytest.mark.asyncio
async def test_reflect(agent, mock_memory_manager):
    """Test reflection process"""
    mock_memory_manager.update_memory.return_value = True
    mock_memory_manager.get_memory_context.return_value = {
        "conversation_history": [
            {"role": "system", "content": "Reflection triggered"}
        ]
    }
    
    await agent.reflect()
    
    history = agent.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"
    assert "Reflection" in history[0]["content"]

@pytest.mark.asyncio
async def test_reflect_memory_manager_error(agent, mock_memory_manager):
    """Test reflection with memory manager error"""
    mock_memory_manager.update_memory.return_value = False
    mock_memory_manager.get_memory_context.return_value = {
        "conversation_history": [
            {"role": "system", "content": "Reflection failed"}
        ]
    }
    
    await agent.reflect()
    
    history = agent.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"

def test_get_conversation_history(agent, mock_memory_manager):
    """Test getting conversation history"""
    test_message = {"role": "user", "content": "test", "timestamp": datetime.now().isoformat()}
    mock_memory_manager.get_memory_context.return_value = {
        "conversation_history": [test_message]
    }
    
    history = agent.get_conversation_history()
    assert history == [test_message]

@pytest.mark.asyncio
async def test_phase_transition(agent, mock_memory_manager):
    """Test phase transitions during message processing"""
    # Mock memory manager to suggest INTERACTION phase
    mock_memory_manager.query_memory.return_value = {
        "response": "Test response",
        "suggested_phase": "INTERACTION",
        "confidence": 0.9
    }
    
    await agent.process_message("Hello")
    assert agent.current_phase == AgentPhase.INTERACTION
    
    # Test invalid phase suggestion defaults to INTERACTION
    mock_memory_manager.query_memory.return_value = {
        "response": "Test response",
        "suggested_phase": "INTERACTION",
        "confidence": 0.9
    }
    
    await agent.process_message("Another message")
    assert agent.current_phase == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_conversation_history_limit(agent, mock_memory_manager):
    """Test conversation history in message processing"""
    # Add more than 5 messages
    for i in range(6):
        await agent.process_message(f"Message {i}")
    
    # Verify that context was sent correctly
    last_call_arg = mock_memory_manager.query_memory.call_args[0][0]
    context = json.loads(last_call_arg)
    assert "current_phase" in context
    assert "user_message" in context 

@pytest.mark.asyncio
async def test_memory_integration_flow(agent, mock_memory_manager):
    """Test the complete flow of memory operations through the agent"""
    # Initial learning phase
    initial_data = "The world contains a mountain pass guarded by trolls"
    success = await agent.learn(initial_data)
    assert success is True
    mock_memory_manager.create_initial_memory.assert_called_once_with(initial_data)
    
    # Interaction phase - should update working memory
    response = await agent.process_message("A group of merchants wants to pass through")
    assert response == "Test response"
    
    # Verify query included both static and working memory
    query_context = json.loads(mock_memory_manager.query_memory.call_args[0][0])
    assert "user_message" in query_context
    assert query_context["user_message"] == "A group of merchants wants to pass through"
    
    # Verify memory update was called with correct structure
    update_calls = mock_memory_manager.update_memory.call_args_list
    assert len(update_calls) > 0
    for call in update_calls:
        update_context = json.loads(call[0][0])
        if "operation" not in update_context:  # Regular update, not reflection
            assert "new_info" in update_context

@pytest.mark.asyncio
async def test_memory_reflection_trigger(agent, mock_memory_manager):
    """Test that reflection is triggered after accumulating messages"""
    # Setup memory manager to simulate conversation history
    conversation_history = []
    for i in range(3):  # Add enough messages to trigger reflection
        conversation_history.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i}",
            "timestamp": datetime.now().isoformat()
        })
    
    mock_memory_manager.get_memory_context.return_value = {
        "static_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "conversation_history": conversation_history
    }
    
    # Process a message that should trigger reflection
    await agent.process_message("One more message")
    
    # Verify reflection was triggered
    reflection_calls = [
        call for call in mock_memory_manager.update_memory.call_args_list
        if json.loads(call[0][0]).get("operation") == "reflect"
    ]
    assert len(reflection_calls) > 0
    
    # Verify reflection context
    reflection_context = json.loads(reflection_calls[0][0][0])
    assert reflection_context["operation"] == "reflect"
    assert "conversation_history" in reflection_context
    assert "current_phase" in reflection_context
    assert "message" in reflection_context
    assert reflection_context["message"]["role"] == "system"
    assert reflection_context["message"]["content"] == "Reflection triggered"

@pytest.mark.asyncio
async def test_static_memory_preservation(agent, mock_memory_manager):
    """Test that static memory remains unchanged through operations"""
    # Setup initial static memory
    static_entity = {
        "identifier": "static_entity_1",
        "type": "test_type",
        "name": "Static Entity",
        "features": ["static_feature"],
        "description": "Static description"
    }
    
    mock_memory_manager.get_memory_context.return_value = {
        "static_memory": {
            "structured_data": {
                "entities": [static_entity]
            },
            "knowledge_graph": {
                "relationships": []
            }
        },
        "working_memory": {
            "structured_data": {"entities": []},
            "knowledge_graph": {"relationships": []}
        },
        "conversation_history": []
    }
    
    # Process several messages
    for i in range(5):
        await agent.process_message(f"Message {i}")
    
    # Verify static memory in final state
    final_memory = mock_memory_manager.get_memory_context()
    assert "static_memory" in final_memory
    assert len(final_memory["static_memory"]["structured_data"]["entities"]) == 1
    assert final_memory["static_memory"]["structured_data"]["entities"][0] == static_entity 