
# python normal_llm02.py

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load GROQ_API_KEY from .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY is missing from .env")

# Create Groq client using OpenAI-compatible API
client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Store conversation history locally
messages = [
    {
        "role": "system",
        "content": "You are a helpful AI assistant."
    }
]

print("===================================")
print("          Simple Groq Chat")
print("===================================")
print("Type your message and press Enter.")
print("Type q to quit.")
print("===================================")

while True:

    # Get message from user
    user_message = input("\nYou: ").strip()

    # Quit program
    if user_message.lower() == "q":
        print("\nGoodbye!")
        break

    # Ignore empty messages
    if not user_message:
        print("Please enter a message.")
        continue

    try:
        # Prepare new user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Send complete conversation history
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        # Extract LLM response
        assistant_message = response.choices[0].message.content
        

        # Display response
        print("\nLLM:")
        print(assistant_message)
        print("\nLLM:")

        # Save assistant reply in conversation history
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })

    except Exception as e:

        # Remove failed user message from history
        messages.pop()

        print("\nError:")
        print(e)
