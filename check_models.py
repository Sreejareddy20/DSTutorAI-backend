import google.generativeai as genai

# Use your API Key to check model availability
genai.configure(api_key="API_KEY")

print("Checking available models for your API Key...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
