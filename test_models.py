import os, time
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY_2")

CANDIDATES = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
]

for model in CANDIDATES:
    llm = init_chat_model(model, model_provider="google_genai", max_retries=1, timeout=30)
    for attempt in (1, 2):
        start = time.time()
        try:
            llm.invoke("Say hi")
            print(f"{model} (call {attempt}): OK, {round(time.time() - start, 1)} seconds")
        except Exception as e:
            print(f"{model} (call {attempt}): ERROR after {round(time.time() - start, 1)}s -> {str(e)[:70]}")