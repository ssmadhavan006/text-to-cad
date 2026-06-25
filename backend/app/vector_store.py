import os
import json
import httpx
import logging
import chromadb
from app.config import settings

logger = logging.getLogger(__name__)

# Paths inside root data directory
DATA_DIR = os.path.join(os.path.dirname(settings.BASE_DIR), "data")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma")
EXAMPLES_JSON_PATH = os.path.join(DATA_DIR, "few_shot_examples.json")
os.makedirs(CHROMA_PATH, exist_ok=True)

_client = None
_collection = None

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(name="few_shot_examples")

def get_ollama_embedding(text: str) -> list[float]:
    """
    Calls Ollama to get the embedding vector for the given text.
    """
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text
    }
    try:
        response = httpx.post(url, json=payload, timeout=20.0)
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Failed to fetch embedding from Ollama for text '{text[:30]}...': {e}")
        raise RuntimeError(f"Ollama embedding retrieval failed: {e}") from e

def initialize_vector_store():
    """
    Reads the static examples JSON file and populates the ChromaDB collection.
    Rebuilds the collection on every start to ensure any edits to the JSON corpus are synced.
    """
    logger.info("Initializing vector store collection...")
    try:
        client = get_chroma_client()
        try:
            client.delete_collection(name="few_shot_examples")
            logger.info("Deleted existing collection to perform fresh rebuild.")
        except Exception:
            pass
            
        collection = client.get_or_create_collection(name="few_shot_examples")
        
        if not os.path.exists(EXAMPLES_JSON_PATH):
            logger.error(f"Few-shot examples JSON file not found at: {EXAMPLES_JSON_PATH}")
            return
            
        with open(EXAMPLES_JSON_PATH, "r", encoding="utf-8") as f:
            examples = json.load(f)
            
        logger.info(f"Loading {len(examples)} examples into vector store...")
            
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for idx, ex in enumerate(examples):
            desc = ex["description"]
            try:
                emb = get_ollama_embedding(desc)
                ids.append(f"example_{idx}")
                embeddings.append(emb)
                documents.append(desc)
                # Chroma metadata values must be simple types (str, int, float, bool)
                metadatas.append({
                    "description": desc,
                    "parameters": json.dumps(ex["parameters"]),
                    "cot_explanation": ex["cot_explanation"],
                    "code": ex["code"]
                })
            except Exception as e:
                logger.error(f"Skipping example {idx} due to embedding error: {e}")
                
        if ids:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Successfully indexed {len(ids)} examples in ChromaDB.")
        else:
            logger.warning("No examples were indexed in ChromaDB.")
    except Exception as e:
        logger.exception(f"Error during vector store initialization: {e}")

def retrieve_examples(query_description: str, k: int = 3) -> list[dict]:
    """
    Retrieves the top-k most similar examples from ChromaDB based on cosine similarity
    of the query description.
    """
    logger.info(f"Retrieving top {k} examples for query description: '{query_description}'")
    
    try:
        collection = get_collection()
        query_emb = get_ollama_embedding(query_description)
        
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=k
        )
        
        retrieved = []
        if results and "metadatas" in results and results["metadatas"]:
            metadata_list = results["metadatas"][0]
            for meta in metadata_list:
                retrieved.append({
                    "description": meta.get("description"),
                    "parameters": json.loads(meta.get("parameters", "{}")),
                    "cot_explanation": meta.get("cot_explanation"),
                    "code": meta.get("code")
                })
        
        logger.info(f"Retrieved {len(retrieved)} examples from ChromaDB.")
        return retrieved
    except Exception as e:
        logger.error(f"Error querying ChromaDB vector store: {e}")
        # Fallback: if ChromaDB fails, read directly from JSON and search by keyword or return first k
        logger.warning("Falling back to reading from local JSON corpus due to search failure.")
        try:
            with open(EXAMPLES_JSON_PATH, "r", encoding="utf-8") as f:
                examples = json.load(f)
            # Try a simple keyword match fallback
            query_lower = query_description.lower()
            matched = []
            for ex in examples:
                # Check if keywords from query are in example description
                if any(word in ex["description"].lower() for word in query_lower.split() if len(word) > 3):
                    matched.append(ex)
            if matched:
                return matched[:k]
            return examples[:k]
        except Exception as json_err:
            logger.error(f"Fallback direct JSON read failed: {json_err}")
            return []
