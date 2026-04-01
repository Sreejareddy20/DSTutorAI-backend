import google.generativeai as genai

# Paste your API key here
genai.configure(api_key="AIzaSyAW9Q8iMoPVnTKh6HpZyAqvfv4R1rEaEF4")

print("Checking available models for your account...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
