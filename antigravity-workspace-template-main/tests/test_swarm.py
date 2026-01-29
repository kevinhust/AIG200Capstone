"""Tests for the multi-agent swarm system."""

import pytest
from src.swarm import SwarmOrchestrator, MessageBus
from src.agents.router_agent import RouterAgent
from src.agents.coder_agent import CoderAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.researcher_agent import ResearcherAgent


class TestMessageBus:
    """Test the MessageBus class."""
    
    def test_message_bus_init(self):
        """Test message bus initialization."""
        bus = MessageBus()
        assert len(bus.messages) == 0
    
    def test_send_message(self):
        """Test sending messages."""
        bus = MessageBus()
        bus.send("router", "coder", "task", "Build a calculator")
        
        assert len(bus.messages) == 1
        msg = bus.messages[0]
        assert msg["from"] == "router"
        assert msg["to"] == "coder"
        assert msg["type"] == "task"
        assert msg["content"] == "Build a calculator"
        assert "timestamp" in msg
    
    def test_get_context_for(self):
        """Test retrieving context for an agent."""
        bus = MessageBus()
        bus.send("router", "coder", "task", "Task 1")
        bus.send("coder", "router", "result", "Result 1")
        bus.send("router", "reviewer", "task", "Task 2")
        
        coder_context = bus.get_context_for("coder")
        assert len(coder_context) == 2  # Messages to and from coder
        
        reviewer_context = bus.get_context_for("reviewer")
        assert len(reviewer_context) == 1
    
    def test_clear(self):
        """Test clearing the message bus."""
        bus = MessageBus()
        bus.send("router", "coder", "task", "Task")
        bus.clear()
        assert len(bus.messages) == 0


class TestSwarmOrchestrator:
    """Test the SwarmOrchestrator class."""
    
    def test_swarm_init(self):
        """Test swarm initialization."""
        swarm = SwarmOrchestrator()
        
        assert swarm.router is not None
        assert isinstance(swarm.router, RouterAgent)
        assert len(swarm.workers) == 3
        assert "coder" in swarm.workers
        assert "reviewer" in swarm.workers
        assert "researcher" in swarm.workers
    
    def test_swarm_execute(self):
        """Test basic swarm execution."""
        swarm = SwarmOrchestrator()
        result = swarm.execute("Write a hello world function", verbose=False)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_swarm_reset(self):
        """Test swarm reset functionality."""
        swarm = SwarmOrchestrator()
        swarm.execute("Test task", verbose=False)
        
        # Should have messages before reset
        assert len(swarm.message_bus.messages) > 0
        
        swarm.reset()
        
        # Messages should be cleared
        assert len(swarm.message_bus.messages) == 0


class TestAgents:
    """Test individual agent classes."""
    
    def test_router_agent_init(self):
        """Test RouterAgent initialization."""
        router = RouterAgent()
        assert router.role == "router"
        assert router.system_prompt is not None
    
    def test_router_delegation(self):
        """Test router delegation logic."""
        router = RouterAgent()
        
        # Test simple delegation
        delegations = router._simple_delegate("Build a calculator")
        assert len(delegations) > 0
        assert delegations[0]["agent"] == "coder"
        
        delegations = router._simple_delegate("Review this code for security")
        assert any(d["agent"] == "reviewer" for d in delegations)
        
        delegations = router._simple_delegate("Research JWT authentication")
        assert any(d["agent"] == "researcher" for d in delegations)
    
    def test_coder_agent_init(self):
        """Test CoderAgent initialization."""
        coder = CoderAgent()
        assert coder.role == "coder"
        assert "code" in coder.system_prompt.lower()
    
    def test_reviewer_agent_init(self):
        """Test ReviewerAgent initialization."""
        reviewer = ReviewerAgent()
        assert reviewer.role == "reviewer"
        assert "review" in reviewer.system_prompt.lower() or "quality" in reviewer.system_prompt.lower()
    
    def test_researcher_agent_init(self):
        """Test ResearcherAgent initialization."""
        researcher = ResearcherAgent()
        assert researcher.role == "researcher"
        assert "research" in researcher.system_prompt.lower() or "information" in researcher.system_prompt.lower()
