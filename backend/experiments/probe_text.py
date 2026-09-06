import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
reply = ChatGoogleGenerativeAI(model="gemini-3.6-flash").invoke("Say the word: banana")

print("type(reply.content) ->", type(reply.content).__name__)

t = getattr(reply, "text", None)
if callable(t):
    print("reply.text()        ->", repr(t())[:120])
elif t is not None:
    print("reply.text          ->", repr(t)[:120])
else:
    print("reply.text          -> NOT PRESENT")
