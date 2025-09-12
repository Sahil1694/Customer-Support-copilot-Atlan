import os
import json
import google.generativeai as genai
from typing import Dict, Any

# Import the prompt template from the separate prompts file
from pipeline.prompts import CLASSIFICATION_PROMPT

# --- Part 1: Configuration ---

# Configure the Gemini API key from environment variables
# This setup allows the app to run both locally (with a .env file)
# and in a deployed environment (like Streamlit Community Cloud)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # This is fine if dotenv is not installed, especially in deployed environments
    pass

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Please create a .env file and set it.")
genai.configure(api_key=api_key)


# --- Part 2: Core Classification Logic ---

def _clean_llm_response(response_text: str) -> str:
    """
    Private helper function to clean the LLM's raw response.
    It removes markdown code fences and leading/trailing whitespace,
    making the string more reliable for JSON parsing.
    """
    cleaned_text = response_text.strip().replace("```json", "").replace("```", "")
    return cleaned_text.strip()

def classify_ticket(ticket_text: str) -> Dict[str, Any]:
    """
    Takes a ticket text string, calls the Gemini LLM for classification,
    and returns a structured Python dictionary.

    This is the primary function that will be imported and used by the main app.py.
    """
    if not ticket_text:
        return {"error": "Input ticket text cannot be empty."}

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = CLASSIFICATION_PROMPT.format(ticket_text=ticket_text)
        
        response = model.generate_content(prompt)
        
        cleaned_response = _clean_llm_response(response.text)
        classification = json.loads(cleaned_response)
        
        # Validate that the response contains the keys we expect
        required_keys = ["topic_tags", "sentiment", "priority"]
        if not all(key in classification for key in required_keys):
            raise ValueError(f"LLM response is missing one or more required keys. Got: {classification.keys()}")

        return classification

    except json.JSONDecodeError:
        # This handles cases where the LLM returns a non-JSON string
        raw_response = response.text if 'response' in locals() else "N/A"
        return {
            "error": "Failed to decode JSON from LLM response.",
            "raw_response": raw_response
        }
    except Exception as e:
        # This catches other potential errors (API issues, etc.)
        return {
            "error": f"An unexpected error occurred: {str(e)}"
        }

# --- Part 3: Standalone Execution for Bulk Processing ---

# The `if __name__ == "__main__":` block allows this script to be run directly
# from the command line. This is useful for performing the initial bulk
# classification of the sample tickets before running the main Streamlit app.

if __name__ == "__main__":
    # Note: These paths assume you are running the script from the `backend/` directory.
    # python -m pipeline.classifier
    input_filename = "data/sample_tickets.json"
    output_filename = "data/classified_tickets.json"

    try:
        with open(input_filename, 'r') as f:
            all_tickets = json.load(f)
    except FileNotFoundError:
        exit()
    except json.JSONDecodeError:
        exit()

    classification_results = []
    for i, ticket in enumerate(all_tickets, 1):
        ticket_id = ticket.get('id', 'N/A')
        
        ticket_body = ticket.get("body")
        if not ticket_body:
            continue
            
        result = classify_ticket(ticket_body)
        
        classified_ticket = ticket.copy()
        classified_ticket['classification'] = result
        
        classification_results.append(classified_ticket)

    try:
        with open(output_filename, 'w') as f:
            json.dump(classification_results, f, indent=4)
    except Exception as e:
        pass