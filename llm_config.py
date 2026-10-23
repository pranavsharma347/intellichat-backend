import os
from itertools import cycle
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()
api_keys=[

    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
    os.getenv("GOOGLE_API_KEY_5"),

]#here problem is as key is empty then it set none


api_keys=[k for  k in api_keys if k] #filtering out None values

keyPools=cycle(api_keys) #creating a cycle iterator for api keys



def get_llm():        
        current_key = next(keyPools)  # Get the next key from the cycle of every call
        os.environ["GOOGLE_API_KEY"] = current_key
        return init_chat_model("gemini-3.5-flash-lite", model_provider="google_genai")
