from mangum import Mangum
from app.main import app

# Create the ASGI handler for Lambda
handler = Mangum(app, lifespan="off")
