import httpx, os, json
from dotenv import load_dotenv
load_dotenv()

url = os.getenv('AZURE_OPENAI_EMBED_ENDPOINT').rstrip('/') + "/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-02-01"
key = os.getenv('AZURE_OPENAI_EMBED_API_KEY')

print(f"URL: {url}")
print("요청 중...", flush=True)

try:
    r = httpx.post(url, json={"input": "test"}, headers={"api-key": key}, timeout=10.0)
    print(f"Status: {r.status_code}")
    print(r.text[:200])
except httpx.TimeoutException:
    print("타임아웃 (10초)")
except Exception as e:
    print(f"에러: {e}")
