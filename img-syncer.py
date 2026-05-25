import requests
import base64
import json
import os
import time

# --- Configuration ---
REPO_OWNER = "IndieClub"
REPO_NAME = "image-collection"
BRANCH = "main"

# Whitelist: "folder_path": "prefix"
TARGET_DIRS = {
    "": "",         # Root folder, no prefix
    "dapp": "dapp_" # dapp folder, prefix with dapp_
}

def sync_images():
    img_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
    image_dict = {}

    for folder, prefix in TARGET_DIRS.items():
        # Correct API format: ://github.com
        api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{folder}?ref={BRANCH}"
        print(f"Scanning folder: /{folder}")
        
        try:
            # verify=False bypasses the LibreSSL error on your Mac
            response = requests.get(api_url, timeout=10, verify=False)
            response.raise_for_status()
            
            for item in response.json():
                if item['type'] == 'file' and item['name'].lower().endswith(img_exts):
                    # name without extension
                    name_base = os.path.splitext(item['name'])[0]
                    final_key = f"{prefix}{name_base}"
                    
                    print(f"  Encoding: {final_key}")
                    
                    # Fetch raw image and convert to base64
                    img_data = requests.get(item['download_url'], timeout=10, verify=False).content
                    image_dict[final_key] = base64.b64encode(img_data).decode('utf-8')
                    
        except Exception as e:
            print(f"  Error in /{folder}: {e}")

    # Write to local file
    with open('images.json', 'w') as f:
        json.dump(image_dict, f, indent=4)
    
    print(f"\nSuccess! Saved {len(image_dict)} images to images.json")

    # Output the version TXT (just the timestamp)
    version_timestamp = time.strftime("%Y%m%d%H%M%S")
    with open('version.txt', 'w') as f:
        f.write(version_timestamp)
    print(f"version.txt: {version_timestamp}")

if __name__ == "__main__":
    # Suppress the SSL warning since we are using verify=False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    sync_images()
