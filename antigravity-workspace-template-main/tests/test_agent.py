import pytest
from unittest.mock import MagicMock, patch
from src.agent import GeminiAgent

@pytest.fixture
def mock_agent():
    """Fixture to create an agent with mocked dependencies."""
    with patch('src.agent.MemoryManager') as MockMemory:
        agent = GeminiAgent()
        agent.memory = MockMemory.return_value
        agent.memory.get_history.return_value = []
        return agent

def test_agent_initialization(mock_agent):
    """Test that the agent initializes correctly."""
    assert mock_agent.settings.AGENT_NAME == "AntigravityAgent"

def test_agent_think_act_loop(mock_agent):
    """Test the Think-Act loop."""
    task = "Test Task"
    
    # Mock the think method to avoid sleep
    with patch.object(mock_agent, 'think') as mock_think:
        response = mock_agent.act(task)
        
        # Verify think was called
        mock_think.assert_called_once_with(task)
        
        # Verify memory was updated
        # 3 calls: User task + Thinking Process + Final Answer
        assert mock_agent.memory.add_entry.call_count == 3
        
        # Verify response format
        assert "I have completed the task" in response

def test_agent_tools_integration():
    """Test that tools can be imported and used."""
    from src.tools.example_tool import web_search
    result = web_search("test query")
    assert "Search results for: test query" in result
