import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# --- Configuration ---
REPO_OWNER = "IndieClub"
REPO_NAME = "image-collection"
BRANCH = "main"
MAX_WORKERS = 5  

# Whitelist: "folder_path": "prefix"
TARGET_DIRS = {
    "": "",         # Root folder, no prefix
    "dapp": "dapp_" # dapp folder, prefix with dapp_
}

# Image extensions mapping to their respective MIME subtypes
MIME_MAP = {
    '.png': 'png',
    '.jpg': 'jpeg',
    '.jpeg': 'jpeg',
    '.gif': 'gif',
    '.webp': 'webp'
}

def fetch_folder_contents(session, folder):
    """Fetches all items from a GitHub repository folder, handling pagination safely."""
    # Explicit URL construction to prevent any hidden string issues
    base_url = "https://api.github.com"
    api_url = f"{base_url}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{folder}?ref={BRANCH}"
    items = []
    
    while api_url:
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        items.extend(response.json())
        
        # Safe GitHub API link header pagination parser
        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            next_link = None
            for link in links:
                if 'rel="next"' in link:
                    # Isolate the text inside the angle brackets <url>
                    next_link = link.split(';')[0].strip('< >')
                    break
            api_url = next_link
        else:
            api_url = None
            
    return items

def download_and_encode(session, item, prefix):
    """Downloads a single image and converts it to a Data URI."""
    _, ext = os.path.splitext(item['name'].lower())
    
    if item['type'] == 'file' and ext in MIME_MAP:
        name_base, _ = os.path.splitext(item['name'])
        final_key = f"{prefix}{name_base}"
        mime_type = MIME_MAP[ext]
        
        try:
            img_data = session.get(item['download_url'], timeout=10).content
            b64_str = base64.b64encode(img_data).decode('utf-8')
            data_uri = f"data:image/{mime_type};base64,{b64_str}"
            return final_key, data_uri
        except Exception as e:
            print(f"Error downloading {item['name']}: {e}")
            
    return None

def sync_images():
    image_dict = {}
    download_tasks = []
    
    with requests.Session() as session:
        for folder, prefix in TARGET_DIRS.items():
            print(f"Scanning folder: /{folder}")
            try:
                folder_items = fetch_folder_contents(session, folder)
                for item in folder_items:
                    download_tasks.append((item, prefix))
            except Exception as e:
                print(f"Error scanning /{folder}: {e}")

        print(f"\nStarting concurrent downloads with {MAX_WORKERS} workers...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(download_and_encode, session, item, prefix): item['name'] 
                for item, prefix in download_tasks
            }
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    key, data_uri = result
                    image_dict[key] = data_uri
                    print(f"  Encoded: {key}")

    # Write data locally
    with open('images.json', 'w', encoding='utf-8') as f:
        json.dump(image_dict, f, indent=4)
    print(f"\nSuccess! Saved {len(image_dict)} images to images.json")

    # Output the version timestamp
    version_timestamp = time.strftime("%Y%m%d%H%M%S")
    with open('version.txt', 'w', encoding='utf-8') as f:
        f.write(version_timestamp)
    print(f"version.txt: {version_timestamp}")

if __name__ == "__main__":
    sync_images()
