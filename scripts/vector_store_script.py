import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- Configuration ---
KNOWLEDGE_BASE_PATH = "data/knowledge_base.json"
# Updated save path to be specific to ChromaDB
VECTOR_STORE_SAVE_PATH = "data/chroma_db"

# Configuration for the text splitter
CHUNK_SIZE = 1000  # The number of characters in each chunk
CHUNK_OVERLAP = 100 # The number of characters to overlap between chunks

# We will use a powerful, open-source embedding model.
# "all-MiniLM-L6-v2" is a great starting point - it's fast and effective.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# --- Core Logic ---

def load_knowledge_base(filepath: str) -> list:
    """Loads the scraped data from the JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def create_documents_from_data(data: list) -> list:
    """Converts the raw data into LangChain's Document format."""
    documents = [
        Document(page_content=item['content'], metadata={'source': item['url']})
        for item in data if item.get('content')
    ]
    return documents

def split_documents(documents: list) -> list:
    """Splits the documents into smaller chunks using the recursive strategy."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )
    chunked_documents = text_splitter.split_documents(documents)
    return chunked_documents

def build_and_save_vector_store(chunks: list, save_path: str):
    """
    Creates embeddings for the chunks and builds a ChromaDB vector store,
    then saves it to disk.
    """
    if not chunks:
        return

    # Initialize the embedding model. It might download the model files on the first run.
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # Chroma will automatically create and save the database in the specified directory.
    # The `persist_directory` argument tells Chroma to save the data to disk.
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=save_path
    )

# --- Main Execution ---

if __name__ == "__main__":
    # 1. Load the raw scraped data
    scraped_data = load_knowledge_base(KNOWLEDGE_BASE_PATH)

    if scraped_data:
        # 2. Convert to LangChain Documents
        documents = create_documents_from_data(scraped_data)

        # 3. Split the documents into chunks
        chunked_docs = split_documents(documents)

        # 4. Build and save the vector store
        build_and_save_vector_store(chunked_docs, VECTOR_STORE_SAVE_PATH)

