import requests

def analyze_image(filepath):
    # Replace with your Google Gemini API endpoint and API key
    API_ENDPOINT = 'https://api.google.com/gemini/v1/analyze'
    API_KEY = 'AIzaSyA4m61-B8nDyHHlOiwI4602M9ZYexYxo0Y'

    with open(filepath, 'rb') as file:
        files = {'file': file}
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = requests.post(API_ENDPOINT, files=files, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {'error': 'Failed to analyze image'}