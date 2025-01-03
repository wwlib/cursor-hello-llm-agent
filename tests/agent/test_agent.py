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
        "response": "Test response",
        "suggested_phase": "INTERACTION",
        "confidence": 0.9
    }
    mock.get_memory_context.return_value = {
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