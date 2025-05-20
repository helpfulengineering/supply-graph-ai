import time
import re
from typing import Dict, Any, List, Optional, Tuple
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

from .directory_manager import DirectoryManager

class LLMProvider:
    """Provider for LLM services using actual model calls"""
    
    def __init__(self, model_name: str = None):
        """Initialize the LLM provider with model and directories"""
        # Use environment variable or default to an open-source model that doesn't require login
        # TinyLlama is a smaller model that's openly available
        self.model_name = model_name or os.environ.get("LLM_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        self.directory_manager = DirectoryManager()
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the model and tokenizer with additional error handling"""
        print(f"Initializing model: {self.model_name}")
        
        try:
            # Set up device configuration
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")
            
            # Load tokenizer with fallbacks
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            except Exception as e:
                print(f"Error loading tokenizer: {str(e)}")
                print("Falling back to default tokenizer")
                self.tokenizer = AutoTokenizer.from_pretrained("facebook/opt-125m")  # Very small fallback
            
            # Load model with appropriate configuration
            try:
                if device == "cuda":
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        device_map="auto",
                        torch_dtype=torch.float16,
                        low_cpu_mem_usage=True
                    )
                else:
                    # For CPU
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        device_map={"": device},
                        low_cpu_mem_usage=True
                    )
                    
                # Create generation pipeline
                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if device == "cuda" else -1
                )
                print(f"Successfully loaded model: {self.model_name}")
            except Exception as e:
                print(f"Error loading model: {str(e)}")
                print("Falling back to text-only response mode")
                self.model = None
                self.generator = None
        except Exception as e:
            print(f"Critical error initializing LLM provider: {str(e)}")
            print("API will continue to run, but LLM features will be unavailable")
            self.model = None
            self.tokenizer = None
            self.generator = None
            
        # Flag to check if model is available
        self.model_available = self.generator is not None
        
    def _format_prompt_for_model(self, prompt: str, system_message: Optional[str] = None) -> str:
        """Format prompt based on the model architecture"""
        # Check if model is a Llama variant
        if "llama" in self.model_name.lower():
            if system_message:
                # TinyLlama uses the same format as Llama-2
                return f"<s>[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n{prompt} [/INST]"
            else:
                return f"<s>[INST] {prompt} [/INST]"
        # Add support for different model formats as needed
        else:
            # Generic format for other models
            if system_message:
                return f"{system_message}\n\n{prompt}"
            else:
                return prompt
    
    def _fill_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Fill a template with variables"""
        result = template
        for key, value in variables.items():
            pattern = r"{{" + re.escape(key) + r"}}"
            result = re.sub(pattern, str(value), result)
        return result
    
    def _prepare_context(self, context_name: Optional[str]) -> Dict[str, Any]:
        """Prepare context data from file if specified"""
        if not context_name:
            return {}
            
        try:
            return self.directory_manager.get_context(context_name)
        except FileNotFoundError as e:
            print(f"Warning: {str(e)}")
            return {}
    
    def _prepare_prompt(self, 
                      raw_prompt: str, 
                      prompt_template: Optional[str], 
                      template_variables: Dict[str, Any]) -> str:
        """Prepare final prompt text using template if specified"""
        if not prompt_template:
            return raw_prompt
            
        try:
            template, required_vars = self.directory_manager.get_prompt(prompt_template)
            
            # Check if all required variables are provided
            missing_vars = [var for var in required_vars if var not in template_variables]
            if missing_vars:
                raise ValueError(f"Missing required template variables: {', '.join(missing_vars)}")
                
            # Add raw prompt to template variables if not overridden
            if 'prompt' not in template_variables:
                template_variables['prompt'] = raw_prompt
                
            return self._fill_template(template, template_variables)
        except FileNotFoundError:
            # Fall back to raw prompt if template not found
            return raw_prompt
            
    async def generate(self, 
                      prompt: str,
                      prompt_template: Optional[str] = None,
                      context_name: Optional[str] = None, 
                      template_variables: Dict[str, Any] = None,
                      system_message: Optional[str] = None,
                      temperature: float = 0.7,
                      max_tokens: int = 1000,
                      stop_sequences: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a response using the LLM"""
        start_time = time.time()
        
        # If model isn't available, return a fallback response
        if not hasattr(self, "model_available") or not self.model_available:
            return {
                "response": f"LLM model is not available. I received your prompt: '{prompt}'",
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": 0,
                    "total_tokens": len(prompt.split())
                },
                "model": "fallback_text_only",
                "finish_reason": "model_unavailable",
                "processing_time_ms": 0
            }
        
        if template_variables is None:
            template_variables = {}
            
        # Get context data if specified
        context_data = self._prepare_context(context_name)
        
        # Prepare the final prompt
        prepared_prompt = self._prepare_prompt(
            raw_prompt=prompt,
            prompt_template=prompt_template,
            template_variables=template_variables
        )
        
        # Format for the specific model
        formatted_prompt = self._format_prompt_for_model(
            prompt=prepared_prompt,
            system_message=system_message
        )
        
        # Configure generation parameters
        generation_config = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "do_sample": temperature > 0,
            "top_p": 0.95,
            "top_k": 50,
            "return_full_text": False,
        }
        
        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences
            
        # Perform actual model inference
        try:
            result = self.generator(
                formatted_prompt,
                **generation_config
            )
            
            # Extract generated text
            generated_text = result[0]["generated_text"].strip()
            
            # Calculate token usage
            input_tokens = len(self.tokenizer.encode(formatted_prompt))
            output_tokens = len(self.tokenizer.encode(generated_text))
            total_tokens = input_tokens + output_tokens
            
            end_time = time.time()
            processing_time_ms = int((end_time - start_time) * 1000)
            
            return {
                "response": generated_text,
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": total_tokens
                },
                "model": self.model_name,
                "finish_reason": result[0].get("finish_reason", "length"),
                "processing_time_ms": processing_time_ms
            }
            
        except Exception as e:
            raise RuntimeError(f"Error generating LLM response: {str(e)}")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Return a list of recommended open-source models that can be used"""
        return [
            {
                "id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "name": "TinyLlama 1.1B Chat",
                "description": "Small and fast Llama model for chat (1.1B parameters)",
                "memory_required": "~2GB"
            },
            {
                "id": "microsoft/phi-2",
                "name": "Microsoft Phi-2",
                "description": "Small but capable 2.7B parameter model",
                "memory_required": "~5GB"
            },
            {
                "id": "facebook/opt-1.3b",
                "name": "OPT 1.3B",
                "description": "Open Pre-trained Transformer 1.3B parameter model",
                "memory_required": "~3GB"
            },
            {
                "id": "stabilityai/stablelm-base-alpha-3b",
                "name": "StableLM 3B",
                "description": "Base 3B parameter model from Stability AI",
                "memory_required": "~6GB"
            }
        ]