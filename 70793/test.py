import platform
platform.platform = lambda: "Windows-11"
platform.system = lambda: "Windows"
platform.machine = lambda: "AMD64"

from dotenv import load_dotenv
load_dotenv()
from openai import AzureOpenAI
import os
c = AzureOpenAI(api_key=os.getenv('AZURE_OPENAI_EMBED_API_KEY'),
                azure_endpoint=os.getenv('AZURE_OPENAI_EMBED_ENDPOINT'),api_version="2024-02-01",
                timeout=10.0) # 10초 타임아웃
r = c.embeddings.create(model=os.getenv('AZURE_EMBED_DEPLOYMENT', 'text-embedding-3-small'), input='test')
print('OK:', len(r.data[0].embedding))