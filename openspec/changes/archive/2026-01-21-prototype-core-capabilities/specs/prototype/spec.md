## ADDED Requirements

### Requirement: Interactive User Interface
The system SHALL provide a web-based user interface using Streamlit.

#### Scenario: Chat Interaction
- **WHEN** the user types "Can I eat this?" and uploads an image
- **THEN** the UI displays the upload, correctly sends it to the agent swarm, and streams the response.

#### Scenario: Agent Transparency
- **WHEN** the Coordinator delegates a task to Nutrition Agent
- **THEN** the UI shows a "Routing to Nutrition Agent..." status indicator.

### Requirement: Semantic Nutrition Search
The system SHALL use semantic embeddings for retrieving nutrition data.

#### Scenario: Synonym Retrieval
- **WHEN** the user queries "protein bar" (even if exact phrase is missing)
- **THEN** the RAG tool retrieves logically relevant items (e.g., "energy bar", "snack bar") using vector similarity.

### Requirement: Real-time Food Classification
The system SHALL use a pre-trained Vision Transformer (ViT) model for image classification.

#### Scenario: ViT Inference
- **WHEN** an image is passed to `VisionTool`
- **THEN** it runs local inference (ViT) and returns the top predicted food label (e.g., "hamburger") with confidence score.
