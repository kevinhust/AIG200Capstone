"""
Enhanced Coordinator Agent for Personal Health Butler AI.

Routes health requests to Nutrition/Fitness agents with full context passing:
- Loads user profiles and passes to Fitness Agent
- Chains Nutrition → Fitness with full meal analysis data
- Supports multi-turn goal conversations
"""

from typing import Dict, List, Optional
import logging
import re
from src.agents.router_agent import RouterAgent
from health_butler.data.user_profiles import UserProfile, get_user_profile

logger = logging.getLogger(__name__)


class CoordinatorAgent(RouterAgent):
    """
    Health-specific Router Agent with enhanced context management.
    
    Responsibilities:
    - Route requests to Nutrition or Fitness agents
    - Load and pass user profiles to agents
    - Chain Nutrition output to Fitness input (meal → exercise advice)
    - Maintain conversation context for goal tracking
    """
    
    def __init__(self):
        system_prompt = """You are the Coordinator Agent for the Personal Health Butler AI.

Your responsibilities:
1. Analyze user inputs (questions about food, exercise, or general health).
2. Determine if the request needs the 'nutrition' agent (food analysis, diet queries) or the 'fitness' agent (exercise advice, activity suggestions).
3. Connect the workflow: Nutrition Agent output → Fitness Agent input when relevant (e.g., "I ate X" → Nutrition calcs → Fitness advice).
4. Support goal management conversations (creating, tracking, updating fitness goals).

Available specialist agents:
- nutrition: Analyzes food images or descriptions, estimates calories/macros.
- fitness: Suggests exercises, sets goals, tracks progress, learns preferences.

When analyzing a task, respond with a delegation plan in this format:
DELEGATION:
- agent: <agent_name>
- task: <specific task for that agent>

For meal analysis, you should delegate to BOTH agents in sequence:
1. nutrition agent to analyze the food
2. fitness agent to suggest exercises based on calorie intake
"""
        # Initialize BaseAgent directly to override Router's init completely while keeping inheritance structure
        super(RouterAgent, self).__init__(role="coordinator", system_prompt=system_prompt)
        
        # User profile loaded per session
        self.user_profile: Optional[UserProfile] = None
        
    def execute_with_context(
        self,
        task: str,
        user_profile: Optional[UserProfile] = None,
        context: Optional[List[Dict]] = None
    ) -> str:
        """
        Execute coordination with full context management.
        
        Args:
            task: User request
            user_profile: Optional user profile to pass to agents
            context: Optional conversation context
            
        Returns:
            Final coordinated response
        """
        # Store or load user profile
        if user_profile:
            self.user_profile = user_profile
        elif self.user_profile is None:
            try:
                self.user_profile = get_user_profile()
                logger.info("User profile loaded from disk")
            except Exception as e:
                logger.warning(f"Could not load user profile: {e}")
        
        # Get delegation plan
        delegations = self.analyze_and_delegate(task)
        logger.info(f"Delegation plan: {delegations}")
        
        # Execute delegations with context passing
        results = []
        nutrition_result = None
        
        for delegation in delegations:
            agent_name = delegation['agent']
            agent_task = delegation['task']
            
            # Build context for this agent
            agent_context = self._build_agent_context(
                agent_name=agent_name,
                user_profile=self.user_profile,
                nutrition_result=nutrition_result,
                base_context=context
            )
            
            # Execute (this would call the actual agent in production)
            # For now, returning delegation info
            result = f"[{agent_name.upper()}] {agent_task}"
            
            # If this was nutrition agent, store result for fitness agent
            if agent_name == 'nutrition':
                nutrition_result = result
            
            results.append(result)
        
        # Synthesize if multiple agents involved
        if len(results) > 1:
            return self.synthesize_results(delegations, results)
        
        return results[0] if results else "No agents available."
    
    def _build_agent_context(
        self,
        agent_name: str,
        user_profile: Optional[UserProfile],
        nutrition_result: Optional[str],
        base_context: Optional[List[Dict]]
    ) -> List[Dict[str, str]]:
        """
        Build context to pass to specialist agents.
        
        Args:
            agent_name: Name of the agent receiving context
            user_profile: User health profile
            nutrition_result: Previous nutrition analysis (if available)
            base_context: Base conversation context
            
        Returns:
            Context list for agent
        """
        context = base_context.copy() if base_context else []
        
        # Add user profile for fitness agent
        if agent_name == 'fitness' and user_profile:
            context.append({
                "type": "user_profile",
                "content": user_profile.to_dict()
            })
            logger.info("Added user profile to fitness agent context")
        
        # Add nutrition data for fitness agent
        if agent_name == 'fitness' and nutrition_result:
            # Parse nutrition result to extract calories/macros
            nutrition_data = self._parse_nutrition_result(nutrition_result)
            if nutrition_data:
                context.append({
                    "type": "nutrition_data",
                    "from": "nutrition",
                    "content": nutrition_data
                })
                logger.info(f"Added nutrition data to fitness agent context: {nutrition_data}")
        
        return context
    
    def _parse_nutrition_result(self, nutrition_result: str) -> Optional[Dict]:
        """
        Parse nutrition agent output to extract structured data.
        
        Args:
            nutrition_result: Raw nutrition agent response
            
        Returns:
            Dictionary with calories and macros or None
        """
        # Extract calories using regex
        calories_match = re.search(r'(\d+)\s*(?:kcal|calories?)', nutrition_result, re.IGNORECASE)
        
        # Extract macros
        protein_match = re.search(r'(\d+)g?\s*protein', nutrition_result, re.IGNORECASE)
        carbs_match = re.search(r'(\d+)g?\s*carb(?:ohydrate)?s?', nutrition_result, re.IGNORECASE)
        fat_match = re.search(r'(\d+)g?\s*fat', nutrition_result, re.IGNORECASE)
        
        if not calories_match:
            return None
        
        nutrition_data = {
            "total_calories": int(calories_match.group(1))
        }
        
        # Add macros if available
        macros = {}
        if protein_match:
            macros["protein"] = int(protein_match.group(1))
        if carbs_match:
            macros["carbs"] = int(carbs_match.group(1))
        if fat_match:
            macros["fat"] = int(fat_match.group(1))
        
        if macros:
            nutrition_data["macros"] = macros
        
        return nutrition_data

    def _simple_delegate(self, task: str) -> List[Dict[str, str]]:
        """
        Enhanced health-specific fallback delegation with chaining support.
        """
        task_lower = task.lower()
        delegations = []
        
        # Check for goal-related keywords (fitness only)
        if any(word in task_lower for word in ['goal', 'progress', 'track', 'lose weight', 'gain muscle']):
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations
        
        # Check for exercise completion tracking
        if any(word in task_lower for word in ['completed', 'finished', 'done with']) and \
           any(word in task_lower for word in ['walk', 'run', 'swim', 'exercise', 'workout']):
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations
        
        # Check for nutrition keywords
        has_nutrition = any(word in task_lower for word in [
            'food', 'eat', 'ate', 'calorie', 'meal', 'nutrition', 
            'diet', 'lunch', 'dinner', 'breakfast', 'snack'
        ])
        
        # Check for fitness keywords
        has_fitness = any(word in task_lower for word in [
            'exercise', 'walk', 'run', 'gym', 'workout', 'fitness', 
            'steps', 'activity', 'burn calories'
        ])
        
        # Meal analysis → chain both agents
        if has_nutrition and ('ate' in task_lower or 'just ate' in task_lower or 'i ate' in task_lower):
            # First nutrition to analyze meal
            delegations.append({'agent': 'nutrition', 'task': task})
            # Then fitness to suggest exercises
            delegations.append({
                'agent': 'fitness',
                'task': 'Suggest exercises to balance this meal intake'
            })
            return delegations
        
        # Nutrition only
        if has_nutrition:
            delegations.append({'agent': 'nutrition', 'task': task})
        
        # Fitness only
        if has_fitness:
            delegations.append({'agent': 'fitness', 'task': task})
        
        # Default to nutrition if ambiguous (it's a food app typically)
        if not delegations:
            delegations.append({'agent': 'nutrition', 'task': task})
        
        return delegations
    
    def supports_chaining(self) -> bool:
        """Indicate that this coordinator supports agent chaining."""
        return True


# Convenience function for Streamlit integration
def coordinate_health_request(
    task: str,
    user_profile: Optional[UserProfile] = None,
    context: Optional[List[Dict]] = None
) -> str:
    """
    Coordinate a health request through Nutrition/Fitness agents.
    
    Args:
        task: User request
        user_profile: Optional user profile
        context: Optional conversation context
        
    Returns:
        Coordinated response
    """
    coordinator = CoordinatorAgent()
    return coordinator.execute_with_context(task, user_profile, context)


if __name__ == "__main__":
    # Test enhanced coordinator
    logging.basicConfig(level=logging.INFO)
    
    coordinator = CoordinatorAgent()
    
    # Test 1: Simple delegation
    print("\n=== Test 1: Simple Nutrition Query ===")
    delegations = coordinator.analyze_and_delegate("What's in this burger?")
    print(f"Delegations: {delegations}")
    
    # Test 2: Chained delegation (meal → exercise)
    print("\n=== Test 2: Meal Analysis with Exercise Recommendation ===")
    delegations = coordinator.analyze_and_delegate("I just ate a burger and fries")
    print(f"Delegations: {delegations}")
    
    # Test 3: Goal setting
    print("\n=== Test 3: Goal Setting ===")
    delegations = coordinator.analyze_and_delegate("Help me set a goal to lose 5kg")
    print(f"Delegations: {delegations}")
    
    # Test 4: Exercise completion
    print("\n=== Test 4: Exercise Completion ===")
    delegations = coordinator.analyze_and_delegate("I completed a 30-minute walk")
    print(f"Delegations: {delegations}")
    
    # Test 5: Nutrition result parsing
    print("\n=== Test 5: Nutrition Parsing ===")
    nutrition_output = "This burger contains approximately 850 calories with 35g protein, 90g carbs, and 28g fat."
    parsed = coordinator._parse_nutrition_result(nutrition_output)
    print(f"Parsed: {parsed}")
