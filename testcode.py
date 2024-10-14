from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import time
from functools import lru_cache
import asyncio
import hashlib

app = FastAPI()

# Global dictionaries for simple in-memory cache and quota control
cache = {}
user_requests = {}

# Middleware for Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_body = await request.body()  # Get request body for logging

    # Logging request details
    print(f"Request: {request.method} {request.url}")
    print(f"Request Body: {request_body.decode('utf-8')}")

    # Process the request
    response = await call_next(request)

    # Logging response details
    duration = time.time() - start_time
    print(f"Response Status Code: {response.status_code}")
    print(f"Request completed in {duration:.4f}s")

    return response

# Middleware for Caching
@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    # Create a unique cache key based on the request URL and body
    cache_key = hashlib.md5((str(request.url) + str(await request.body())).encode('utf-8')).hexdigest()

    # Check if cache is available
    if cache_key in cache:
        print(f"Cache hit for key {cache_key}")
        return JSONResponse(cache[cache_key])

    # Process request and cache response
    response = await call_next(request)
    response_body = [section async for section in response.body_iterator]
    response_data = b''.join(response_body).decode('utf-8')

    # Cache response with TTL of 60 seconds
    cache[cache_key] = response_data
    asyncio.create_task(clear_cache(cache_key, ttl=60))
    
    # Return response
    return JSONResponse(response_data)

async def clear_cache(cache_key, ttl=60):
    await asyncio.sleep(ttl)
    if cache_key in cache:
        del cache[cache_key]

# Middleware for Quota Control
@app.middleware("http")
async def quota_middleware(request: Request, call_next):
    client_ip = request.client.host
    max_requests = 10  # Example limit: 10 requests
    window_seconds = 60  # Time window: 60 seconds

    if client_ip not in user_requests:
        user_requests[client_ip] = []

    # Filter out requests older than the time window
    current_time = time.time()
    user_requests[client_ip] = [timestamp for timestamp in user_requests[client_ip] if current_time - timestamp < window_seconds]

    # If the request quota is exceeded, block the request
    if len(user_requests[client_ip]) >= max_requests:
        raise HTTPException(status_code=429, detail="Quota exceeded. Please wait before making more requests.")

    # Log the request
    user_requests[client_ip].append(current_time)

    return await call_next(request)

# Guard Rails: Validate Payload or Perform Early Checks
@app.middleware("http")
async def guard_rails_middleware(request: Request, call_next):
    # Example guard rail: limit payload size (e.g., 1 MB)
    max_payload_size = 1 * 1024 * 1024  # 1 MB

    # Check request size
    content_length = int(request.headers.get('content-length', 0))
    if content_length > max_payload_size:
        raise HTTPException(status_code=413, detail="Request payload too large")
    
    print("Guard rails called")

    # Continue processing the request
    return await call_next(request)

# Pydantic model for input validation
class Item(BaseModel):
    name: str = Field(..., min_length=1, description="The name of the item")
    price: float = Field(..., gt=0, description="The price must be greater than 0")
    description: str | None = None

# POST endpoint to create an item
@app.post("/items/")
async def create_item(item: Item):
    print("final api method called")
    # Simple response to simulate processing
    return {"item": item, "message": "Item successfully created"}

# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# Run the app with: uvicorn filename:app --reload
