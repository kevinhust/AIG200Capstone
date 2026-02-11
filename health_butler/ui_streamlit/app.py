import streamlit as st
import sys
import os
from pathlib import Path
import tempfile

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import Swarm
try:
    from health_butler.swarm import HealthSwarm
except ImportError as e:
    st.error(f"Failed to import HealthSwarm: {e}")
    st.stop()

# Page Config
st.set_page_config(
    page_title="Personal Health Butler AI",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .agent-thought {
        font-size: 0.8rem;
        color: #666;
        border-left: 2px solid #ccc;
        padding-left: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Swarm (Cached per session)
if "swarm" not in st.session_state:
    with st.spinner("Waking up the Agent Swarm..."):
        # Initialize swarm with verbose logging
        st.session_state.swarm = HealthSwarm(verbose=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.title("Health Butler 🤖")
    st.caption("Powered by Antigravity Swarm")
    
    st.markdown("### Active Agents")
    st.success("🧭 Coordinator")
    st.success("🥗 Nutrition")
    st.success("🏃 Fitness")
    
    st.markdown("---")
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.session_state.swarm.reset()
        st.rerun()

# Main Interface
st.title("Personal Health Butler")
st.markdown("Upload a meal photo or describe your day. I'll analyze nutrition and suggest workouts.")

# 1. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "image" in msg:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])
        
        # Show agent details if available
        if "delegations" in msg:
            with st.expander("See Agent Reasoning"):
                for d in msg["delegations"]:
                    st.markdown(f"**{d['agent'].capitalize()}**: {d['task']}")
                if "logs" in msg:
                    for log in msg["logs"]:
                        st.text(f"{log['from']} -> {log['to']}: {log['type']}")

# 2. Input Handling
uploaded_file = st.file_uploader("📸 Snap a meal", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
user_input = st.chat_input("Type a message...")

# Logic Trigger
if user_input or uploaded_file:
    # Determine input type
    image_path = None
    prompt = user_input
    
    # Handle Image
    if uploaded_file:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(uploaded_file.getbuffer())
            image_path = tmp.name
        
        # If no text provided with image, use default prompt
        if not prompt:
            prompt = "Analyze this meal and give me advice."
            
        # Display User Message
        with st.chat_message("user"):
            st.image(uploaded_file, width=300)
            st.markdown(prompt)
        
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt, 
            "image": uploaded_file
        })
    else:
        # Text only
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. Swarm Execution
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        status = st.status("🧠 Swarm is thinking...", expanded=True)
        
        try:
            # Execute Swarm
            status.write("🧭 Coordinator analyzing intent...")
            
            # We assume swarm.execute is synchronous for now. 
            # In a real async setup, we'd poll for updates.
            result = st.session_state.swarm.execute(
                user_input=prompt,
                image_path=image_path
            )
            
            # Visualize Steps based on logs
            delegations = result.get("delegations", [])
            logs = result.get("message_log", [])
            
            for d in delegations:
                status.write(f"👉 Delegated to **{d['agent'].capitalize()} Agent**")
                
            # Check for specific agent activities in logs
            agent_activities = set()
            for log in logs:
                if log['from'] in ['nutrition', 'fitness'] and log['type'] == 'result':
                    agent_activities.add(log['from'])
            
            if 'nutrition' in agent_activities:
                status.write("🥗 Nutrition analysis complete")
            if 'fitness' in agent_activities:
                status.write("🏃 Fitness plan generated")
            
            status.update(label="Response Ready!", state="complete", expanded=False)
            
            # Display Final Response
            final_response = result["response"]
            response_placeholder.markdown(final_response)
            
            # Save to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "delegations": delegations,
                "logs": logs
            })
            
        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Swarm encountered an error: {e}")
            
    # Cleanup temp file
    if image_path:
        os.unlink(image_path)
