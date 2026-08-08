import streamlit as st
import requests
import json

# Streamlit secrets से GitHub डिटेल्स फेच करें
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_OWNER = st.secrets.get("REPO_OWNER", "")
REPO_NAME = st.secrets.get("REPO_NAME", "ck-pdf-processor")
FILE_PATH = "shipper_rules.json"

def fetch_rules_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            file_info = response.json()
            # GitHub API फाइल के कंटेंट को base64 में लौटाती है, इसलिए इसे डिकोड करना पड़ता है
            content_encoded = file_info.get("content", "")
            import base64
            decoded_bytes = base64.b64decode(content_encoded)
            return json.loads(decoded_bytes.decode('utf-8'))
    except Exception:
        pass
    return {}

def push_rules_to_github(shippers_json_payload):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    
    try:
        # 1. पहले पुरानी फाइल का SHA पता करें (अगर फाइल पहले से है)
        res = requests.get(url, headers=headers, timeout=15)
        sha = res.json().get("sha") if res.status_code == 200 else None
        
        # 2. डिक्शनरी को सुंदर JSON स्ट्रिंग में बदलें
        json_str = json.dumps(shippers_json_payload, indent=4)
        
        # 3. GitHub API टेक्स्ट फाइल भेजने के लिए base64 मांगती है (यह सिर्फ API की तकनीकी जरूरत है, हम कोई यूजर फाइल अपलोड नहीं कर रहे)
        import base64
        encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": "Update shipper rules via CK PDF Processor UI",
            "content": encoded_content,
        }
        if sha:
            payload["sha"] = sha
            
        put_res = requests.put(url, headers=headers, data=json.dumps(payload), timeout=20)
        return put_res.status_code in [200, 201]
    except Exception:
        return False
