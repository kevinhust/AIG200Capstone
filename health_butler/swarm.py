"""
Health Butler Swarm Orchestrator.

Implements a specialized Multi-Agent Swarm for the Personal Health Butler AI.
Uses the Router-Worker pattern with Coordinator, Nutrition, and Fitness agents.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from health_butler.coordinator.coordinator_agent import CoordinatorAgent
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.agents.fitness.fitness_agent import FitnessAgent

# Setup logging
logger = logging.getLogger(__name__)


class MessageBus:
    """
    Simple message bus for agent communication.
    
    Maintains a chronological log of all inter-agent messages for context
    sharing, UI display, and debugging.
    """
    
    def __init__(self):
        """Initialize the message bus with an empty message log."""
        self.messages: List[Dict[str, Any]] = []
    
    def send(self, from_agent: str, to_agent: str, message_type: str, content: str):
        """
        Send a message from one agent to another.
        
        Args:
            from_agent: The sending agent's role.
            to_agent: The receiving agent's role.
            message_type: Type of message (task, result, query, status).
            content: The message content.
        """
        message = {
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        logger.info(f"[MessageBus] {from_agent} → {to_agent}: {message_type}")
    
    def get_context_for(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get relevant message context for a specific agent.
        
        Args:
            agent_name: The agent's role name.
            
        Returns:
            List of messages relevant to this agent.
        """
        return [msg for msg in self.messages if msg["to"] == agent_name or msg["from"] == agent_name]
    
    def get_all_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in chronological order."""
        return self.messages.copy()
    
    def get_status_updates(self) -> List[Dict[str, Any]]:
        """Get only status messages (for UI display)."""
        return [msg for msg in self.messages if msg["type"] == "status"]
    
    def clear(self):
        """Clear all messages from the bus."""
        self.messages = []


class HealthSwarm:
    """
    Health Butler Multi-Agent Swarm Orchestrator.
    
    Coordinates the Coordinator, Nutrition, and Fitness agents to provide
    comprehensive health and nutrition analysis.
    
    Workflow:
    1. User input → Coordinator (intent routing)
    2. Coordinator → Appropriate specialist(s) (Nutrition/Fitness)
    3. Specialists → Execute with tools (ViT, RAG)
    4. Coordinator → Synthesize final response
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the Health Butler Swarm.
        
        Args:
            verbose: Whether to print detailed execution logs.
        """
        self.verbose = verbose
        self._log("🏥 Initializing Health Butler Swarm...")
        
        # Initialize message bus
        self.message_bus = MessageBus()
        
        # Initialize Coordinator (Router)
        self._log("   🧭 Creating Coordinator agent...")
        self.coordinator = CoordinatorAgent()
        
        # Initialize specialist agents
        self._log("   🥗 Creating Nutrition agent...")
        self._log("   🏃 Creating Fitness agent...")
        self.workers: Dict[str, Any] = {
            "nutrition": NutritionAgent(),
            "fitness": FitnessAgent()
        }
        
        self._log(f"✅ Health Swarm initialized with {len(self.workers)} specialist agents!\n")
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
        logger.info(message)
    
    def execute(
        self, 
        user_input: str, 
        image_path: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a user request using the Health Swarm.
        
        Args:
            user_input: The text input from the user.
            image_path: Optional path to an uploaded image.
            user_context: Optional user preferences/goals.
            
        Returns:
            Dict containing:
                - response: Final synthesized response
                - delegations: List of agent delegations made
                - agent_outputs: Individual agent results
                - message_log: Complete message bus log
        """
        self._log(f"\n{'='*70}")
        self._log(f"🎯 User Request: {user_input}")
        if image_path:
            self._log(f"   📷 Image: {image_path}")
        self._log("="*70)
        
        # Clear message bus for new request
        self.message_bus.clear()
        
        # Record user input
        self.message_bus.send("user", "coordinator", "task", user_input)
        
        # Step 1: Coordinator analyzes and creates delegation plan
        self._log("\n🧭 [Coordinator] Analyzing request and creating delegation plan...")
        self.message_bus.send("coordinator", "system", "status", "Analyzing user intent...")
        
        delegations = self.coordinator.analyze_and_delegate(user_input)
        
        self._log(f"   📋 Delegation plan: {len(delegations)} step(s)")
        for i, d in enumerate(delegations, 1):
            self._log(f"      {i}. {d['agent'].capitalize()} → {d['task'][:50]}...")
        
        # Step 2: Execute delegations sequentially
        agent_outputs: List[Dict[str, Any]] = []
        
        for i, delegation in enumerate(delegations, 1):
            agent_name = delegation['agent']
            agent_task = delegation['task']
            
            self._log(f"\n{'─'*70}")
            self._log(f"📤 [Coordinator → {agent_name.capitalize()}] Task {i}/{len(delegations)}")
            self.message_bus.send("coordinator", "system", "status", f"Routing to {agent_name.capitalize()} Agent...")
            
            # Record delegation
            self.message_bus.send("coordinator", agent_name, "task", agent_task)
            
            # Get worker agent
            worker = self.workers.get(agent_name)
            if not worker:
                error_msg = f"Unknown agent: {agent_name}"
                logger.error(error_msg)
                agent_outputs.append({"agent": agent_name, "result": error_msg, "error": True})
                continue
            
            # Build context for the worker
            context = self._build_agent_context(agent_name, image_path, user_context, agent_outputs)
            
            # Execute task
            self._log(f"\n🔧 [{agent_name.capitalize()}] Executing...")
            self.message_bus.send(agent_name, "system", "status", f"{agent_name.capitalize()} Agent working...")
            
            try:
                result = worker.execute(agent_task, context)
                agent_outputs.append({
                    "agent": agent_name,
                    "task": agent_task,
                    "result": result,
                    "error": False
                })
                self._log(f"✅ [{agent_name.capitalize()}] Complete!")
                self._log(f"   Preview: {result[:150]}..." if len(result) > 150 else f"   Result: {result}")
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                logger.error(f"[{agent_name}] {error_msg}")
                agent_outputs.append({
                    "agent": agent_name,
                    "task": agent_task,
                    "result": error_msg,
                    "error": True
                })
            
            # Record result
            self.message_bus.send(agent_name, "coordinator", "result", agent_outputs[-1]["result"])
        
        # Step 3: Coordinator synthesizes final response
        self._log(f"\n{'─'*70}")
        self._log("🧭 [Coordinator] Synthesizing final response...")
        self.message_bus.send("coordinator", "system", "status", "Preparing final response...")
        
        final_response = self._synthesize_results(delegations, agent_outputs)
        
        self.message_bus.send("coordinator", "user", "result", final_response)
        
        self._log("\n" + "="*70)
        self._log("🎉 Request Complete!\n")
        
        return {
            "response": final_response,
            "delegations": delegations,
            "agent_outputs": agent_outputs,
            "message_log": self.message_bus.get_all_messages()
        }
    
    def _build_agent_context(
        self, 
        agent_name: str, 
        image_path: Optional[str],
        user_context: Optional[Dict[str, Any]],
        previous_outputs: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Build context for an agent including image path and previous results.
        
        Args:
            agent_name: The target agent.
            image_path: Optional image path.
            user_context: Optional user preferences.
            previous_outputs: Results from previous agents in the chain.
            
        Returns:
            List of context messages for the agent.
        """
        context = []
        
        # Add image path if present (for Nutrition Agent)
        if image_path and agent_name == "nutrition":
            context.append({
                "type": "image_path",
                "content": image_path
            })
        
        # Add user preferences if present
        if user_context:
            context.append({
                "type": "user_context",
                "content": str(user_context)
            })
        
        # Add previous agent outputs (chain results)
        for output in previous_outputs:
            if not output.get("error"):
                context.append({
                    "from": output["agent"],
                    "type": "previous_result",
                    "content": output["result"]
                })
        
        return context
    
    def _synthesize_results(
        self, 
        delegations: List[Dict[str, str]], 
        agent_outputs: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesize final response from agent outputs.
        
        For simple single-agent responses, return directly.
        For multi-agent workflows, use Coordinator to synthesize.
        
        Args:
            delegations: The delegation plan.
            agent_outputs: Results from each agent.
            
        Returns:
            Final synthesized response string.
        """
        # Filter successful outputs
        successful_outputs = [o for o in agent_outputs if not o.get("error")]
        
        if not successful_outputs:
            return "I apologize, but I encountered an error processing your request. Please try again."
        
        # Single agent: return directly
        if len(successful_outputs) == 1:
            return successful_outputs[0]["result"]
        
        # Multiple agents: synthesize
        synthesis_prompt = "Synthesize the following agent outputs into a cohesive response:\n\n"
        for output in successful_outputs:
            synthesis_prompt += f"[{output['agent'].capitalize()} Agent]:\n{output['result']}\n\n"
        synthesis_prompt += "Provide a unified, user-friendly summary."
        
        return self.coordinator.execute(synthesis_prompt)
    
    def get_status_updates(self) -> List[Dict[str, Any]]:
        """Get status updates for UI display."""
        return self.message_bus.get_status_updates()
    
    def reset(self):
        """Reset the swarm state."""
        self.message_bus.clear()
        self.coordinator.reset_history()
        for worker in self.workers.values():
            worker.reset_history()


# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing Health Butler Swarm...\n")
    
    swarm = HealthSwarm(verbose=True)
    
    # Test 1: Text query
    print("\n" + "="*70)
    print("TEST 1: Text Query")
    print("="*70)
    result = swarm.execute("What are the health benefits of eating salmon?")
    print(f"\n📝 Final Response:\n{result['response']}")
    
    # Test 2: Fitness query
    print("\n" + "="*70)
    print("TEST 2: Fitness Query")
    print("="*70)
    swarm.reset()
    result = swarm.execute("I just ate a 800 calorie lunch. What exercise should I do?")
    print(f"\n📝 Final Response:\n{result['response']}")
