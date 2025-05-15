import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from datetime import datetime, UTC
import re

# Configure logging
logging.basicConfig(
    filename='pastebin_crawler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define keywords to search for
KEYWORDS = [
    'crypto', 'bitcoin', 'ethereum', 'blockchain',
    't.me'
]

def get_paste_ids(archive_url, max_pastes=30):
    """Scrape Pastebin archive to extract up to max_pastes valid Paste IDs."""
    print("Scraping Pastebin archive...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(archive_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find paste links in archive table
        paste_ids = []
        for link in soup.select('table.maintable tr td a[href^="/"]')[:max_pastes * 2]:  # Overshoot to account for invalid IDs
            paste_id = link['href'].strip('/')
            # Validate paste ID: should be 8-character alphanumeric
            if re.match(r'^[a-zA-Z0-9]{8}$', paste_id):
                paste_ids.append(paste_id)
            if len(paste_ids) >= max_pastes:
                break
        
        logging.info(f"Extracted {len(paste_ids)} paste IDs from archive")
        print(f"Extracted {len(paste_ids)} paste IDs")
        return paste_ids
    except requests.RequestException as e:
        logging.error(f"Failed to scrape archive: {e}")
        print(f"Error scraping archive: {e}")
        return []

def fetch_paste_content(paste_id):
    """Fetch raw content of a paste using its ID."""
    print(f"Fetching paste {paste_id}...")
    url = f"https://pastebin.com/raw/{paste_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"Successfully fetched paste {paste_id}")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to fetch paste {paste_id}: {e}")
        print(f"Error fetching paste {paste_id}: {e}")
        return None

def find_keywords(content):
    """Check content for keywords and return list of matches."""
    if not content:
        return []
    found = []
    content_lower = content.lower()
    
    for keyword in KEYWORDS:
        # Use regex for t.me to ensure it's a link-like pattern
        if keyword == 't.me':
            if re.search(r'\bt\.me\b', content_lower):
                found.append(keyword)
        elif keyword in content_lower:
            found.append(keyword)
    
    return found

def save_match(paste_id, keywords, output_file):
    """Save paste information to JSONL file if keywords are found."""
    timestamp = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    context = f"Found {' and '.join(keywords)} in Pastebin paste ID {paste_id}"
    data = {
        "source": "pastebin",
        "context": context,
        "paste_id": paste_id,
        "url": f"https://pastebin.com/raw/{paste_id}",
        "discovered_at": timestamp,
        "keywords_found": keywords,
        "status": "pending"
    }
    
    try:
        with open(output_file, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')
        logging.info(f"Saved match for paste {paste_id} with keywords {keywords}")
        print(f"Saved match for paste {paste_id} with keywords {keywords}")
    except IOError as e:
        logging.error(f"Failed to write to {output_file}: {e}")
        print(f"Error writing to {output_file}: {e}")

def main():
    archive_url = "https://pastebin.com/archive"
    output_file = "keyword_matches.jsonl"
    
    print("Starting Pastebin Keyword Crawler...")
    # Clear output file if it exists
    try:
        open(output_file, 'w').close()
    except IOError as e:
        logging.error(f"Failed to clear output file: {e}")
        print(f"Error clearing output file: {e}")
        return
    
    # Get paste IDs
    paste_ids = get_paste_ids(archive_url)
    if not paste_ids:
        logging.error("No paste IDs retrieved. Exiting.")
        print("No paste IDs retrieved. Exiting.")
        return
    
    # Process each paste
    for i, paste_id in enumerate(paste_ids, 1):
        logging.info(f"Processing paste {i}/{len(paste_ids)}: {paste_id}")
        print(f"Processing paste {i}/{len(paste_ids)}: {paste_id}")
        content = fetch_paste_content(paste_id)
        
        if content:
            keywords = find_keywords(content)
            if keywords:
                save_match(paste_id, keywords, output_file)
                logging.info(f"Found keywords {keywords} in paste {paste_id}")
                print(f"Found keywords {keywords} in paste {paste_id}")
            else:
                logging.info(f"No keywords found in paste {paste_id}")
                print(f"No keywords found in paste {paste_id}")
        
        # Rate limiting: wait 2 seconds between requests
        time.sleep(2)

    print("Crawling completed.")

if __name__ == "__main__":
    logging.info("Starting Pastebin Keyword Crawler")
    main()
    logging.info("Crawling completed")