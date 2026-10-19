#python normal_llm01.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)
model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
response = client.responses.create(
    model=model,  # replace if a different model is enabled for you
    input="Explain binary search to a first-year programmer in 150 words."
)
#print(response.id)
print(response.output)
print("\n\n")
print(response.output[0].type)
print("\n\n")
print(response.output_text)

#for item in response.output:
#    print(f"item = {item}\n\n\n")