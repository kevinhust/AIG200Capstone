# Change: Enhanced Fitness Agent with Goal Setting and Personalization

## Why
The current Fitness Agent provides only basic, generic exercise suggestions. To deliver personalized wellness guidance that aligns with our MVP vision, the agent needs to:
1. Set and track user fitness goals based on health data
2. Recommend exercises tailored to individual limitations (e.g., knee injuries)
3. Learn user preferences over time to increase engagement
4. Calculate precise calorie-to-exercise mappings using scientific MET values
5. Integrate deeply with Nutrition Agent data for holistic recommendations

This enhancement transforms the Fitness Agent from a simple advice-giver into an intelligent, adaptive wellness coach that respects user privacy by storing all data locally.

## What Changes
- **User Profile System**: 
  - Create `health_butler/data/user_profiles.py` for managing user health data (age, weight, fitness level, limitations, goals)
  - Local JSON persistence (`~/.health_butler/user_profile.json`) for privacy
  - Pydantic models for type safety and validation
  
- **Exercise Knowledge Base (RAG)**:
  - Create `health_butler/data_rag/exercise_rag_tool.py` for exercise semantic search
  - Ingest Compendium of Physical Activities dataset (800+ exercises with MET values)
  - ChromaDB collection "exercise_data" parallel to existing nutrition RAG
  - Metadata filtering for contraindications, intensity, equipment needs
  
- **Fitness Agent Enhancement**:
  - Update `health_butler/agents/fitness/fitness_agent.py` with:
    - Goal setting and tracking capabilities (SMART goals)
    - Preference learning (track completed exercises, suggest favorites more often)
    - Context-aware recommendations (time of day, available equipment)
    - Integration with user profile and exercise RAG
    
- **Coordinator Integration**:
  - Update `health_butler/coordinator/coordinator_agent.py` to pass full nutrition analysis + user profile context
  - Support multi-turn conversations for goal management
  
- **UI Enhancements**:
  - Add user profile setup form in Streamlit
  - Goal dashboard with progress tracking
  - Exercise completion tracker

## Impact
- **Affected Specs**: `fitness-agent` (new), `prototype` (modified for UI integration)
- **Affected Code**: 
  - New: `health_butler/data/user_profiles.py`, `health_butler/data_rag/exercise_rag_tool.py`, `health_butler/scripts/ingest_exercise_data.py`
  - Modified: `health_butler/agents/fitness/fitness_agent.py`, `health_butler/coordinator/coordinator_agent.py`, Streamlit UI files
  - Tests: New test files for user profile, exercise RAG, and enhanced fitness agent
- **Data Requirements**: Download Compendium of Physical Activities dataset (~2MB CSV)
- **Privacy Model**: All user data stored locally on device (no cloud storage)
- **Timeline**: 3-5 days implementation
