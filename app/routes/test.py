try:
    from app.config import config
    print("Config imported successfully")
except ImportError as e:
    print("Error importing config:", e)