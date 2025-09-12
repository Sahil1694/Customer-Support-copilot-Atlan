Atlan Customer Support Copilot
Live Application Link: [INSERT YOUR DEPLOYED STREAMLIT URL HERE]

1. Project Overview
This project is a functional prototype of an AI-powered Customer Support Copilot designed to assist Atlan's support team. The application leverages a sophisticated AI pipeline to automate the triage, classification, and response generation for customer support tickets.

The system is demonstrated through a "dummy helpdesk" interface built with Streamlit, which showcases two core functionalities: a bulk classification dashboard for an entire support queue and a real-time interactive agent for handling new, incoming tickets.

2. Core Features
📊 Bulk Ticket Classification Dashboard:

On startup, the application ingests a queue of sample tickets from a JSON file.

Each ticket is displayed alongside its AI-generated classification, including:

Topic Tags: (e.g., Connector, Lineage, API/SDK)

Sentiment: (e.g., Frustrated, Curious, Angry)

Priority: (e.g., P0 (High), P1 (Medium), P2 (Low))

🤖 Interactive AI Agent:

Provides a real-time interface to submit new customer queries.

Transparent AI Analysis: Clearly displays the AI's internal classification ("back-end view") for the new ticket.

Intelligent Response Generation:

For knowledge-based topics (How-to, Product, API/SDK, etc.), it uses a Retrieval-Augmented Generation (RAG) pipeline to provide direct answers based on Atlan's official documentation.

For complex or bug-related topics (Connector, Troubleshooting, etc.), it intelligently routes the ticket, informing the user that it has been classified and escalated.

Cited Sources: All RAG-generated answers include a list of the source URLs used, ensuring transparency and trustworthiness.

3. Architecture Diagram
The application follows a self-contained architecture where Streamlit manages both the UI and the backend AI logic. The core pipeline is divided into two main workflows:

graph TD
    subgraph User Interaction
        User[👤 User / Evaluator]
    end

    subgraph Application on Streamlit Cloud
        App[ streamlit run app.py ]
    end

    subgraph AI Pipeline Logic
        Classifier[🧠 Gemini 1.5 Flash Classifier]
        RAG[🚀 RAG Pipeline]
    end
    
    subgraph Data Layer
        Tickets[📄 classified_tickets.json]
        KB[📚 ChromaDB Vector Store <br/> (Atlan Docs)]
    end

    User --> App;
    App -- On Load --> Tickets;
    App -- On New Query --> Classifier;
    Classifier --> App;
    App -- If RAG Topic --> RAG;
    RAG -- Retrieves --> KB;
    RAG -- Generates --> Classifier;

4. Tech Stack & Design Decisions
Application Framework: Streamlit

Decision: Chosen for its ability to rapidly develop interactive data and AI applications purely in Python. It allows the focus to remain on the AI pipeline rather than complex front-end development.

Trade-off: While not designed for massive-scale production use like a dedicated web framework, it is the perfect tool for creating a high-fidelity, functional prototype for demonstration purposes.

Core LLM: Google Gemini 1.5 Flash

Decision: Selected for its excellent performance in multi-task instructions (classification) and generation, its large context window, and its cost-effectiveness. The flash model provides a great balance of speed and capability.

Knowledge Base & RAG:

Vector Database: ChromaDB: Chosen as a modern, persistent vector store that is easy to manage and integrates seamlessly with LangChain. It is more robust for this use case than a simple in-memory store like FAISS.

Embedding Model: all-MiniLM-L6-v2: A high-performance, open-source sentence-transformer model that is fast, efficient, and runs locally without API calls, making it ideal for converting text chunks into meaningful embeddings.

Re-ranking Model: cross-encoder/ms-marco-MiniLM-L-6-v2: A critical component for accuracy. A re-ranking step was added to the RAG pipeline to significantly improve the quality of retrieved documents. It takes a larger initial set of documents from ChromaDB and re-orders them based on true semantic relevance to the query, ensuring the LLM receives the best possible context.

Key Engineering Decision: Pre-computation

Decision: To avoid hitting API rate limits on the free tier, a one-time script (precompute_classifications.py) was created to process the bulk tickets. The main application loads this pre-computed JSON file.

Benefit: This makes the dashboard load instantly, improves the user experience, and completely solves the rate-limiting issue, ensuring the application is robust for demonstration.

5. How to Run Locally
Clone the Repository:

git clone <your-repo-url>
cd backend

Set up a Python Virtual Environment:

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

Install Dependencies:

pip install -r requirements.txt

Set Up Environment Variables:

Create a file named .env in the backend/ directory.

Add your Google API key to this file:

GOOGLE_API_KEY="your_api_key_here"

Build the Knowledge Base (One-Time Setup):

Run the scraping script to gather the documentation:

python -m scripts.build_knowledge_base

Run the vector store script to chunk and embed the content:

python -m scripts.build_vector_store

Pre-compute the Classifications (One-Time Setup):

Run the pre-computation script to avoid rate limits on the dashboard:

python -m scripts.precompute_classifications

Run the Streamlit Application:

streamlit run app.py

The application should now be running in your browser.