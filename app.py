from app import create_app
from scripts.initialize_firebase import initialize_firebase

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)