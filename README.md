## App Image Resource Syncer

This tool automates the process of fetching image assets from the repo, converting them to Base64, and preparing a versioned JSON bundle for our app to consume.

## 🛠 Setup & Installation

## 1. Fix macOS SSL Compatibility

Since macOS uses an older SSL library (LibreSSL), you must downgrade `urllib3` to ensure the script can connect to GitHub:

```bash
python3 -m pip install requests "urllib3<2.0"
```

## 2. Configuration

The script is pre-configured to scan the root `/` and `/dapp` folders of the `IndieClub/image-collection` repository.

## 🚀 Usage

Run the sync script before deploying or when assets change:

```bash
python3 img-syncer.py
```

## Generated Artifacts

1. `images.json`

   : The main resource bundle.

   - *Root images*: Key is the filename (e.g., `logo`).
   - *Dapp images*: Key is prefixed (e.g., `dapp_icon`).

2. **`version.txt`**: A plain text file containing a numeric timestamp (e.g., `20240525081830`).

## ⚠️ Important Notes

- **GitHub Rate Limits**: Without a token, you are limited to 60 requests/hour. If your asset list grows large, add a `GITHUB_TOKEN` to the request headers.

