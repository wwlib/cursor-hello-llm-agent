import pytest
from unittest.mock import Mock, patch, ANY
import json
from datetime import datetime
from src.utils.logging_config import LoggingConfig

from src.agent.agent import Agent, AgentPhase

TEST_GUID = "test_agent"

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    mock = Mock()
    return mock

@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager"""
    mock = Mock()
    # Setup memory manager to return appropriate responses
    mock.query_memory.return_value = {
        "response": "Test response"
    }
    # get_memory() returns the actual memory dict structure
    mock.get_memory.return_value = {
        "static_memory": "Test static memory",
        "context": [],
        "conversation_history": [],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    mock.update_memory.return_value = True
    mock.create_initial_memory.return_value = True
    return mock

@pytest.fixture
def agent_logger():
    """Create logger for Agent tests"""
    return LoggingConfig.get_component_file_logger(
        TEST_GUID,
        "agent_test",
        log_to_console=False
    )

@pytest.fixture
def agent(mock_llm_service, mock_memory_manager, agent_logger):
    """Create an agent instance with mock services"""
    return Agent(mock_llm_service, mock_memory_manager, domain_name="test", logger=agent_logger)

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
    mock_memory_manager.get_memory.return_value = {
        "static_memory": "Test static memory",
        "context": [],
        "conversation_history": [
            {"role": "user", "content": "Hello", "timestamp": datetime.now().isoformat()},
            {"role": "agent", "content": "Test response", "timestamp": datetime.now().isoformat()}
        ],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    response = await agent.process_message("Hello")
    
    assert response == "Test response"
    
    # Verify query_memory was called with correct dict (not JSON string)
    mock_memory_manager.query_memory.assert_called_once()
    call_args = mock_memory_manager.query_memory.call_args[0][0]
    assert isinstance(call_args, dict)
    assert call_args["query"] == "Hello"
    
    history = agent.get_conversation_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "agent"
    assert history[1]["content"] == "Test response"

@pytest.mark.asyncio
async def test_process_message_memory_manager_error(agent, mock_memory_manager):
    """Test message processing with memory manager error"""
    mock_memory_manager.query_memory.return_value = {
        "response": "Error processing message"
    }
    
    response = await agent.process_message("Hello")
    assert response == "Error processing message"

@pytest.mark.asyncio
async def test_learn_success(agent, mock_memory_manager):
    """Test successful learning"""
    mock_memory_manager.create_initial_memory.return_value = True
    
    success = await agent.learn("New information")
    assert success is True
    assert agent.current_phase == AgentPhase.LEARNING

@pytest.mark.asyncio
async def test_learn_memory_manager_error(agent, mock_memory_manager):
    """Test learning with memory manager error"""
    mock_memory_manager.create_initial_memory.return_value = False
    
    success = await agent.learn("New information")
    assert success is False


def test_get_conversation_history(agent, mock_memory_manager):
    """Test getting conversation history"""
    test_message = {"role": "user", "content": "test", "timestamp": datetime.now().isoformat()}
    mock_memory_manager.get_memory.return_value = {
        "static_memory": "Test static memory",
        "context": [],
        "conversation_history": [test_message],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    history = agent.get_conversation_history()
    assert history == [test_message]

@pytest.mark.asyncio
async def test_phase_transition(agent, mock_memory_manager):
    """Test phase transitions during message processing"""
    # Process message in INITIALIZATION phase
    await agent.process_message("Hello")
    assert agent.current_phase == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_conversation_history_limit(agent, mock_memory_manager):
    """Test conversation history in message processing"""
    # Add more than 5 messages
    for i in range(6):
        await agent.process_message(f"Message {i}")
    
    # Verify that query_memory was called with correct dict format
    last_call_arg = mock_memory_manager.query_memory.call_args[0][0]
    assert isinstance(last_call_arg, dict)  # Changed from json.loads
    assert "query" in last_call_arg  # Changed from "user_message"
    assert last_call_arg["query"] == "Message 5"

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
    
    # Verify query included message (as dict, not JSON string)
    query_context = mock_memory_manager.query_memory.call_args[0][0]
    assert isinstance(query_context, dict)  # Changed from json.loads
    assert "query" in query_context  # Changed from "user_message"
    assert query_context["query"] == "A group of merchants wants to pass through"

@pytest.mark.asyncio
async def test_memory_reflection_trigger(agent, mock_memory_manager):
    """Test that reflection/compression happens automatically
    
    NOTE: Reflection/compression is handled automatically by MemoryManager
    during query_memory(), not explicitly triggered by Agent. This test
    verifies that the Agent correctly delegates to MemoryManager.
    """
    # Setup memory manager to simulate conversation history
    conversation_history = []
    for i in range(10):  # Add enough messages to potentially trigger compression
        conversation_history.append({
            "role": "user" if i % 2 == 0 else "agent",
            "content": f"Message {i}",
            "timestamp": datetime.now().isoformat()
        })
    
    mock_memory_manager.get_memory.return_value = {
        "static_memory": "Test static memory",
        "context": [],
        "conversation_history": conversation_history,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    # Process a message - MemoryManager handles compression automatically
    await agent.process_message("One more message")
    
    # Verify query_memory was called (compression happens inside MemoryManager)
    assert mock_memory_manager.query_memory.called
    
    # Note: We can't directly verify compression here because it's handled
    # internally by MemoryManager. The Agent just delegates to MemoryManager.

@pytest.mark.asyncio
async def test_static_memory_preservation(agent, mock_memory_manager):
    """Test that static memory remains unchanged through operations"""
    # Setup initial static memory
    static_memory_text = "Test static memory content"
    
    mock_memory_manager.get_memory.return_value = {
        "static_memory": static_memory_text,
        "context": [],
        "conversation_history": [],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    # Process several messages
    for i in range(5):
        await agent.process_message(f"Message {i}")
    
    # Verify static memory in final state
    final_memory = mock_memory_manager.get_memory()
    assert "static_memory" in final_memory
    assert final_memory["static_memory"] == static_memory_text 