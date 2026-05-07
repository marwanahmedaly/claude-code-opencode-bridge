from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:38765/anthropic",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="glm-5.1", # or glm-5 or minimax-m2.7
    messages=[{"role": "user", "content": "Hello, how are you?"}],
    max_tokens=1000
)

print(response.choices[0].message.content)
