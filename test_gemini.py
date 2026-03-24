import google.generativeai as genai

# Use Gemini API Key from AI Studio (not generic Google API Key)
GEN_KEY = "YOUR_GEMINI_API_KEY"  # from https://aistudio.google.com/app/apikey
genai.configure(api_key=GEN_KEY)

try:
    client = genai.GenerativeModel("gemini-1.5-flash")  # free and fast model
    resp = client.generate_content("Hello farmers! Give one tip for farming in India.")
    print("Response:", resp.text)
except Exception as e:
    print("Gemini API failed:", e)
