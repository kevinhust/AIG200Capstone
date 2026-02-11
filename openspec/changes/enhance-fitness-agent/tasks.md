## 1. Data Infrastructure
- [x] Create change proposal directory structure
- [ ] 1.1 Create user profile system (`user_profiles.py`)
  - [ ] Define Pydantic models (UserProfile, FitnessGoal, HealthLimitation)
  - [ ] Implement JSON persistence to `~/.health_butler/`
  - [ ] Add session state integration
  - [ ] Write unit tests
- [ ] 1.2 Build exercise RAG tool (`exercise_rag_tool.py`)
  - [ ] Create ChromaDB collection "exercise_data"
  - [ ] Implement semantic search with metadata filtering
  - [ ] Add contraindication filtering logic
  - [ ] Write unit tests
- [ ] 1.3 Create exercise data ingestion script
  - [ ] Download Compendium of Physical Activities CSV
  - [ ] Parse and clean dataset
  - [ ] Enrich with metadata (contraindications, categories, equipment)
  - [ ] Load into ChromaDB
  - [ ] Verify data quality (spot checks)

## 2. Fitness Agent Enhancement
- [ ] 2.1 Enhance `fitness_agent.py`
  - [ ] Update system prompt with new capabilities
  - [ ] Add user profile integration
  - [ ] Implement exercise RAG tool integration
  - [ ] Add goal setting methods
  - [ ] Implement preference tracking
  - [ ] Add calorie-to-exercise calculation using MET values
- [ ] 2.2 Write comprehensive tests
  - [ ] Test goal setting and retrieval
  - [ ] Test exercise recommendations with contraindications
  - [ ] Test preference learning logic
  - [ ] Test calorie burn calculations

## 3. Integration
- [ ] 3.1 Update Coordinator Agent
  - [ ] Modify handoff to pass full nutrition context
  - [ ] Add user profile to agent context
  - [ ] Support multi-turn goal conversations
  - [ ] Write integration tests
- [ ] 3.2 Enhance Streamlit UI
  - [ ] Create user profile setup form
  - [ ] Add goal dashboard sidebar widget
  - [ ] Implement exercise completion tracker
  - [ ] Add profile export functionality
  - [ ] Test UI flows end-to-end

## 4. Verification
- [ ] 4.1 Automated testing
  - [ ] Run all unit tests (>80% coverage target)
  - [ ] Run integration tests
  - [ ] Verify ChromaDB query performance (<500ms)
- [ ] 4.2 Manual verification
  - [ ] Complete full user journey in Streamlit
  - [ ] Test profile persistence across sessions
  - [ ] Verify contraindication filtering works
  - [ ] Test preference learning over multiple interactions
- [ ] 4.3 Documentation
  - [ ] Update `health_butler/README.md`
  - [ ] Document user profile schema
  - [ ] Create usage walkthrough
