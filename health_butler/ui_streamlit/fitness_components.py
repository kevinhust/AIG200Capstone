"""
Streamlit UI components for Fitness Agent features.

Provides:
- User profile setup form
- Goal dashboard widget
- Exercise completion tracker
- Profile export/import functionality
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import uuid

from health_butler.data.user_profiles import (
    UserProfile,
    FitnessGoal,
    get_user_profile,
    save_user_profile
)


def render_profile_setup() -> Optional[UserProfile]:
    """
    Render user profile setup form in sidebar or modal.
    
    Returns:
        UserProfile if successfully loaded/created, None otherwise
    """
    with st.sidebar:
        with st.expander("👤 User Profile", expanded=False):
            st.markdown("### Personal Health Info")
            
            # Try to load existing profile
            try:
                existing_profile = get_user_profile()
                has_profile = True
            except:
                existing_profile = UserProfile.create_default()
                has_profile = False
            
            # Form fields with defaults from existing profile
            age = st.number_input(
                "Age (years)",
                min_value=13,
                max_value=120,
                value=existing_profile.age,
                help="Your current age"
            )
            
            weight = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=300.0,
                value=float(existing_profile.weight_kg),
                step=0.5,
                help="Your current weight in kilograms"
            )
            
            height = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=250.0,
                value=float(existing_profile.height_cm) if existing_profile.height_cm else 170.0,
                step=0.5,
                help="Your height in centimeters (optional)"
            )
            
            sex = st.selectbox(
                "Sex",
                options=["male", "female", "other"],
                index=["male", "female", "other"].index(existing_profile.sex) if existing_profile.sex else 0,
                help="Biological sex (affects calorie calculations)"
            )
            
            fitness_level = st.selectbox(
                "Fitness Level",
                options=["beginner", "intermediate", "advanced"],
                index=["beginner", "intermediate", "advanced"].index(existing_profile.fitness_level),
                help="Your current fitness level"
            )
            
            # Health limitations (multi-select)
            limitation_options = [
                "knee_injury",
                "ankle_injury",
                "back_injury",
                "heart_disease",
                "high_blood_pressure",
                "diabetes",
                "asthma",
                "severe_obesity",
                "osteoporosis",
                "herniated_disc"
            ]
            
            limitations = st.multiselect(
                "Health Limitations",
                options=limitation_options,
                default=existing_profile.health_limitations,
                help="Select any health conditions that affect your exercise choices"
            )
            
            # Available equipment
            equipment_options = [
                "none (bodyweight only)",
                "home (basic equipment)",
                "gym (full equipment)",
                "pool (swimming)",
                "outdoor (trails/parks)"
            ]
            
            equipment_selected = st.multiselect(
                "Available Equipment",
                options=equipment_options,
                default=[eq for eq in equipment_options if any(
                    existing_eq in eq for existing_eq in existing_profile.available_equipment
                )],
                help="What equipment/facilities do you have access to?"
            )
            
            # Parse equipment back to simple format
            equipment = []
            for eq in equipment_selected:
                if "none" in eq:
                    equipment.append("none")
                elif "home" in eq:
                    equipment.append("home")
                elif "gym" in eq:
                    equipment.append("gym")
                elif "pool" in eq:
                    equipment.append("pool")
                elif "outdoor" in eq:
                    equipment.append("outdoor")
            
            if not equipment:
                equipment = ["none"]
            
            # Save button
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Profile", use_container_width=True):
                    new_profile = UserProfile(
                        age=age,
                        weight_kg=weight,
                        height_cm=height if height > 0 else None,
                        sex=sex,
                        fitness_level=fitness_level,
                        health_limitations=limitations,
                        available_equipment=equipment,
                        # Preserve existing goals and preferences
                        fitness_goals=existing_profile.fitness_goals,
                        exercise_preferences=existing_profile.exercise_preferences
                    )
                    
                    save_user_profile(new_profile)
                    st.success("✅ Profile saved!")
                    st.session_state['user_profile'] = new_profile
                    return new_profile
            
            with col2:
                if st.button("💾 Export", use_container_width=True):
                    export_path = Path.home() / "Downloads" / f"health_profile_{datetime.now().strftime('%Y%m%d')}.json"
                    existing_profile.export_json(export_path)
                    st.success(f"Exported to {export_path.name}")
            
            # Display current profile info
            if has_profile:
                st.markdown("---")
                st.markdown("**Current Profile:**")
                st.caption(f"Age: {existing_profile.age} | Weight: {existing_profile.weight_kg}kg")
                if existing_profile.bmi:
                    st.caption(f"BMI: {existing_profile.bmi}")
                if existing_profile.health_limitations:
                    st.caption(f"⚠️ Limitations: {', '.join(existing_profile.health_limitations[:2])}")
            
            return existing_profile if has_profile else None


def render_goal_dashboard():
    """
    Render fitness goals dashboard in sidebar.
    Shows progress bars, status, and days remaining for active goals.
    """
    # Load user profile
    try:
        profile = st.session_state.get('user_profile') or get_user_profile()
    except:
        return
    
    active_goals = profile.active_goals
    
    if not active_goals:
        return
    
    with st.sidebar:
        st.markdown("### 🎯 Your Fitness Goals")
        
        for goal in active_goals[:3]:  # Show max 3 goals
            # Status emoji
            status_emoji = "🟢" if goal.is_on_track else "🟡"
            
            # Goal container
            with st.container():
                st.markdown(f"{status_emoji} **{goal.description[:40]}...**" if len(goal.description) > 40 else f"{status_emoji} **{goal.description}**")
                
                # Progress bar
                progress = goal.progress_percent / 100.0
                st.progress(progress)
                
                # Details in columns
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📊 {goal.current_value}/{goal.target_value} {goal.unit}")
                with col2:
                    st.caption(f"📅 {goal.days_remaining} days left")
                
                # Update progress button
                with st.expander(f"Update Progress for {goal.goal_id[:8]}..."):
                    new_value = st.number_input(
                        f"Current {goal.unit}",
                        min_value=0.0,
                        value=float(goal.current_value),
                        step=0.1,
                        key=f"goal_update_{goal.goal_id}"
                    )
                    
                    if st.button("Update", key=f"btn_{goal.goal_id}"):
                        goal.update_progress(new_value)
                        save_user_profile(profile)
                        st.success("Progress updated!")
                        st.rerun()
                
                st.markdown("---")


def render_exercise_completion_tracker():
    """
    Render exercise completion tracker below fitness recommendations.
    Allows users to mark exercises as completed for preference learning.
    """
    st.markdown("### ✅ Track Your Activity")
    
    # Common exercises
    exercise_categories = {
        "🏃 Cardio": ["Walking", "Running", "Cycling", "Swimming", "Jogging", "Elliptical"],
        "💪 Strength": ["Weight Lifting", "Push-ups", "Pull-ups", "Sit-ups", "Gym Session"],
        "🧘 Flexibility": ["Yoga", "Pilates", "Stretching", "Tai Chi"],
        "⚽ Sports": ["Basketball", "Tennis", "Soccer", "Golf", "Dancing"],
        "🏠 Daily": ["Stairs", "Gardening", "Housework", "Shopping Walk"]
    }
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Category selection
        selected_category = st.selectbox(
            "Activity Category",
            options=list(exercise_categories.keys()),
            label_visibility="collapsed"
        )
        
        # Exercise selection within category
        selected_exercise = st.selectbox(
            "Exercise",
            options=exercise_categories[selected_category],
            label_visibility="collapsed"
        )
    
    with col2:
        # Duration input
        duration = st.number_input(
            "Minutes",
            min_value=1,
            max_value=300,
            value=30,
            step=5
        )
    
    # Log button
    if st.button("📝 Log Activity", type="primary", use_container_width=True):
        try:
            profile = st.session_state.get('user_profile') or get_user_profile()
            profile.increment_exercise_preference(selected_exercise)
            save_user_profile(profile)
            
            # Get preference count
            count = profile.exercise_preferences.get(selected_exercise.lower().replace(" ", "_"), 1)
            
            st.success(f"✅ Logged {duration} min of {selected_exercise}! (Session #{count})")
            
            # Update session state
            st.session_state['user_profile'] = profile
            st.session_state['last_exercise'] = selected_exercise
            
        except Exception as e:
            st.error(f"Error logging activity: {e}")
    
    # Show recent activities
    try:
        profile = st.session_state.get('user_profile') or get_user_profile()
        top_prefs = profile.get_top_preferences(5)
        
        if top_prefs:
            st.markdown("**Your Top Activities:**")
            cols = st.columns(5)
            for i, (exercise, count) in enumerate(top_prefs):
                with cols[i]:
                    st.metric(
                        label=exercise.replace("_", " ").title(),
                        value=f"{count}x"
                    )
    except:
        pass


def render_goal_creation_form():
    """
    Render goal creation form for setting new fitness goals.
    """
    st.markdown("### 🎯 Create a New Fitness Goal")
    
    with st.form("goal_creation_form"):
        goal_type = st.selectbox(
            "Goal Type",
            options=["weight_loss", "muscle_gain", "endurance", "consistency", "custom"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        description = st.text_input(
            "Goal Description",
            placeholder="e.g., Lose 5kg through regular exercise",
            help="Describe your fitness goal clearly"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_value = st.number_input(
                "Target Value",
                min_value=0.0,
                value=5.0,
                step=0.5,
                help="Numeric target (e.g., 5 for 5kg)"
            )
        
        with col2:
            unit = st.selectbox(
                "Unit",
                options=["kg", "lbs", "km", "miles", "days", "sessions", "minutes"],
                help="Unit of measurement"
            )
        
        weeks_to_deadline = st.slider(
            "Deadline (weeks from now)",
            min_value=1,
            max_value=52,
            value=8,
            help="How long to achieve this goal?"
        )
        
        submitted = st.form_submit_button("Create Goal", type="primary", use_container_width=True)
        
        if submitted:
            if not description:
                st.error("Please provide a goal description")
            else:
                try:
                    profile = st.session_state.get('user_profile') or get_user_profile()
                    
                    new_goal = FitnessGoal(
                        goal_id=str(uuid.uuid4()),
                        goal_type=goal_type,
                        description=description,
                        target_value=target_value,
                        unit=unit,
                        deadline=datetime.now() + timedelta(weeks=weeks_to_deadline)
                    )
                    
                    profile.add_goal(new_goal)
                    save_user_profile(profile)
                    
                    st.success(f"✅ Goal created! Deadline: {new_goal.deadline.strftime('%B %d, %Y')}")
                    st.session_state['user_profile'] = profile
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating goal: {e}")


# Main integration function for existing app.py
def integrate_fitness_ui():
    """
    Main integration function to add all fitness UI components.
    Call this from your Streamlit app.py main function.
    """
    # Initialize session state for user profile
    if 'user_profile' not in st.session_state:
        try:
            st.session_state['user_profile'] = get_user_profile()
        except:
            st.session_state['user_profile'] = None
    
    # Render sidebar components
    render_profile_setup()
    render_goal_dashboard()
    
    # Return functions for main app to use
    return {
        'profile_setup': render_profile_setup,
        'goal_dashboard': render_goal_dashboard,
        'exercise_tracker': render_exercise_completion_tracker,
        'goal_creator': render_goal_creation_form
    }


if __name__ == "__main__":
    # Standalone testing
    st.set_page_config(
        page_title="Fitness Agent UI Components",
        page_icon="💪",
        layout="wide"
    )
    
    st.title("💪 Fitness Agent UI Components - Demo")
    
    # Integrate UI
    integrate_fitness_ui()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["Exercise Tracker", "Goal Creator", "Profile Info"])
    
    with tab1:
        render_exercise_completion_tracker()
    
    with tab2:
        render_goal_creation_form()
    
    with tab3:
        st.markdown("### Profile Information")
        try:
            profile = get_user_profile()
            st.json(profile.to_dict())
        except:
            st.info("No profile found. Please create one in the sidebar.")
