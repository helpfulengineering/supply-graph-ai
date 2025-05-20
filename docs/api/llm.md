# LLM API
A FastAPI application for serving LLM inferences.

## Features

New: `/llm` POST endpoint for generic LLM inference with prompt and context, powered by Groq Cloud (LLaMA 3.1).
Models defined in `src/core/api/models/llm/request.py` and `src/core/api/models/llm/response.py`.


## API Documentation
### LLM Endpoint
`POST /llm`
Generate text using an LLM provider with a prompt and optional context.
Request Body
```
{
  "prompt": "string", // Required: The main task or query for the LLM
  "context": "string", // Optional: Supplementary information to guide the response
  "model": "string", // Optional: LLM model (default: "llama-3.1-8b-instant")
  "max_tokens": integer, // Optional: Maximum tokens in response (default: 512)
  "temperature": float, // Optional: Sampling temperature (default: 0.8)
  "top_p": float, // Optional: Top-p sampling (default: 0.95)
  "stream": boolean // Optional: Enable streaming response (default: false)
}
```
Responses

200 OK (Non-Streaming):
```
{
  "response": "string", // LLM-generated text
  "model": "string", // Model used
  "usage": { // Optional: Token usage
    "prompt_tokens": integer,
    "completion_tokens": integer,
    "total_tokens": integer
  }
}
```

200 OK (Streaming): Text/event-stream with chunks of text, ending with [DONE].
500 Internal Server Error: If the LLM provider fails.

Example
```
curl -X POST http://localhost:8000/llm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of Brazil?",
    "context": "Answer concisely with no explanation.",
    "model": "llama-3.1-8b-instant",
    "max_tokens": 50,
    "temperature": 0.7,
    "stream": false
  }'
```


## Usage Guide
### Using the LLM Endpoint
The `/llm` endpoint allows clients to send a prompt and optional context to generate text using an LLM (e.g., LLaMA 3.1 via Groq Cloud). The request and response are defined in `src/core/api/models/llm/request.py` and `src/core/api/models/llm/response.py`, respectively.
### Example: Non-Streaming Request
Send a prompt to get a concise response:
```
curl -X POST http://localhost:8000/llm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of Brazil?",
    "context": "Answer concisely with no explanation.",
    "model": "llama-3.1-8b-instant",
    "max_tokens": 50
  }'
```
Response:
```
{
  "response": "The capital is Brasília.",
  "model": "llama-3.1-8b-instant",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 6,
    "total_tokens": 18
  }
}
```

### Example: Streaming Request
Stream a response for a creative task:
```
curl -X POST http://localhost:8000/llm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Tell me a short story.",
    "context": "The story should be about a dragon in a fantasy setting.",
    "model": "llama-3.1-8b-instant",
    "max_tokens": 100,
    "stream": true
  }'
```
Response: Streams tokens like "Once ", "upon ", "a time...", ending with `[DONE]`.

