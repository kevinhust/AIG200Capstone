import streamlit as st
import time
from PIL import Image
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import tools (Phase 2 Prototype)
# In Phase 3, we will import the CoordinatorAgent here.
try:
    from health_butler.cv_food_rec.vision_tool import VisionTool
    from health_butler.data_rag.rag_tool import RagTool
except ImportError as e:
    st.error(f"Failed to import core modules: {e}")
    st.stop()

# Page Config
st.set_page_config(
    page_title="Personal Health Butler AI",
    page_icon="🤖",
    layout="wide"
)

# Initialize Tools (Cached)
@st.cache_resource
def load_tools():
    vision = VisionTool()
    rag = RagTool()
    return vision, rag

try:
    with st.spinner("Initializing AI Core..."):
        vision_tool, rag_tool = load_tools()
except Exception as e:
    st.error(f"Failed to load AI models: {e}")
    st.stop()

# Sidebar
with st.sidebar:
    st.title("Health Butler AI 🍎")
    st.markdown("---")
    st.header("Debug Controls")
    
    if st.button("Reset Session"):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    st.info("Phase 2 Prototype\n- ViT Vision\n- ChromaDB RAG\n- Streamlit UI")

# Main Interface
st.title("Your Personal AI Health Assistant")
st.markdown("Upload a meal photo or ask a nutrition question.")

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image" in msg:
            st.image(msg["image"], width=300)

# Input Area
col1, col2 = st.columns([1, 4])

# Image Upload
uploaded_file = st.file_uploader("Upload Meal Photo", type=["jpg", "png", "jpeg"])
if uploaded_file and "last_processed_file" not in st.session_state:
    st.session_state.last_processed_file = None

# Logic when image is uploaded
if uploaded_file and uploaded_file != st.session_state.last_processed_file:
    # Save temp file
    temp_path = Path("temp.jpg")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Display User Message
    with st.chat_message("user"):
        st.image(uploaded_file, caption="Analyzing this meal...", width=300)
    st.session_state.messages.append({"role": "user", "content": "Analyze this meal.", "image": uploaded_file})
    
    # AI Response (Thinking)
    with st.chat_message("assistant"):
        status_container = st.status("Thinking...", expanded=True)
        
        # 1. Vision Analysis
        status_container.write("🔍 Scanning image with ViT...")
        vision_results = vision_tool.detect_food(str(temp_path))
        
        if vision_results and "label" in vision_results[0]:
            food_item = vision_results[0]["label"]
            confidence = vision_results[0]["confidence"]
            status_container.write(f"✅ Detected: **{food_item}** ({confidence:.1%})")
            
            # 2. RAG Lookup
            status_container.write(f"📚 Looking up nutrition for '{food_item}'...")
            rag_results = rag_tool.query(food_item, top_k=1)
            
            nutrition_info = "No specific nutrition data found."
            if rag_results:
                nutrition_info = rag_results[0]["text"]
                status_container.write("✅ Nutrition data retrieved.")
            
            status_container.update(label="Analysis Complete", state="complete", expanded=False)
            
            # Final Response
            response_text = f"I identified **{food_item}** in your photo.\n\nHere is the nutritional info I found:\n> {nutrition_info}\n\nWould you like a fitness recommendation for this meal?"
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
        else:
            status_container.update(label="Analysis Failed", state="error")
            st.error("Could not identify the food item.")
    
    st.session_state.last_processed_file = uploaded_file

# Text Input
if prompt := st.chat_input("Ask about nutrition or fitness..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        # For Phase 2, we just stick to RAG for questions
        # In Phase 3, this will go to CoordinatorAgent
        status = st.status("Searching knowledge base...", expanded=True)
        results = rag_tool.query(prompt)
        status.update(label="Complete", state="complete", expanded=False)
        
        if results:
            response = f"Based on your query, here is what I found:\n\n"
            for r in results:
                response += f"- {r['text']}\n"
        else:
            response = "I couldn't find relevant information in my database."
            
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
