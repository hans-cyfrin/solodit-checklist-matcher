import sys
import logging
import os
import numpy as np
from typing import List, Tuple, Union, Optional, Dict, Any
import torch
from sentence_transformers import SentenceTransformer
import time
from dotenv import load_dotenv
from openrouter import chat_completion

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger(__name__)

# Check NumPy version and handle compatibility issues
try:
    numpy_version = np.__version__
    major_version = int(numpy_version.split('.')[0])
    if major_version >= 2:
        logger.warning(f"NumPy version {numpy_version} may have compatibility issues with sentence-transformers")
except Exception as e:
    logger.error(f"Error checking NumPy version: {str(e)}")

try:
    import torch
except ImportError:
    logger.error("PyTorch is not installed. Please install it manually: pip install torch==1.13.1")
    torch = None

# Fix huggingface_hub compatibility issue
try:
    import huggingface_hub
    if not hasattr(huggingface_hub, 'cached_download'):
        # Patch the missing function with the newer equivalent
        from huggingface_hub.file_download import hf_hub_download
        huggingface_hub.cached_download = hf_hub_download
        logger.info("Successfully patched huggingface_hub for compatibility with sentence-transformers")
except ImportError:
    logger.warning("Could not import huggingface_hub. This may cause issues with sentence-transformers.")
except Exception as e:
    logger.warning(f"Error patching huggingface_hub: {str(e)}")

# Initialize the model lazily to avoid circular imports
_model = None

# Add a simple in-memory cache for embeddings
_embedding_cache = {}
_cache_hits = 0
_cache_misses = 0

def get_model():
    """
    Get or initialize the sentence-transformers model.
    Uses a singleton pattern to avoid reloading the model.

    Returns:
        SentenceTransformer: The initialized model or None if initialization failed
    """
    global _model
    if _model is None:
        try:
            logger.info("Initializing sentence-transformers model...")
            from sentence_transformers import SentenceTransformer

            # Check if CUDA is available and set device accordingly
            device = 'cuda' if torch and torch.cuda.is_available() else 'cpu'
            if device == 'cuda':
                logger.info("Using CUDA for model inference")
            else:
                logger.info("Using CPU for model inference")

            _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
            logger.info("Model initialized successfully")
            return _model
        except ImportError:
            error_msg = "sentence-transformers is not installed. Please install it manually: pip install sentence-transformers"
            logger.error(error_msg)
            if torch is None:
                logger.error("PyTorch is also missing, which is required by sentence-transformers")
            return None
        except Exception as e:
            error_msg = f"Failed to initialize sentence-transformers: {str(e)}"
            logger.error(error_msg)
            logger.error("Please check your installation and dependencies")
            return None
    return _model


def generate_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a given text using sentence-transformers.
    Uses caching to avoid regenerating embeddings for the same text.

    Args:
        text (str): The text to generate embedding for

    Returns:
        numpy.ndarray: The embedding vector
    """
    global _cache_hits, _cache_misses

    if not text or not isinstance(text, str):
        return np.zeros(384)  # Return zero vector for empty text

    # Clean and normalize the text
    text = text.strip()
    if not text:
        return np.zeros(384)

    # Check cache first
    text_hash = hash(text)
    if text_hash in _embedding_cache:
        _cache_hits += 1
        if _cache_hits % 100 == 0:
            logger.info(f"Embedding cache stats - Hits: {_cache_hits}, Misses: {_cache_misses}")
        return _embedding_cache[text_hash]

    _cache_misses += 1

    # Generate embedding
    model = get_model()

    if model is None:
        logger.warning("Model initialization failed. Returning zero vector.")
        return np.zeros(384)

    try:
        if torch is not None:
            with torch.no_grad():  # Disable gradient calculation for inference
                embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        else:
            embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)

        # Cache the result
        _embedding_cache[text_hash] = embedding

        # Limit cache size to prevent memory issues
        if len(_embedding_cache) > 10000:  # Arbitrary limit, adjust based on memory constraints
            # Remove oldest entries (simple approach)
            keys_to_remove = list(_embedding_cache.keys())[:1000]
            for key in keys_to_remove:
                del _embedding_cache[key]
            logger.info(f"Embedding cache pruned. New size: {len(_embedding_cache)}")

        return embedding
    except Exception as e:
        logger.warning(f"Error generating embedding: {str(e)}")
        return np.zeros(384)  # Fallback to zero vector on error

def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
    """
    Generate embeddings for a batch of texts efficiently.
    Uses caching and batching for better performance.

    Args:
        texts (List[str]): List of texts to generate embeddings for
        batch_size (int): Batch size for processing

    Returns:
        List[np.ndarray]: List of embedding vectors
    """
    if not texts:
        return []

    # Clean and normalize texts
    cleaned_texts = [text.strip() if isinstance(text, str) else "" for text in texts]

    # Check which texts are already in cache
    results = []
    texts_to_encode = []
    indices_to_encode = []

    for i, text in enumerate(cleaned_texts):
        if not text:
            results.append(np.zeros(384))
            continue

        text_hash = hash(text)
        if text_hash in _embedding_cache:
            results.append(_embedding_cache[text_hash])
        else:
            texts_to_encode.append(text)
            indices_to_encode.append(i)
            # Add placeholder
            results.append(None)

    # If all texts were in cache, return results
    if not texts_to_encode:
        return results

    # Generate embeddings for texts not in cache
    model = get_model()
    if model is None:
        # Fill remaining results with zero vectors
        for i in indices_to_encode:
            results[i] = np.zeros(384)
        return results

    try:
        # Process in batches for better performance
        all_embeddings = []
        for i in range(0, len(texts_to_encode), batch_size):
            batch_texts = texts_to_encode[i:i+batch_size]

            if torch is not None:
                with torch.no_grad():
                    batch_embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)
            else:
                batch_embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)

            # Handle single result case
            if len(batch_texts) == 1 and not isinstance(batch_embeddings, list):
                batch_embeddings = [batch_embeddings]

            all_embeddings.extend(batch_embeddings)

        # Update cache and results
        for i, idx in enumerate(indices_to_encode):
            embedding = all_embeddings[i] if i < len(all_embeddings) else np.zeros(384)
            text_hash = hash(cleaned_texts[idx])
            _embedding_cache[text_hash] = embedding
            results[idx] = embedding

        return results
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {str(e)}")
        # Fill remaining results with zero vectors
        for i in indices_to_encode:
            results[i] = np.zeros(384)
        return results

def generate_checklist_item_embedding(item: dict) -> np.ndarray:
    """
    Generate embedding for a checklist item by combining question and description.

    Args:
        item (dict): Checklist item with 'question' and 'description' fields

    Returns:
        numpy.ndarray: The embedding vector
    """
    if not isinstance(item, dict):
        return np.zeros(384)

    # Combine question and description for better semantic matching
    question = item.get('question', '')
    description = item.get('description', '')

    # Add category if available for better context
    category = item.get('category', '')

    # Combine all fields with proper weighting (question is most important)
    combined_text = f"{question} {description}"
    if category:
        combined_text = f"{category}: {combined_text}"

    return generate_embedding(combined_text)

def semantic_search(query_text: str, embeddings: List[Tuple[str, np.ndarray]], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Perform semantic search against a list of embeddings.

    Args:
        query_text (str): The query text
        embeddings (list): List of (id, embedding) tuples
        top_k (int): Number of top results to return

    Returns:
        list: List of (id, score) tuples for top matches
    """
    if not query_text or not embeddings:
        return []

    # Generate query embedding
    query_embedding = generate_embedding(query_text)

    # Ensure query embedding is valid
    if np.all(query_embedding == 0):
        return []

    # Extract IDs and embeddings
    ids = [item_id for item_id, _ in embeddings]
    item_embeddings = np.array([emb for _, emb in embeddings])

    # Vectorized cosine similarity calculation
    # 1. Normalize all vectors in one go
    query_norm = np.linalg.norm(query_embedding)
    if query_norm < 1e-10:
        return []

    query_embedding_normalized = query_embedding / query_norm

    # 2. Normalize all item embeddings
    item_norms = np.linalg.norm(item_embeddings, axis=1)
    valid_indices = item_norms >= 1e-10

    # 3. Calculate dot products (cosine similarities) in one operation
    similarities = np.zeros(len(embeddings))
    if np.any(valid_indices):
        # Only normalize valid embeddings to avoid division by zero
        normalized_embeddings = np.zeros_like(item_embeddings)
        normalized_embeddings[valid_indices] = item_embeddings[valid_indices] / item_norms[valid_indices, np.newaxis]

        # Calculate cosine similarities using dot product of normalized vectors
        similarities[valid_indices] = np.dot(normalized_embeddings[valid_indices], query_embedding_normalized)

    # 4. Get top k indices
    if len(similarities) <= top_k:
        top_indices = np.argsort(similarities)[::-1]
    else:
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

    # 5. Create result tuples
    results = [(ids[i], float(similarities[i])) for i in top_indices]

    return results