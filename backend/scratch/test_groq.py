import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

api_key = os.environ.get("GROQ_API_KEY")
print("API Key:", api_key[:15] + "..." if api_key else "None")

try:
    client = Groq(api_key=api_key)
    print("Testing chat completion...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello! Reply with OK if you receive this."}],
        temperature=0.1,
    )
    print("Success!")
    print("Response:", completion.choices[0].message.content)
except Exception as e:
    print("Error during Groq call:")
    import traceback
    traceback.print_exc()
