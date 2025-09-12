import os
import json
import google.generativeai as genai
from typing import Dict, Any, List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from .prompts import RAG_PROMPT_TEMPLATE

# --- Configuration ---
VECTOR_STORE_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "data/knowledge_base.json")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Configure the Gemini API key
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")
genai.configure(api_key=api_key)


class RAGPipeline:
    """
    A class to handle the Retrieval-Augmented Generation pipeline.
    It loads the vector store once and can be used to answer multiple queries.
    """
    def __init__(self):
        self.vector_store = self._load_vector_store()
        self.llm = genai.GenerativeModel('gemini-2.5-flash')
        
    def query(self, question: str, context: str = "") -> str:
        """
        Query the RAG pipeline with a question and optional context.
        This is the main interface method used by the UI.
        """
        try:
            # If context is provided, we can incorporate it into the question
            if context:
                enhanced_question = f"{question}\n\nAdditional context: {context}"
            else:
                enhanced_question = question
                
            # Get answer from RAG
            result = self.get_rag_answer(enhanced_question)
            
            # Handle potential errors
            if "error" in result:
                return f"I encountered an issue while processing your request: {result['error']}"
                
            return result["answer"]
        except Exception as e:
            return f"I'm sorry, I encountered an error while processing your question: {str(e)}"


    def _ensure_local_vector_store(self) -> None:
        """
        Build the local Chroma vector store from the knowledge base if it doesn't exist.
        This is intended for simple POC deployments where we don't ship large artifacts.
        """
        # If the directory already exists and is non-empty, assume it's usable
        if os.path.isdir(VECTOR_STORE_PATH) and any(os.scandir(VECTOR_STORE_PATH)):
            return

        # If knowledge base doesn't exist, nothing to build
        if not os.path.isfile(KNOWLEDGE_BASE_PATH):
            return

        try:
            with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
        except Exception:
            kb_data = []

        if not kb_data:
            return

        # Convert to Documents
        documents: List[Document] = [
            Document(page_content=item.get('content', ''), metadata={'source': item.get('url', '')})
            for item in kb_data
            if item.get('content')
        ]
        if not documents:
            return

        # Split documents
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(documents)
        if not chunks:
            return

        # Build and persist vector store
        os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=VECTOR_STORE_PATH
        )

    def _load_vector_store(self):
        """Loads the ChromaDB vector store from the specified path. Builds it if missing (POC)."""
        # Ensure the store exists for POC flows
        self._ensure_local_vector_store()

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        try:
            return Chroma(
                persist_directory=VECTOR_STORE_PATH,
                embedding_function=embeddings
            )
        except Exception:
            return None

    def get_rag_answer(self, question: str) -> Dict[str, Any]:
        """
        Retrieves relevant context, generates an answer using the LLM,
        and returns the answer along with the sources.
        """
        if self.vector_store is None:
            return {"error": "Vector store is not available."}
        
        # 1. Retrieve relevant documents (context)
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 8})
        relevant_docs = retriever.invoke(question)

        if not relevant_docs:
            return {
                "answer": "I do not have enough information to answer this question based on the available knowledge base. Please try rephrasing your question or contact our support team for assistance.",
                "sources": []
            }
            
        # 2. Format the context and prompt
        # Prefer Atlan official domains first when building sources
        def source_key(doc):
            src = (doc.metadata.get('source', '') or '').lower()
            if 'docs.atlan.com' in src or 'developer.atlan.com' in src:
                return (0, src)
            return (1, src)

        # Sort docs to prioritize official domains without losing content
        sorted_docs = sorted(relevant_docs, key=source_key)
        context_str = "\n\n".join([doc.page_content for doc in sorted_docs])
        prompt = RAG_PROMPT_TEMPLATE.format(context=context_str, question=question)

        # 3. Generate the answer using the LLM
        try:
            response = self.llm.generate_content(prompt)
            
            # 4. Extract and format sources
            sources = []
            for doc in sorted_docs:
                source_url = doc.metadata.get('source', 'N/A')
                if source_url != 'N/A' and source_url not in sources:
                    sources.append(source_url)
            
            # 5. Format the response with proper source citations without duplication
            answer_text = response.text or ""

            # Normalize and de-duplicate sources
            unique_sources = []
            for s in sources:
                if s and s not in unique_sources:
                    unique_sources.append(s)
            
            return {
                "answer": answer_text,
                "sources": unique_sources[:5],
                "context_used": len(relevant_docs)
            }
        except Exception as e:
            return {"error": f"Failed to generate an answer from the LLM: {str(e)}"}
