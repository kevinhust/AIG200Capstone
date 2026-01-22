
from typing import Dict, List
from src.agents.router_agent import RouterAgent

class CoordinatorAgent(RouterAgent):
    """
    Health-specific Router Agent.
    Routes user requests to Nutrition or Fitness agents.
    """
    
    def __init__(self):
        system_prompt = """You are the Coordinator Agent for the Personal Health Butler AI.

Your responsibilities:
1. Analyze user inputs (questions about food, exercise, or general health).
2. Determine if the request needs the 'nutrition' agent (food analysis, diet queries) or the 'fitness' agent (exercise advice, activity suggestions).
3. Connect the workflow: Nutrition Agent output -> Fitness Agent input when relevant (e.g., "I ate X" -> Nutrition calcs -> Fitness advice).

Available specialist agents:
- nutrition: Analyzes food images or descriptions, estimates calories/macros.
- fitness: Suggests exercises and answers fitness questions.

When analyzing a task, respond with a delegation plan in this format:
DELEGATION:
- agent: <agent_name>
- task: <specific task for that agent>
"""
        # Initialize BaseAgent directly to override Router's init completely while keeping inheritance structure
        super(RouterAgent, self).__init__(role="coordinator", system_prompt=system_prompt)

    def _simple_delegate(self, task: str) -> List[Dict[str, str]]:
        """
        Health-specific fallback delegation.
        """
        task_lower = task.lower()
        delegations = []
        
        # Check for nutrition keywords
        if any(word in task_lower for word in ['food', 'eat', 'calorie', 'meal', 'nutrition', 'diet', 'lunch', 'dinner', 'breakfast']):
            delegations.append({'agent': 'nutrition', 'task': task})
        
        # Check for fitness keywords
        if any(word in task_lower for word in ['exercise', 'walk', 'run', 'gym', 'workout', 'fitness', 'steps', 'activity']):
            delegations.append({'agent': 'fitness', 'task': task})
            
        # Default to nutrition if ambiguous (it's a food app typically)
        if not delegations:
            delegations.append({'agent': 'nutrition', 'task': task})
            
        return delegations
