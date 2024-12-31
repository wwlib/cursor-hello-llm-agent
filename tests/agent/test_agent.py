import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime

from src.agent.agent import Agent, AgentPhase

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    mock = Mock()
    mock.generate.return_value = json.dumps({
        "response": "Test response",
        "new_information": {"test": "data"},
        "suggested_phase": "INTERACTION"
    })
    return mock

@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager"""
    mock = Mock()
    mock.get_memory_context.return_value = {"test": "memory"}
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
async def test_process_message_success(agent, mock_llm_service, mock_memory_manager):
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
    
    # Verify LLM and memory manager were called
    mock_llm_service.generate.assert_called_once()
    mock_memory_manager.get_memory_context.assert_called_once()
    mock_memory_manager.update_memory.assert_called_once()

@pytest.mark.asyncio
async def test_process_message_error(agent, mock_llm_service):
    """Test message processing with LLM error"""
    mock_llm_service.generate.side_effect = Exception("LLM error")
    
    response = await agent.process_message("Hello")
    
    assert "Error processing message" in response
    assert len(agent.conversation_history) == 2
    assert agent.conversation_history[1]["role"] == "error"

@pytest.mark.asyncio
async def test_learn_success(agent, mock_llm_service, mock_memory_manager):
    """Test successful learning"""
    success = await agent.learn("New information")
    
    assert success is True
    assert agent.current_phase == AgentPhase.LEARNING
    assert len(agent.conversation_history) == 1
    assert "successfully" in agent.conversation_history[0]["content"]
    
    mock_llm_service.generate.assert_called_once()
    mock_memory_manager.update_memory.assert_called_once()

@pytest.mark.asyncio
async def test_learn_failure(agent, mock_llm_service):
    """Test learning with error"""
    mock_llm_service.generate.side_effect = Exception("Learning error")
    
    success = await agent.learn("New information")
    
    assert success is False
    assert len(agent.conversation_history) == 1
    assert "error" in agent.conversation_history[0]["content"].lower()

@pytest.mark.asyncio
async def test_reflect(agent, mock_llm_service, mock_memory_manager):
    """Test reflection process"""
    await agent.reflect()
    
    assert len(agent.conversation_history) == 1
    assert "reflection" in agent.conversation_history[0]["content"].lower()
    
    mock_llm_service.generate.assert_called_once()
    mock_memory_manager.update_memory.assert_called_once()

@pytest.mark.asyncio
async def test_reflect_error(agent, mock_llm_service):
    """Test reflection with error"""
    mock_llm_service.generate.side_effect = Exception("Reflection error")
    
    await agent.reflect()
    
    assert len(agent.conversation_history) == 1
    assert "error" in agent.conversation_history[0]["content"].lower()

def test_get_conversation_history(agent):
    """Test getting conversation history"""
    agent.conversation_history = [{"test": "message"}]
    history = agent.get_conversation_history()
    assert history == [{"test": "message"}]

def test_get_current_phase(agent):
    """Test getting current phase"""
    assert agent.get_current_phase() == AgentPhase.INITIALIZATION
    
    agent.current_phase = AgentPhase.INTERACTION
    assert agent.get_current_phase() == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_phase_transition(agent):
    """Test phase transitions during message processing"""
    await agent.process_message("Hello")
    assert agent.current_phase == AgentPhase.INTERACTION

@pytest.mark.asyncio
async def test_conversation_history_limit(agent):
    """Test conversation history in message processing"""
    # Add more than 5 messages
    for i in range(6):
        await agent.process_message(f"Message {i}")
    
    # Check that the prompt only includes last 5 messages
    last_call_args = agent.llm.generate.call_args[0][0]
    history_section = last_call_args.split("Previous Messages:")[1].split("User Message:")[0]
    message_count = history_section.count('"role":')
    assert message_count <= 10  # 5 messages * 2 (user + assistant) 