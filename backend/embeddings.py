import numpy as np

# Initialize the model lazily to avoid circular imports
_model = None

def get_model():
    """
    Get the SentenceTransformer model, initializing it if necessary.

    Returns:
        SentenceTransformer: The model instance
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _model

def generate_embedding(text):
    """
    Generate embedding for a given text using sentence-transformers.

    Args:
        text (str): The text to generate embedding for

    Returns:
        numpy.ndarray: The embedding vector
    """
    if not text:
        return np.zeros(384)  # Return zero vector for empty text

    # Generate embedding
    model = get_model()
    embedding = model.encode(text)

    return embedding

def generate_checklist_item_embedding(item):
    """
    Generate embedding for a checklist item by combining question and description.

    Args:
        item (dict): Checklist item with 'question' and 'description' fields

    Returns:
        numpy.ndarray: The embedding vector
    """
    # Combine question and description for better semantic matching
    combined_text = f"{item['question']} {item['description']}"

    return generate_embedding(combined_text)

def semantic_search(query_text, embeddings, top_k=5):
    """
    Perform semantic search against a list of embeddings.

    Args:
        query_text (str): The query text
        embeddings (list): List of (id, embedding) tuples
        top_k (int): Number of top results to return

    Returns:
        list: List of (id, score) tuples for top matches
    """
    # Generate query embedding
    query_embedding = generate_embedding(query_text)

    # Calculate cosine similarity
    results = []
    for item_id, item_embedding in embeddings:
        # Cosine similarity
        similarity = np.dot(query_embedding, item_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(item_embedding)
        )
        results.append((item_id, float(similarity)))

    # Sort by similarity (descending)
    results.sort(key=lambda x: x[1], reverse=True)

    # Return top k results
    return results[:top_k]