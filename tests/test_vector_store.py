import pytest
from app.vector_store import initialize_vector_store, retrieve_examples, get_ollama_embedding

def test_ollama_embedding():
    try:
        emb = get_ollama_embedding("test query text")
        assert isinstance(emb, list)
        assert len(emb) > 0
        assert isinstance(emb[0], float)
    except Exception as e:
        pytest.skip(f"Ollama local embeddings API not responding: {e}")

def test_initialize_and_retrieve():
    # Make sure DB is populated
    try:
        initialize_vector_store()
    except Exception as e:
        pytest.skip(f"ChromaDB initialization failed: {e}")
        
    # Query for box
    res_box = retrieve_examples("design a simple rectangular block or cuboid box", k=1)
    assert len(res_box) > 0
    assert "box" in res_box[0]["description"].lower() or "cuboid" in res_box[0]["description"].lower()
    assert "length" in res_box[0]["parameters"]
    
    # Query for gear
    res_gear = retrieve_examples("parametric gear with teeth", k=1)
    assert len(res_gear) > 0
    assert "gear" in res_gear[0]["description"].lower() or "spur" in res_gear[0]["description"].lower()
    
    # Query for bracket
    res_bracket = retrieve_examples("mounting plate with holes", k=1)
    assert len(res_bracket) > 0
    assert "bracket" in res_bracket[0]["description"].lower() or "mounting plate" in res_bracket[0]["description"].lower()
