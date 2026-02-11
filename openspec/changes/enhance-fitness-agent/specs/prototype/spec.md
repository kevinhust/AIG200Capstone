## MODIFIED Requirements

### Requirement: Interactive User Interface
The system SHALL provide a web-based user interface using Streamlit with fitness-specific components for profile management and goal tracking.

#### Scenario: Chat Interaction
- **WHEN** the user types "Can I eat this?" and uploads an image
- **THEN** the UI displays the upload, correctly sends it to the agent swarm, and streams the response.

#### Scenario: Agent Transparency
- **WHEN** the Coordinator delegates a task to Nutrition Agent or Fitness Agent
- **THEN** the UI shows a routing status indicator (e.g., "Routing to Nutrition Agent...", "Analyzing fitness goals...")

#### Scenario: Profile Setup Form
- **WHEN** a first-time user accesses the application
- **THEN** the UI displays a setup form for age, weight, fitness level, health limitations, and saves the profile

#### Scenario: Goal Dashboard
- **WHEN** user has active fitness goals
- **THEN** the sidebar displays a goal widget with progress bars, current values, and days remaining

#### Scenario: Exercise Completion Tracking
- **WHEN** Fitness Agent recommends exercises
- **THEN** the UI displays a "Mark as Completed" button to track preference history
