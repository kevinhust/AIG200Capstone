**Subject:** Proposal for Custom AI Capstone Project: Personal Health Butler AI - Group 5

**Dear Professor Amit,**

We are **Group 5** (Aziz, Wangchuk, Mingxuan, Zhihuai) from the AI Capstone course. We are writing to formally propose a custom project idea: **"Personal Health Butler AI."**

We have designed this project to address the common problem of "generic health advice" by building a deeply personalized, **Multi-Agent AI** system that integrates Computer Vision and RAG.

**Project Overview (MVP Scope):**
Our goal is to build an intelligent nutrition and fitness assistant that users can interact with naturally. The core workflow is:
1.  **Snap & Analyze**: User uploads a meal photo -> **AI Nutritionist Agent** (powered by **YOLO26**) detects food items and estimates calories/macros.
2.  **Verify**: The specific food data is cross-referenced with a **RAG Knowledge Base** (USDA/WHO data) to ensure accuracy.
3.  **Advise**: A **Coordinator Agent** synthesizes this analysis with the user's goals to provide instant, evidence-based dietary feedbacks and simple exercise suggestions (via a **Fitness Agent**).

**Technical Innovation & 2026 Tech Stack:**
To ensure this meets Capstone rigor, we are aggressively adopting 2026 industry standards:

-   **Multi-Agent Orchestration**: Using **LangGraph** to manage the cyclic workflow between diverse agents (Nutrition, Fitness, Coordinator).
-   **Computer Vision**: Fine-tuning **YOLO26** (latest edge-optimized model) on the Food-101 dataset for real-time food recognition.
-   **RAG Pipeline**: Using **FAISS** vector store with high-precision **e5-large** embeddings to retrieve trusted health protocols, strictly eliminating LLM hallucinations.
-   **LLM Intelligence**: leveraging **Gemini 2.5 Flash** for high-speed, cost-effective reasoning.
-   **Deployment**: A full containerized deployment on **GCP Cloud Run**.

**Feasibility:**
We have focused the scope specifically on **Nutrition & Diet** (excluding broad medical diagnosis) to ensuring we can deliver a high-quality, polished MVP within the 14-week timeline. We have structured the development into modular components (Data, CV, Agents, UI) to allow our 4-person team to work in parallel.

We believe this project combines sufficient technical complexity (Vision + NLP + Agents) with a realistic scope for a successful delivery.

We look forward to your approval and guidance.

Best regards,

**Group 5**
(Aziz Rahman, Tsering Wangchuk Sherpa, Mingxuan Li, Zhihuai Wang)
