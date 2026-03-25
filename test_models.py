import google.generativeai as genai

genai.configure(api_key="AIzaSyCBoKnN_n887xVgDEi2UhsVkQtfu4gqUm4")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
