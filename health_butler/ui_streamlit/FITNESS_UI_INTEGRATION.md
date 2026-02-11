# Fitness Agent UI Integration Guide

## Quick Start

Add these 3 lines to your existing `app.py` to integrate all fitness features:

```python
# At the top with other imports
from health_butler.ui_streamlit.fitness_components import integrate_fitness_ui, render_exercise_completion_tracker

# After st.set_page_config() and before main content
fitness_ui = integrate_fitness_ui()

# After fitness recommendations (in your agent response section)
render_exercise_completion_tracker()
```

That's it! You now have:
- ✅ User profile setup in sidebar
- ✅ Goal dashboard with progress bars
- ✅ Exercise completion tracker

---

## Full Integration Example

Here's how to enhance the existing `app.py`:

```python
import streamlit as st
import time
from PIL import Image
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import existing tools
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.data_rag.rag_tool import RagTool

# NEW: Import Fitness UI components
from health_butler.ui_streamlit.fitness_components import (
    integrate_fitness_ui,
    render_exercise_completion_tracker,
    render_goal_creation_form
)

# NEW: Import enhanced agents
from health_butler.coordinator.coordinator_agent import CoordinatorAgent
from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent

# Page Config
st.set_page_config(
    page_title="Personal Health Butler AI",
    page_icon="🤖",
    layout="wide"
)

# NEW: Initialize Fitness UI (adds sidebar components automatically)
fitness_ui = integrate_fitness_ui()

# Initialize Tools
@st.cache_resource
def load_tools():
    vision = VisionTool()
    rag = RagTool()
    return vision, rag

vision_tool, rag_tool = load_tools()

# NEW: Initialize Agents
@st.cache_resource
def load_agents():
    coordinator = CoordinatorAgent()
    nutrition = NutritionAgent()
    fitness = FitnessAgent()
    return coordinator, nutrition, fitness

coordinator_agent, nutrition_agent, fitness_agent = load_agents()

# Main Interface
st.title("Your Personal AI Health Assistant")
st.markdown("Upload a meal photo or ask a nutrition/fitness question.")

# Chat History (existing)
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image" in msg:
            st.image(msg["image"], width=300)

# Image Upload (existing, but now passes to Coordinator)
uploaded_file = st.file_uploader("Upload Meal Photo", type=["jpg", "png", "jpeg"])

if uploaded_file and "last_processed_file" not in st.session_state:
    st.session_state.last_processed_file = None

if uploaded_file and uploaded_file != st.session_state.last_processed_file:
    temp_path = Path("temp.jpg")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.chat_message("user"):
        st.image(uploaded_file, caption="Analyzing this meal...", width=300)
    st.session_state.messages.append({"role": "user", "content": "Analyze this meal.", "image": uploaded_file})
    
    with st.chat_message("assistant"):
        status_container = st.status("Thinking...", expanded=True)
        
        # Vision Analysis
        status_container.write("🔍 Scanning image with ViT...")
        vision_results = vision_tool.detect_food(str(temp_path))
        
        if vision_results and "label" in vision_results[0]:
            food_item = vision_results[0]["label"]
            confidence = vision_results[0]["confidence"]
            status_container.write(f"✅ Detected: **{food_item}** ({confidence:.1%})")
            
            # RAG Lookup
            status_container.write(f"📚 Looking up nutrition...")
            rag_results = rag_tool.query(food_item, top_k=1)
            
            nutrition_info = rag_results[0]["text"] if rag_results else "No data found."
            status_container.write("✅ Nutrition data retrieved.")
            
            # NEW: Get user profile for personalized fitness advice
            user_profile = st.session_state.get('user_profile')
            
            # NEW: Call Nutrition Agent
            status_container.write("🧑‍⚕️ Analyzing nutrition...")
            nutrition_response = nutrition_agent.execute(f"Analyze {food_item}")
            
            # NEW: Call Fitness Agent with nutrition context
            status_container.write("💪 Generating exercise recommendations...")
            context = [
                {
                    "type": "nutrition_data",
                    "content": {"total_calories": 850, "food_item": food_item}  # Parse from nutrition_response
                }
            ]
            fitness_response = fitness_agent.execute(
                "Suggest exercises to balance this meal",
                context=context
            )
            
            status_container.update(label="Analysis Complete", state="complete", expanded=False)
            
            # Combined Response
            response_text = f"""**Nutrition Analysis:**
{nutrition_response}

**Fitness Recommendation:**
{fitness_response}
"""
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # NEW: Show exercise tracker
            st.markdown("---")
            render_exercise_completion_tracker()
        
        else:
            status_container.update(label="Analysis Failed", state="error")
            st.error("Could not identify the food item.")
    
    st.session_state.last_processed_file = uploaded_file

# Text Input (enhanced with agent routing)
if prompt := st.chat_input("Ask about nutrition or fitness..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        # NEW: Route through Coordinator Agent
        user_profile = st.session_state.get('user_profile')
        
        status = st.status("Routing to specialist...", expanded=True)
        
        # Determine which agent(s) to use
        delegations = coordinator_agent.analyze_and_delegate(prompt)
        status.write(f"📋 Plan: {len(delegations)} step(s)")
        
        responses = []
        for delegation in delegations:
            agent_name = delegation['agent']
            agent_task = delegation['task']
            
            status.write(f"🤖 Calling {agent_name} agent...")
            
            if agent_name == 'nutrition':
                response = nutrition_agent.execute(agent_task)
            elif agent_name == 'fitness':
                # Pass user profile to fitness agent
                context = []
                if user_profile:
                    context.append({"type": "user_profile", "content": user_profile.to_dict()})
                response = fitness_agent.execute(agent_task, context=context)
            else:
                response = "Agent not available."
            
            responses.append(response)
        
        status.update(label="Complete", state="complete", expanded=False)
        
        # Display response(s)
        final_response = "\n\n".join(responses)
        st.markdown(final_response)
        st.session_state.messages.append({"role": "assistant", "content": final_response})
        
        # NEW: Show exercise tracker if fitness-related
        if any(d['agent'] == 'fitness' for d in delegations):
            st.markdown("---")
            render_exercise_completion_tracker()

# NEW: Add goal creation in sidebar or bottom
with st.sidebar:
    with st.expander("🎯 Create New Goal"):
        render_goal_creation_form()
```

---

## Component Reference

### 1. `integrate_fitness_ui()`

Automatically adds profile setup and goal dashboard to sidebar.

**Usage:**
```python
fitness_ui = integrate_fitness_ui()
```

**Returns:** Dictionary with component functions

---

### 2. `render_profile_setup()`

Shows user profile form in sidebar with:
- Age, weight, height, sex
- Fitness level (beginner/intermediate/advanced)
- Health limitations (multi-select)
- Available equipment (multi-select)
- Save and Export buttons

**Usage:**
```python
from health_butler.ui_streamlit.fitness_components import render_profile_setup

profile = render_profile_setup()
if profile:
    st.session_state['user_profile'] = profile
```

---

### 3. `render_goal_dashboard()`

Displays active goals in sidebar with:
- Progress bars
- Status indicators (🟢 on track, 🟡 behind)
- Days remaining
- Update progress controls

**Auto-called by `integrate_fitness_ui()`**

---

### 4. `render_exercise_completion_tracker()`

Allows users to log completed exercises:
- Category selection (Cardio, Strength, Flexibility, Sports, Daily)
- Exercise dropdown
- Duration input
- "Log Activity" button
- Shows top 5 preferred activities

**Usage:**
```python
# After fitness recommendations
render_exercise_completion_tracker()
```

---

### 5. `render_goal_creation_form()`

Form to create new SMART goals:
- Goal type (weight loss, muscle gain, endurance, consistency)
- Description
- Target value and unit
- Deadline (weeks from now)

**Usage:**
```python
with st.expander("Create Goal"):
    render_goal_creation_form()
```

---

## Session State Variables

The fitness UI uses these session state keys:

- `user_profile`: UserProfile object (loaded/saved automatically)
- `last_exercise`: Last logged exercise name
- `messages`: Chat history (existing)

---

## Styling Tips

### Custom Colors
```python
# Add to your app after st.set_page_config()
st.markdown("""
<style>
    .stProgress > div > div > div {
        background-color: #00cc66;  /* Green progress bar */
    }
</style>
""", unsafe_allow_html=True)
```

### Goal Card Styling
```python
# Goals automatically use emojis and compact layout
# Customize with st.markdown in custom CSS
```

---

## Testing the Integration

### Test 1: Profile Creation
1. Click "User Profile" in sidebar
2. Fill in age, weight, limitations
3. Click "Save Profile"
4. Check `~/.health_butler/user_profile.json` created

### Test 2: Goal Setting
1. Expand "Create New Goal"
2. Enter "Lose 5kg in 8 weeks"
3. Click "Create Goal"
4. See goal appear in dashboard

### Test 3: Exercise Logging
1. After getting fitness recommendation
2. Select exercise category and type
3. Enter duration
4. Click "Log Activity"
5. See preference count increment

### Test 4: Full Workflow
1. Upload meal image
2. Get nutrition + fitness recommendations
3. Log an exercise
4. Check goal progress
5. Verify profile updated

---

## Troubleshooting

### Profile not loading?
```python
# Check if file exists
from pathlib import Path
profile_path = Path.home() / ".health_butler" / "user_profile.json"
print(f"Profile exists: {profile_path.exists()}")
```

### Goals not showing?
```python
# Check if goals are in profile
from health_butler.data.user_profiles import get_user_profile
profile = get_user_profile()
print(f"Active goals: {len(profile.active_goals)}")
```

### Exercise tracking not working?
```python
# Verify session state
print(st.session_state.user_profile.exercise_preferences)
```

---

## Next Steps

1. **Add More Exercise Categories**: Edit `exercise_categories` dict in `fitness_components.py`
2. **Custom Goal Types**: Add to `goal_type` selectbox options
3. **Progress Charts**: Use st.line_chart() to visualize goal progress over time
4. **Export Data**: Add CSV export for exercise history

---

**Created**: February 5, 2026  
**Module**: `health_butler/ui_streamlit/fitness_components.py`  
**Dependencies**: streamlit, health_butler.data.user_profiles
