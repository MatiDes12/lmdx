import os
import google.generativeai as genai

# Access your API key as an environment variable.
genai.configure(api_key=os.environ['GOOGLE_API_KEY1'])
# Choose a model that's appropriate for your use case.
model = genai.GenerativeModel('gemini-1.5-flash')

prompt = "Write a story about a magic backpack."

response = model.generate_content(prompt)

print(response.text)