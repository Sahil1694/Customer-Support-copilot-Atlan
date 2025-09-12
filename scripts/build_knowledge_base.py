import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---

# The starting points for our crawl.
START_URLS = [
    "https://docs.atlan.com/",
    "https://developer.atlan.com/"
]

# The path where the final scraped data will be saved.
SAVE_PATH = "data/knowledge_base.json"

# It's a good practice to identify your scraper with a User-Agent.
HEADERS = {
    'User-Agent': 'AtlanSupportCopilotBot/1.0'
}

# --- Core Logic ---

def get_all_links(base_url: str) -> set:
    """
    Crawls a starting URL to find all unique, same-domain links.
    """
    found_links = set()
    try:
        response = requests.get(base_url, headers=HEADERS)
        response.raise_for_status() # Raise an exception for bad status codes
        
        soup = BeautifulSoup(response.content, 'html.parser')
        base_domain = urlparse(base_url).netloc
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Create a full, absolute URL from a relative or absolute path
            full_url = urljoin(base_url, href)
            
            # Keep the link only if it belongs to the same domain
            if urlparse(full_url).netloc == base_domain:
                # Clean off any URL fragments (#section-links)
                found_links.add(full_url.split('#')[0])
                
    except requests.RequestException as e:
        pass

    return found_links

def scrape_page_content(url: str) -> dict | None:
    """
    Scrapes the main textual content from a single URL.
    Returns a dictionary with the URL and its content, or None on failure.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # **This is the most important part to customize.**
        # We need to find the main content container. After inspecting the sites,
        # 'main' and 'article' tags seem to hold the relevant content.
        main_content = soup.find('main') or soup.find('article')
        
        if main_content:
            # Use .get_text() to extract all text from the container.
            # `separator=' '` joins text from different tags with a space.
            # `strip=True` removes leading/trailing whitespace.
            text = main_content.get_text(separator=' ', strip=True)
            return {"url": url, "content": text}
        else:
            # If no main content is found, we can skip this page.
            return None
            
    except requests.RequestException as e:
        return None

# --- Main Execution ---

if __name__ == "__main__":
    all_site_links = set()
    
    # 1. Discover all links from the starting URLs
    for url in START_URLS:
        links = get_all_links(url)
        all_site_links.update(links)
    
    scraped_data = []
    
    # 2. Scrape the content from each unique link
    total_links = len(all_site_links)
    for i, link in enumerate(list(all_site_links), 1):
        content_dict = scrape_page_content(link)
        if content_dict and content_dict['content']:
            scraped_data.append(content_dict)
        
        # Be a good web citizen! Wait 1 second between requests.
        time.sleep(1)
        
    # 3. Save the final data to a JSON file
    try:
        # Ensure the 'data' directory exists
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        
        with open(SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        pass
