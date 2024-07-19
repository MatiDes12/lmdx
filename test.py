import secrets
import string

def generate_secret_key(length=24):
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Example usage
generated_key = generate_secret_key()
print(f"Generated Secret Key: {generated_key}")
