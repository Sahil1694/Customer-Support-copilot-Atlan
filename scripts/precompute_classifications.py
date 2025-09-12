import os
import json
import time
from tqdm import tqdm
from pipeline.classifier import classify_ticket

# --- Configuration ---
INPUT_FILENAME = "data/sample_tickets.json"
OUTPUT_FILENAME = "data/classified_tickets.json"

# --- Main Execution ---

if __name__ == "__main__":
    print("🚀 Starting Ticket Classification Process (with rate limit handling)...")

    # 1. Read tickets from the input JSON file
    try:
        with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
            all_tickets = json.load(f)
        print(f"✅ Successfully loaded {len(all_tickets)} tickets from '{INPUT_FILENAME}'.")
    except FileNotFoundError:
        print(f"🚨 Error: Input file '{INPUT_FILENAME}' not found.")
        exit()
    except json.JSONDecodeError:
        print(f"🚨 Error: Could not decode JSON from '{INPUT_FILENAME}'.")
        exit()

    # 2. Classify each ticket with a delay and progress bar
    classification_results = []
    # tqdm creates a smart progress bar for the loop
    for ticket in tqdm(all_tickets, desc="Classifying Tickets"):
        ticket_body = ticket.get("body")
        if not ticket_body:
            continue

        # Call the classification function
        result = classify_ticket(ticket_body)

        # Combine original ticket info with the new classification
        classified_ticket = ticket.copy()
        classified_ticket['classification'] = result
        classification_results.append(classified_ticket)
        
        # --- THIS IS THE CRITICAL FIX ---
        # Wait for 4 seconds to stay under the 15 requests/minute free tier limit.
        time.sleep(4)

    # 3. Write the complete results to the output file
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(classification_results, f, indent=4)
        print(f"\n✨ Process complete. All classified tickets have been saved to '{OUTPUT_FILENAME}'.")
    except Exception as e:
        print(f"\n🚨 Error: Could not write results. Reason: {e}")

