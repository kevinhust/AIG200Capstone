## ADDED Requirements

### Requirement: Nutrition Analysis Capability
The system SHALL provide a `NutritionAgent` capable of analyzing food descriptions or images to provide nutritional information.

#### Scenario: Text-based Analysis
- **WHEN** the agent receives a text description "100g chicken breast"
- **THEN** it calls the RAG tool to retrieve nutritional data
- **AND** returns a structured response with calories and macros

### Requirement: Fitness Advice Capability
The system SHALL provide a `FitnessAgent` capable of suggesting post-meal activities.

#### Scenario: Post-Meal Suggestion
- **WHEN** the agent receives calorie intake data (e.g., "600 kcal lunch")
- **THEN** it suggests appropriate light exercise (e.g., "15 min walk")

### Requirement: RAG Knowledge Base
The system SHALL support a local RAG pipeline for nutrition data retrieval.

#### Scenario: Data Ingestion
- **WHEN** the ingestion script is run with USDA JSON data
- **THEN** a FAISS index is created and saved to disk

#### Scenario: Content Retrieval
- **WHEN** a query is executed against the index
- **THEN** relevant nutrition content chunks are returned with high similarity score

### Requirement: Swarm Coordination
The system SHALL provide a `CoordinatorAgent` to route user requests to the appropriate specialist.

#### Scenario: Routing to Nutrition
- **WHEN** the user says "What is in this burger?"
- **THEN** the Coordinator delegates the task to the `NutritionAgent`
