from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import openai
from openai import OpenAI
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import os
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

# Load environment variables and initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Initialize FastAPI
app = FastAPI()

# Configure CORS to connect to frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
#Using Redis for scalability a d persistent caching, This can easily be configured to a Redis Cloud database

class QueryType(Enum):
    TIMESENSITIVE = "timesensitive"
    EVERGREEN = "evergreen"
#Splitting as time senstitive queries need to be called by llm for best user satisfacation

def classify_query(query: str) -> QueryType:
    # Use regex patterns to classify query type to conserve llm requests, we do not want to make unnessecary ones
    time_sensitive_patterns = [
     # Weather and Environment
        r'\bweather\b', r'\btemperature\b', r'\bforecast\b',
        
        # Time-based references
        r'\btoday\b', r'\btomorrow\b', r'yesterday',
        r'\b(this|next|last) (week|month|year|weekend)\b',
        r'\bcurrent\b', r'\bnow\b',
        
        # News and Events
        r'\bnews\b', r'\bbreaking\b', r'\blatest\b',
        r'\btrending\b', r'\bviral\b',
        
        # Markets and Prices
        r'\bprice\b', r'\bstock(s)?\b', r'\bmarket\b',
        r'\bcrypto\b', r'\bexchange rate\b',
        
        # Sports and Entertainment
        r'\bsports?\b', r'\bscore(s)?\b', r'\blineup\b',
        r'\bTV guide\b', r'\bnew (movies?|shows?|episodes?|games?)\b',
        
        # Events and Schedules
        r'\bconcerts?\b', r'\bevents?\b', r'\bschedule\b',
        
        # Sales and Deals
        r'\bsale\b', r'\bdiscount\b', r'\bdeals?\b',
        r'\bBlack Friday\b', r'\bCyber Monday\b'
    ]
    #Use \b to reduce false positives in Regex format
    if any(re.search(pattern, query.lower()) for pattern in time_sensitive_patterns):
        return QueryType.TIMESENSITIVE
    return QueryType.EVERGREEN


class QueryRequest(BaseModel):
    query: str
    forceRefresh: bool = False  # Optional parameter to bypass cache

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What's the weather like in New York today?",
                "forceRefresh": False
            }
        }

def get_embedding(text: str):
    """Fetch text embedding from OpenAI API"""
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        #Using high quality embedding model
        
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")


def get_cached_response(query: str): 
    """Check Redis cache for a semantically similar response"""
    query_type = classify_query(query)
    
    # Set threshold based on query type
    threshold = 0.90 if query_type == QueryType.TIMESENSITIVE else 0.80
    
    query_embedding = np.array(get_embedding(query)).reshape(1, -1)
    
    for key in redis_client.scan_iter("query:*"):
        stored_data = json.loads(redis_client.get(key))
        stored_embedding = np.array(stored_data["embedding"]).reshape(1, -1)
        similarity = cosine_similarity(query_embedding, stored_embedding)[0][0]
        
        print(f"Similarity score for '{stored_data['query']}': {similarity}")  # Debug line
        
        # Use higher threshold for time-sensitive queries
        if similarity >= threshold:
            return stored_data, similarity
    
    return None, 0.0

def cache_response(query: str, response: str, expiry_time: Optional[datetime] = None):
    """Store query-response pair in Redis with expiration"""
    embedding = get_embedding(query)
    key = f"query:{hashlib.md5(query.encode()).hexdigest()}"
    query_type = classify_query(query)
    
    cache_data = {
        "query": query,
        "main_response": response,
        "embedding": embedding,
        "timestamp": datetime.now().isoformat(),
        "query_type": query_type.value
    }
    
    if expiry_time:
        # Calculate TTL in seconds
        # Use TTL for time-sensitive queries
        ttl = int((expiry_time - datetime.now()).total_seconds())
        print(f"Setting cache with TTL: {ttl} seconds")
        if ttl > 0:
            redis_client.set(key, json.dumps(cache_data), ex=ttl)
        else:
            # If expiry time is in the past, set default 5 minutes
            print("Using default 5-minute expiration")
            redis_client.set(key, json.dumps(cache_data), ex=300)
    else:
        # No expiration for evergreen queries
        print("Storing evergreen query without expiration")
        redis_client.set(key, json.dumps(cache_data))
    
    print(f"Cache key: {key}")
    return key

    
#Check for proper connection with Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_ping = redis_client.ping()
        # Test OpenAI API key
        api_key_configured = bool(client.api_key)
        return {
            "status": "healthy",
            "redis_connected": redis_ping,
            "api_key_configured": api_key_configured
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/api/query")
async def handle_query(request: Request):
    """API endpoint to process user queries with semantic caching"""
    try:
        # Parse the JSON request body
        body = await request.json()
        query = body.get("query")
        force_refresh = body.get("forceRefresh", False)

        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")

        # Get query type
        query_type = classify_query(query)

        # Test Redis connection
        redis_client.ping()
        
        if not force_refresh:
            try:
                cached_response, similarity = get_cached_response(query)
                if cached_response:
                    return {
                        "response": cached_response["main_response"],
                        "metadata": {
                            "source": "cache",
                            "query_type": query_type.value,
                            "similarity_score": similarity
                        }
                    }
            except Exception as cache_error:
                print(f"Cache error: {str(cache_error)}")
        
        # Verify OpenAI API key
        if not client.api_key:
            raise ValueError("OpenAI API key is not set")
        
        # For time-sensitive queries, append the expiration question
        if query_type == QueryType.TIMESENSITIVE:
            augmented_query = f"""{query}
            
            Additionally, please provide an expiration time for this information in ISO format. 
            Format your response as:
            MAIN_RESPONSE: [your main response]
            EXPIRY: [ISO format date-time when this information expires]"""
        else:
            augmented_query = query

        # Query LLM
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": augmented_query}]
        )
        answer = response.choices[0].message.content

        # Parse the response for time-sensitive queries
        if query_type == QueryType.TIMESENSITIVE:
            try:
                # Split the response into main response and expiry
                parts = answer.split("MAIN_RESPONSE:")
                if len(parts) > 1:
                    parts = parts[1].split("EXPIRY:")
                    main_response = parts[0].strip()
                    expiry_str = parts[1].strip() if len(parts) > 1 else None
                    
                    # Parse the expiry datetime
                    expiry_time = datetime.fromisoformat(expiry_str) if expiry_str else (
                        datetime.now() + timedelta(minutes=5)  # Default 5 minutes if parsing fails
                    )
                else:
                    # If response doesn't contain MAIN_RESPONSE, clean up any EXPIRY text
                    main_response = answer.split("EXPIRY:")[0].strip()
                    expiry_time = datetime.now() + timedelta(minutes=5)
            except Exception as e:
                print(f"Error parsing time-sensitive response: {e}")
                main_response = answer
                expiry_time = datetime.now() + timedelta(minutes=5)
        else:
            main_response = answer
            expiry_time = None

        try:
            cache_response(query, main_response, expiry_time)
        except Exception as cache_error:
            print(f"Cache storage error: {str(cache_error)}")
            
        return {
            "response": main_response,
            "metadata": {
                "source": "llm",
                "query_type": query_type.value
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
