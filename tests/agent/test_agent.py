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
        "new_information": {"test": "data"},
        "suggested_phase": "INTERACTION",
        "confidence": 0.9
    }
    mock.update_memory.return_value = True
    return mock

@pytest.fixture
def agent(mock_llm_service, mock_memory_manager):
    """Create an agent instance with mock services"""
    return Agent(mock_llm_service, mock_memory_manager)

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test agent initialization"""
    assert agent.current_phase == AgentPhase.INITIALIZATION
    assert agent.conversation_history == []

@pytest.mark.asyncio
async def test_process_message_success(agent, mock_memory_manager):
    """Test successful message processing"""
    response = await agent.process_message("Hello")
    
    # Check response
    assert response == "Test response"
    
    # Check conversation history
    assert len(agent.conversation_history) == 2  # User message + assistant response
    assert agent.conversation_history[0]["role"] == "user"
    assert agent.conversation_history[0]["content"] == "Hello"
    assert agent.conversation_history[1]["role"] == "assistant"
    assert agent.conversation_history[1]["content"] == "Test response"
    
    # Verify memory manager was called with correct context
    mock_memory_manager.query_memory.assert_called_once()
    call_arg = mock_memory_manager.query_memory.call_args[0][0]
    context = json.loads(call_arg)
    assert context["current_phase"] == "INITIALIZATION"
    assert context["user_message"] == "Hello"
    assert isinstance(context["recent_messages"], list)

@pytest.mark.asyncio
async def test_process_message_memory_manager_error(agent, mock_memory_manager):
    """Test message processing with memory manager error"""
    mock_memory_manager.query_memory.return_value = None
    
    response = await agent.process_message("Hello")
    
    assert "Error processing message" in response
    assert len(agent.conversation_history) == 2
    assert agent.conversation_history[1]["role"] == "error"

@pytest.mark.asyncio
async def test_learn_success(agent, mock_memory_manager):
    """Test successful learning"""
    success = await agent.learn("New information")
    
    assert success is True
    assert agent.current_phase == AgentPhase.LEARNING
    assert len(agent.conversation_history) == 1
    assert "successfully" in agent.conversation_history[0]["content"]
    
    # Verify memory manager was called with correct context
    mock_memory_manager.update_memory.assert_called_once()
    call_arg = mock_memory_manager.update_memory.call_args[0][0]
    context = json.loads(call_arg)
    assert context["phase"] == "LEARNING"
    assert context["information"] == "New information"
    assert isinstance(context["recent_history"], list)

@pytest.mark.asyncio
async def test_learn_memory_manager_error(agent, mock_memory_manager):
    """Test learning with memory manager error"""
    mock_memory_manager.update_memory.return_value = False
    
    success = await agent.learn("New information")
    
    assert success is False
    assert len(agent.conversation_history) == 1
    assert "Failed" in agent.conversation_history[0]["content"]

@pytest.mark.asyncio
async def test_reflect(agent, mock_memory_manager):
    """Test reflection process"""
    await agent.reflect()
    
    assert len(agent.conversation_history) == 1
    assert "reflection" in agent.conversation_history[0]["content"].lower()
    
    # Verify memory manager was called with correct context
    mock_memory_manager.update_memory.assert_called_once()
    call_arg = mock_memory_manager.update_memory.call_args[0][0]
    context = json.loads(call_arg)
    assert context["operation"] == "reflect"
    assert isinstance(context["recent_history"], list)

@pytest.mark.asyncio
async def test_reflect_memory_manager_error(agent, mock_memory_manager):
    """Test reflection with memory manager error"""
    mock_memory_manager.update_memory.return_value = False
    
    await agent.reflect()
    
    assert len(agent.conversation_history) == 1
    assert "Failed" in agent.conversation_history[0]["content"]

def test_get_conversation_history(agent):
    """Test getting conversation history"""
    test_message = {"role": "user", "content": "test", "timestamp": datetime.now().isoformat()}
    agent.conversation_history = [test_message]
    history = agent.get_conversation_history()
    assert history == [test_message]

def test_get_current_phase(agent):
    """Test getting current phase"""
    assert agent.get_current_phase() == AgentPhase.INITIALIZATION
    
    agent.current_phase = AgentPhase.INTERACTION
    assert agent.get_current_phase() == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_phase_transition(agent, mock_memory_manager):
    """Test phase transitions during message processing"""
    await agent.process_message("Hello")
    assert agent.current_phase == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_conversation_history_limit(agent, mock_memory_manager):
    """Test conversation history in message processing"""
    # Add more than 5 messages
    for i in range(6):
        await agent.process_message(f"Message {i}")
    
    # Verify that only last 5 messages were sent in context
    last_call_arg = mock_memory_manager.query_memory.call_args[0][0]
    context = json.loads(last_call_arg)
    assert len(context["recent_messages"]) <= 5

@pytest.mark.asyncio
async def test_memory_manager_context_format(agent, mock_memory_manager):
    """Test that contexts sent to memory manager are properly formatted"""
    # Test query context
    await agent.process_message("Test message")
    query_context = json.loads(mock_memory_manager.query_memory.call_args[0][0])
    assert set(query_context.keys()) == {"current_phase", "recent_messages", "user_message"}
    
    # Test learning context
    await agent.learn("Test info")
    learning_context = json.loads(mock_memory_manager.update_memory.call_args[0][0])
    assert set(learning_context.keys()) == {"phase", "information", "recent_history"}
    
    # Test reflection context
    await agent.reflect()
    reflection_context = json.loads(mock_memory_manager.update_memory.call_args[0][0])
    assert set(reflection_context.keys()) == {"phase", "recent_history", "operation"}
    assert reflection_context["operation"] == "reflect" 