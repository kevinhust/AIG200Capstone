**Subject:** Final Project Alignment: Multi-Agentic AI **Health Butler** - Group 5

**Dear Professor Amit,**

We are **Group 5** (Aziz, Wangchuk, Mingxuan, Zhihuai) from the AI Capstone course. We are writing to provide a final update on our project: **Health Butler**.

**Project Overview (Final Implementation):**
Our system has evolved into a professional, safety-first nutrition and fitness assistant integrated directly into **Discord**.

1.  **Hybrid Vision**: We've implemented a two-stage pipeline using **YOLOv8** for detection and **Gemini 2.5 Flash** for deep semantic analysis of food ingredients.
2.  **Safety RAG**: We've built an Enhanced RAG system that filters all advice against a curated database of health protocols (e.g., condition-specific contraindications).
3.  **Context-Aware Swarm**: Our agents now consume a 5-step user profile (Onboarding) and real-time calorie data to provide medical-grade personalized feedback.
- **Hybrid Vision Pipeline**: Uses YOLOv8 for physical food detection and Gemini 2.5 Flash for deep semantic constituent analysis.
- **Context-Aware Fitness**: Adapts routines in real-time based on calculated BMR (Mifflin-St Jeor) and current calorie balance.
- **Deployment**: A Discord-based interface deployed on GCP Cloud Run using Dockerized Swarm architecture.

**Tech Stack Summary:**

- **Agent Orchestration**: LangChain, AutoGen, or CrewAI.
- **Knowledge Base (RAG)**: Vector databases (Pinecone, FAISS, or Milvus) for storing vertical health data.
- **Core AI**: PyTorch, Hugging Face (Transformers, CLIP), OpenCV, YOLOv8.
- **Data**: Food-101, COCO-Pose, and curated vertical health datasets for the RAG pipeline .
- **Innovation**: Multi-agent collaborative reasoning; RAG for high-fidelity, private domain knowledge; multimodal data fusion .
