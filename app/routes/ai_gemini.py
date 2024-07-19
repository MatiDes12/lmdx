import requests

def analyze_image(image_path):
    api_url = 'https://api.gemini-ai.com/analyze'
    with open(image_path, 'rb') as image_file:
        files = {'file': image_file}
        response = requests.post(api_url, files=files)

    response.raise_for_status()
    return response.json()
