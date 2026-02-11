# fitness-agent Specification

## Purpose
The Fitness Agent provides personalized exercise recommendations, goal setting, and progress tracking based on user health data and nutritional intake. It integrates with the Nutrition Agent to deliver comprehensive wellness guidance while respecting user privacy through local-only data storage.

## ADDED Requirements

### Requirement: User Health Profile Management
The system SHALL maintain user health profiles with personal attributes, fitness goals, health limitations, and exercise preferences stored locally on the user's device.

#### Scenario: Profile Creation
- **WHEN** a new user first launches the application
- **THEN** the system prompts for health information (age, weight, fitness level, limitations) and creates a JSON profile at `~/.health_butler/user_profile.json`

#### Scenario: Profile Persistence
- **WHEN** the user closes and reopens the application
- **THEN** the system loads the existing profile from disk and makes it available in session state

#### Scenario: Privacy Compliance
- **WHEN** user profile data is saved
- **THEN** the data is stored only in the local filesystem (never transmitted to cloud or external services)

#### Scenario: Profile Export
- **WHEN** the user clicks "Export Profile"
- **THEN** the system downloads the profile JSON file for backup or transfer

### Requirement: Exercise Knowledge Base
The system SHALL provide semantic search over exercise data using a RAG architecture with MET (Metabolic Equivalent) values for accurate calorie burn calculations.

#### Scenario: Exercise Query
- **WHEN** the Fitness Agent queries for "cardio exercises"
- **THEN** the RAG tool returns relevant exercises (running, cycling, swimming) ranked by semantic similarity with MET values included

#### Scenario: Contraindication Filtering
- **WHEN** a user has "knee injury" in their health limitations
- **THEN** exercise recommendations automatically exclude high-impact activities (running, jumping) and suggest low-impact alternatives

#### Scenario: Equipment Filtering
- **WHEN** querying exercises and user profile specifies "home workout"
- **THEN** results are filtered to bodyweight and home equipment exercises only

### Requirement: Personalized Exercise Recommendations
The Fitness Agent SHALL generate exercise recommendations tailored to user attributes, health limitations, and nutritional context.

#### Scenario: Calorie-Based Recommendation
- **WHEN** the Nutrition Agent reports user consumed 850 calories (burger and fries)
- **THEN** the Fitness Agent calculates and suggests exercises to balance intake (e.g., "45-minute brisk walk" using MET value 4.3)

#### Scenario: Limitation-Aware Suggestions
- **WHEN** recommending exercises for a user with "high blood pressure" limitation
- **THEN** suggestions avoid high-intensity exercises and include appropriate modifications

#### Scenario: Context-Aware Timing
- **WHEN** user requests exercise advice at 10 PM
- **THEN** the agent suggests light, evening-appropriate activities (stretching, yoga) instead of high-energy workouts

### Requirement: SMART Goal Setting and Tracking
The system SHALL support creation, tracking, and progress monitoring of Specific, Measurable, Achievable, Relevant, Time-bound fitness goals.

#### Scenario: Goal Creation
- **WHEN** user says "I want to lose 5kg in 2 months"
- **THEN** the agent creates a structured goal with target (5kg), deadline (2 months from now), and tracking parameters

#### Scenario: Progress Visualization
- **WHEN** user views the fitness dashboard
- **THEN** active goals are displayed with progress bars and days remaining

#### Scenario: Goal Achievement
- **WHEN** user reaches their goal target
- **THEN** the system displays congratulatory message and prompts for new goal setting

### Requirement: Exercise Preference Learning
The system SHALL track exercise completion history and adapt recommendations to favor user-preferred activities over time.

#### Scenario: Completion Tracking
- **WHEN** user marks "30-minute walk" as completed
- **THEN** the system increments the preference counter for "walking" in the user profile

#### Scenario: Preference-Based Recommendation
- **WHEN** user has completed "swimming" 10 times and "cycling" 2 times
- **THEN** future cardio recommendations weight swimming more heavily (70% preferred, 30% variety)

#### Scenario: Variety Maintenance
- **WHEN** generating recommendations
- **THEN** the system includes 30% non-preferred exercises to prevent stagnation and introduce new activities

### Requirement: Nutrition-Fitness Integration
The Fitness Agent SHALL receive and process nutrition analysis data from the Nutrition Agent to provide holistic wellness guidance.

#### Scenario: Meal-to-Exercise Flow
- **WHEN** Nutrition Agent completes meal analysis (calories, macros)
- **THEN** Coordinator passes full nutrition context to Fitness Agent for exercise recommendations

#### Scenario: Daily Calorie Balance
- **WHEN** user has eaten 2000 calories throughout the day
- **THEN** Fitness Agent calculates total recommended activity based on cumulative intake and user's goals

#### Scenario: Macro-Specific Advice  
- **WHEN** meal is high in carbohydrates
- **THEN** Fitness Agent suggests timing cardio post-meal to optimize glucose utilization
