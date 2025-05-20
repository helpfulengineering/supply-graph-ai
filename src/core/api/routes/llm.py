from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from groq import Groq
import os
from dotenv import load_dotenv
from src.core.api.models.llm.request import LLMRequest
from src.core.api.models.llm.response import LLMResponse

load_dotenv()

router = APIRouter(prefix="/v1/llm", tags=["llm"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if not client.api_key:
    raise HTTPException(status_code=500, detail="Groq API key is not set.")

@router.post("/", response_model=LLMResponse)
async def generate_response(request: LLMRequest):
    """ Generate response the LLM provider based on prompt and optional context.
    Supports streaming and non-streaming responses. """
    
    try:
        # combine prompt and context (if provided) in the request
        messages = []
        if request.context:
            messages.append({"role": "system", "content": request.context})
        messages.append({"role": "user", "content": request.prompt})
        
        # Call the Groq API
        response = client.chat.completions.create(
            messages=messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stream=request.stream
        )
        
        # If streaming is enabled, return a streaming response
        if request.stream:
            def stream_response():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                yield "[DONE]"
            return StreamingResponse(stream_response(), media_type="text/event-stream")
        else:
            # if not streaming, return the full response
            full_response = response.choices[0].message.content
            usage = (
                response.usage.dict()
                if hasattr(response, "usage") and response.usage
                else None
            )
            return LLMResponse(
                response=full_response,
                model=response.model,
                usage=usage
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with LLM provider: {str(e)}")
    
    
    
@router.get("/health")
async def health_check():
    """ Health check for the LLM Endpoint """
    
    try:
        # test a simple API call to verify Groq connection
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello!"}],
            model="llama-3.1-8b-instant",
            max_tokens=10,
        )
        return {
            "status": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM provider is not healthy: {str(e)}")