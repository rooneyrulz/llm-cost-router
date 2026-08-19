import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def call_model(model_name: str, reasoning_effort: str | None, query: str):
    kwargs = {}
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": query}],
        **kwargs,
    )
    return response
