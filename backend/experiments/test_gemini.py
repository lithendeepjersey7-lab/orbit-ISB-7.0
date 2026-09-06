import os
from dotenv import load_dotenv

load_dotenv()

# 1. Ask the API which models this key is actually allowed to call.
from google import genai

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
print("--- models available to your key ---")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions:
        print(" ", m.name)

# 2. Then try the one Google's error message recommended.
from langchain_google_genai import ChatGoogleGenerativeAI

MODEL = "gemini-3.6-flash"
print("\n--- calling", MODEL, "---")
llm = ChatGoogleGenerativeAI(model=MODEL)
print(llm.invoke("In one sentence, what is a startup competitor analysis?").content)
