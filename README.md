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
   - Different similarity thresholds for different query types
   - Automatic cache expiration for time-sensitive queries

2. **Semantic Caching**
   - Uses OpenAI's `text-embedding-ada-002` model for embeddings
   - Cosine similarity for semantic matching
   - Redis for cache storage with TTL support

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
- 1536-dimensional vectors providing good balance between precision and performance

### Caching Strategy

1. **Query Classification**
   - Time-sensitive queries (weather, news, etc.): 5-minute default TTL
   - Evergreen queries (facts, definitions): No expiration
   - Higher similarity threshold (0.95) for time-sensitive queries
   - Lower threshold (0.85) for evergreen queries

2. **Cache Implementation**
   - Redis for distributed caching support
   - Hash-based keys for efficient lookups
   - JSON serialization for metadata storage
   - TTL support for automatic expiration

## Tradeoffs and Optimizations

### Current Tradeoffs

1. **Similarity Thresholds**
   - Higher thresholds reduce false positives but increase cache misses
   - Lower thresholds improve cache hits but may return less accurate responses

2. **Cache Storage**
   - Storing full embeddings increases memory usage
   - Alternative: Could store quantized embeddings at the cost of accuracy

3. **Query Classification**
   - Regex-based classification is fast but may miss edge cases
   - Alternative: Could use ML-based classification at the cost of latency

### Potential Optimizations

1. **Embedding Optimizations**
   - Implement embedding quantization
   - Add embedding clustering for faster similarity search
   - Consider using approximate nearest neighbors (ANN) for large-scale deployment

2. **Caching Improvements**
   - Implement cache warming for common queries
   - Add cache eviction policies based on usage patterns
   - Consider hierarchical caching for different query types

3. **Performance Enhancements**
   - Add batch processing for multiple similar queries
   - Implement request coalescing for concurrent similar queries
   - Add response streaming for long-form content

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
