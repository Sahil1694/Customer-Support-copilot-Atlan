from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- Configuration ---
# This MUST match the path where you saved the database
VECTOR_STORE_SAVE_PATH = "data/chroma_db"

# This MUST match the embedding model you used to build the database
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# --- Main Test Execution ---

if __name__ == "__main__":
    print("🚀 Starting Vector Store Test...")

    # 1. Initialize the same embedding model
    print("🧠 Initializing embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # 2. Load the persistent vector store from disk
    print(f"📚 Loading vector store from '{VECTOR_STORE_SAVE_PATH}'...")
    try:
        vector_store = Chroma(
            persist_directory=VECTOR_STORE_SAVE_PATH,
            embedding_function=embeddings
        )
        print("✅ Vector store loaded successfully!")
    except Exception as e:
        print(f"🚨 Failed to load vector store: {e}")
        exit()

    # 3. Define a sample query to test the retriever
    # This query is based on the sample data you provided earlier.
    sample_query = "How do I add a resource or link to an existing asset?"
    print(f"\n❓ Performing similarity search for query: '{sample_query}'")

    # 4. Perform the similarity search
    # The `similarity_search` method returns a list of Document objects.
    # By default, it returns the top 4 most relevant results.
    try:
        search_results = vector_store.similarity_search(sample_query)
        if not search_results:
            print("⚠️ Search returned no results.")
        else:
            print(f"✅ Found {len(search_results)} relevant chunks.")
    except Exception as e:
        print(f"🚨 An error occurred during search: {e}")
        exit()
    
    # 5. Print the results for inspection
    print("\n--- Top Search Results ---")
    for i, doc in enumerate(search_results):
        print(f"\n--- Result {i+1} ---")
        print(f"**Source URL:** {doc.metadata.get('source', 'N/A')}")
        print("\n**Content:**")
        print(doc.page_content)
        print("-" * 20)

    print("\n✨ Test complete!")
