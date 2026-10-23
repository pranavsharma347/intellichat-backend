import os, time
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
print("Model:", MODEL)

for i in range(1, 6):
    key = os.getenv(f"GOOGLE_API_KEY_{i}")
    if not key:
        print(f"Key {i}: .env mein nahi mili")
        continue
    os.environ["GOOGLE_API_KEY"] = key
    llm = init_chat_model(MODEL, model_provider="google_genai", max_retries=1, timeout=30)
    start = time.time()
    try:
        llm.invoke("Say hi")
        print(f"Key {i}: OK, {round(time.time() - start, 1)} seconds")
    except Exception as e:
        print(f"Key {i}: ERROR after {round(time.time() - start, 1)}s -> {str(e)[:100]}")