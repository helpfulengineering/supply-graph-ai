import uvicorn
from src.config.settings import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("src.core.main:app", 
                host=API_HOST, 
                port=API_PORT, 
                reload=True,
                reload_dirs=["src"])