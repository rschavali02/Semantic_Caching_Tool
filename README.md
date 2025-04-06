# Semantic Cache Chat

A smart chatbot application with semantic caching capabilities, built with FastAPI and React. The system uses OpenAI's embeddings for semantic similarity matching and implements intelligent caching strategies based on query types.

## Features

- Semantic similarity-based caching using OpenAI's text embeddings
- Intelligent query classification (time-sensitive vs. evergreen)
- Adaptive cache expiration based on query type
- Real-time chat interface with React
- Docker containerization for easy deployment
- Redis for scalable caching

## Architecture Overview

### Backend (FastAPI)

The backend is built with FastAPI and implements a semantic caching system with the following components:

1. **Query Classification**
   - Regex-based classification of queries into time-sensitive and evergreen
      > I used Regex espressions to classify to remove more unessecary llm costs. Scalability wise I believe this approach is better than implementing a model.
   - Different similarity thresholds for different query types
      > Time-sensative queries should have a high threshold as information varies vs. Evergreen queries. I set the threshold for Evergreen queries to 0.8 based on the precident from this paper: https://arxiv.org/html/2411.05276v2
   - Automatic cache expiration for time-sensitive queries
      > Time-sensitive caches need to expire overtime. I handle this by appending a question asking the llm when the query should expire, I then append this time as a datetime object and set the expiry condition using Redis' time to live feature rather than the default LRU condition.

2. **Semantic Caching**
   - Uses OpenAI's `text-embedding-ada-002` model for embeddings
   - Cosine similarity for semantic matching
     > I use a threshold score for semantic caching
   - Redis for cache storage with TTL support
     > The time-sensitive queries expire with TTL

3. **API Endpoints**
   - `/api/query`: Main endpoint for processing queries
   - `/api/cache-info/{query_hash}`: Debug endpoint for cache inspection
   - `/health`: Health check endpoint

### Frontend (React)

- Modern React application with Vite
- Tailwind CSS for styling
- Real-time chat interface
- Query type indicators and metadata display

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Node.js (for frontend development)
- OpenAI API key

### Backend Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd semantic-cache-chat
   ```

2. Create a `.env` file in the root directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. Start the backend services:
   ```bash
   docker-compose up --build
   ```

The backend will be available at `http://localhost:8000`.

### Frontend Setup (Optional)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`.

## Testing the Cache

Here are some curl commands to test the caching functionality:

1. Test a time-sensitive query:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current sitaution on tariffs?", "forceRefresh": false}'
```

2. Test cache hit (run a semantically similar query):
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What’s the latest update on tariffs?", "forceRefresh": false}'
```

3. Force refresh the cache:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current sitaution on tariffs?", "forceRefresh": true}'
```

4. Check cache info for a specific query:
```bash
# First, get the query hash from a response, then:
curl http://localhost:8000/api/cache-info/fd9bcf84280849b40fb395c259dc32b2
```

5. Test an evergreen query:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?", "forceRefresh": false}'
```

To verify the 5-minute cache expiration:
1. Make a time-sensitive query
2. Check its TTL immediately:
```bash
docker-compose exec redis redis-cli TTL "query:your_query_hash"
```
3. Wait a few minutes and check again to see the TTL decrease

## Design Decisions

### Embedding Model Choice

We use OpenAI's `text-embedding-ada-002` model for several reasons:
- High-quality embeddings with good semantic understanding
- Cost-effective compared to larger models
- Fast inference time

### Caching Strategy

1. **Query Classification**
   - Time-sensitive queries (weather, news, etc.): 5-minute default TTL
   - Evergreen queries (facts, definitions): No expiration
     > With more time, I would have implemented and LRU expiration for Evergreen queries.
   - Higher similarity threshold (0.90) for time-sensitive queries
   - Lower threshold (0.80) for evergreen queries

2. **Cache Implementation**
   - Redis for distributed caching support
     > Redis can also be switched to a cloud database for better scalability
     > It is a robust solution for caching
   - Hash-based keys for efficient lookups
   - TTL support for automatic expiration

## Tradeoffs and Optimizations

### Current Tradeoffs

1. **Similarity Thresholds**
   - Higher thresholds reduce false positives but increase cache misses
   - Lower thresholds improve cache hits but may return less accurate responses

2. **Query Classification**
   - Regex-based classification is fast but may miss edge cases due to hardcoded setting
   - Alternative: Could use ML-based classification at the cost of latency and increased complexity

### Potential Optimizations
1. **Cache Storage**
   - Currently Evergreen caches have no expiration date while the Time-sensitive queries do. There should be a condition to remove Evergreen queries when the cache is full. 

3. **Performance Enhancements**
   - Add response streaming for long-form content, for longer queries we might need a better strategy to classify
