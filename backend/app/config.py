import os

# Since pydantic-settings isn't explicitly in pyproject.toml yet, let's write a simple settings loader
# or we can add pydantic-settings if we want. But a simple class using os.getenv is even simpler and
# has fewer dependencies. Let's write a simple config file using python's os.environ.


class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "qwen2.5-coder:7b")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "qwen2.5-coder:1.5b")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
    
    # Base dirs
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")
    OUTPUTS_DIR: str = os.path.join(STATIC_DIR, "outputs")
    
settings = Settings()

