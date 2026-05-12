import requests
import io
from PIL import Image

# Create a simple test image
img = Image.new('RGB', (100, 100), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Test vehicle upload to backend
url = "http://192.168.254.102:8000/api/cars/"
files = {
    'photo': ('test_image.jpg', img_bytes, 'image/jpeg')
}
data = {
    'name': 'Test Car',
    'brand': 'Toyota',
    'model': 'Corolla',
    'year': 2024,
    'price_per_day': 1500,
    'type': 'Sedan',
    'transmission': 'Automatic',
    'fuel': 'Gasoline',
    'seats': 5,
    'location': 'Test City',
    'description': 'Test vehicle'
}

response = requests.post(url, files=files, data=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
