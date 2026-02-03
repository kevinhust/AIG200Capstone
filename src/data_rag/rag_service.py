import os
from typing import List, Dict
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from dotenv import load_dotenv

# Robustly load .env from project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
env_path = os.path.join(project_root, ".env")

if os.path.exists(env_path):
    load_dotenv(env_path)

# Manual fallback if load_dotenv fails (e.g. issues with parsing)
if not os.getenv("GOOGLE_API_KEY"):
    try:
        with open(env_path, 'r') as f:
            for line in f:
                if "GOOGLE_API_KEY" in line:
                    key = line.split('=')[1].strip().strip('"').strip("'")
                    os.environ["GOOGLE_API_KEY"] = key
    except Exception:
        pass

class RAGService:
    """
    RAG Service using FAISS and Google Gemini.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("WARNING: GOOGLE_API_KEY not found in environment.")
        
        # Initialize Embeddings (Local to avoid quota limits)
        # Using a small, efficient model suitable for CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Initialize LLM
        # Using gemini-pro as it is widely available. 
        # If gemini-1.5-flash failed, pro is a safer fallback for MVP.
        self.llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", google_api_key=self.api_key, temperature=0.3)
        
        # Initialize Vector Store (In-memory or load from disk)
        self.vector_store = self._initialize_vector_store()

    def _initialize_vector_store(self):
        """
        Initializes the FAISS vector store. 
        Populates with sample data for MVP if no persistence is found.
        """
        # Sample data for MVP Knowledge Base
        texts = [
            "Grilled chicken breast is a low-fat source of protein, essential for muscle repair.",
            "Broccoli contains sulforaphane, a compound that may have anti-cancer properties.",
            "Pizza can be high in refined carbs and saturated fats, best consumed in moderation.",
            "Salmon provides omega-3 fatty acids which support heart and brain health.",
            "Oats are a great source of soluble fiber which can help lower cholesterol.",
            "Spinach is rich in iron and calcium, though the iron is non-heme.",
            "Avocado contains healthy monounsaturated fats and potassium."
        ]
        docs = [Document(page_content=t, metadata={"source": "MVP_KB"}) for t in texts]
        
        try:
            print("Initializing FAISS Vector Store...")
            return FAISS.from_documents(docs, self.embeddings)
        except Exception as e:
            print(f"Error initializing FAISS: {e}")
            return None

    def retrieve_info(self, query: str, k: int = 2) -> List[Dict]:
        """
        Retrieves relevant information for the query.
        """
        if not self.vector_store:
            return []
            
        try:
            docs = self.vector_store.similarity_search_with_score(query, k=k)
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown"),
                    "score": float(score) 
                })
            return results
        except Exception as e:
            print(f"Error retrieving info: {e}")
            return []

    def generate_advice(self, food_items: List[Dict], user_query: str = "") -> str:
        """
        Generates nutrition advice based on food items and retrieved context.
        """
        if not self.api_key:
            return "Error: GOOGLE_API_KEY is missing. Cannot generate advice."

        food_names = [item['name'] for item in food_items]
        foods_str = ", ".join(food_names)
        
        # 1. Retrieve context for each food
        context_parts = []
        for food in food_names:
            results = self.retrieve_info(food)
            for res in results:
                # Deduplicate roughly
                if res['content'] not in context_parts:
                    context_parts.append(res['content'])
        
        context_str = "\n".join(context_parts)
        
        # 2. Generate with LLM
        template = """
        You are a helpful Nutrition Assistant.
        Based on the following detected foods: {foods}
        And the following nutritional context from our database:
        {context}
        
        User Question: {query}
        
        Please provide a concise nutritional analysis and advice. 
        If specific context is missing, use your general knowledge but mention that it's general advice.
        """
        
        prompt = PromptTemplate(template=template, input_variables=["foods", "context", "query"])
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "foods": foods_str,
                "context": context_str,
                "query": user_query if user_query else "Is this a healthy meal?"
            })
            
            content = response.content
            # Handle case where content is a list of parts (e.g. Gemni 1.5/3 multimodal output)
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    elif isinstance(part, str):
                        text_parts.append(part)
                return "\n".join(text_parts)
                
            return str(content)
        except Exception as e:
            return f"Error generating advice: {e}"
