
from src.swarm import SwarmOrchestrator, MessageBus
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.coordinator.coordinator_agent import CoordinatorAgent

class HealthSwarmOrchestrator(SwarmOrchestrator):
    """
    Orchestrates the Personal Health Butler swarm.
    Overrides the default SwarmOrchestrator to use health-specific agents.
    """
    
    def __init__(self):
        print("🥗 Initializing Personal Health Butler Swarm (Refactored Root)...")
        
        # Initialize message bus
        self.message_bus = MessageBus()
        
        # Initialize custom Coordinator as Router
        print("   🧭 Creating Coordinator agent...")
        self.router = CoordinatorAgent()
        
        # Initialize specialist workers
        print("   🍎 Creating Nutrition agent...")
        print("   🏃 Creating Fitness agent...")
        self.workers = {
            "nutrition": NutritionAgent(),
            "fitness": FitnessAgent()
        }
        
        print(f"✅ Health Swarm initialized with {len(self.workers)} specialist agents!\n")

if __name__ == "__main__":
    swarm = HealthSwarmOrchestrator()
    swarm.execute("I just ate a big burger, what should I do?", verbose=True)
