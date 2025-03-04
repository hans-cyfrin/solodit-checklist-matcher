#!/usr/bin/env python3
"""
Demonstration script for the embeddings module.
This script shows how to use the embeddings module for semantic search.
"""

import logging
import time
import numpy as np
from embeddings import (
    generate_embedding,
    generate_embeddings_batch,
    generate_checklist_item_embedding,
    semantic_search
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_single_embedding():
    """Demonstrate generating a single embedding"""
    logger.info("Generating a single embedding...")
    
    text = "Smart contract reentrancy vulnerability in the withdraw function"
    start_time = time.time()
    embedding = generate_embedding(text)
    elapsed = time.time() - start_time
    
    logger.info(f"Generated embedding with shape {embedding.shape} in {elapsed:.2f} seconds")
    logger.info(f"First 5 values: {embedding[:5]}")
    
    return embedding

def demo_batch_embedding():
    """Demonstrate batch embedding generation"""
    logger.info("Generating batch embeddings...")
    
    texts = [
        "Reentrancy vulnerability in withdraw function",
        "Integer overflow in token transfer",
        "Unchecked return value from external call",
        "Missing access control on critical function",
        "Flash loan attack vulnerability"
    ]
    
    start_time = time.time()
    embeddings = generate_embeddings_batch(texts)
    elapsed = time.time() - start_time
    
    logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f} seconds")
    logger.info(f"Average time per embedding: {elapsed/len(embeddings):.4f} seconds")
    
    return embeddings

def demo_checklist_item_embedding():
    """Demonstrate generating an embedding for a checklist item"""
    logger.info("Generating checklist item embedding...")
    
    item = {
        "id": "SOL-SEC-01",
        "question": "Is the contract vulnerable to reentrancy?",
        "description": "Check if the contract has proper reentrancy guards and follows the checks-effects-interactions pattern",
        "category": "Security"
    }
    
    embedding = generate_checklist_item_embedding(item)
    logger.info(f"Generated checklist item embedding with shape {embedding.shape}")
    
    return embedding

def demo_semantic_search():
    """Demonstrate semantic search functionality"""
    logger.info("Performing semantic search...")
    
    # Create sample checklist items
    checklist_items = [
        {
            "id": "SOL-SEC-01",
            "question": "Is the contract vulnerable to reentrancy?",
            "description": "Check if the contract has proper reentrancy guards and follows the checks-effects-interactions pattern",
            "category": "Security"
        },
        {
            "id": "SOL-SEC-02",
            "question": "Is the contract vulnerable to integer overflow/underflow?",
            "description": "Check if the contract uses SafeMath or Solidity 0.8+ for arithmetic operations",
            "category": "Security"
        },
        {
            "id": "SOL-SEC-03",
            "question": "Does the contract check return values from external calls?",
            "description": "Ensure that the contract properly checks return values from external calls and handles failures",
            "category": "Security"
        },
        {
            "id": "SOL-SEC-04",
            "question": "Does the contract implement proper access control?",
            "description": "Verify that critical functions have appropriate access control mechanisms",
            "category": "Security"
        },
        {
            "id": "SOL-SEC-05",
            "question": "Is the contract vulnerable to flash loan attacks?",
            "description": "Check if the contract is resilient against price manipulation via flash loans",
            "category": "Security"
        }
    ]
    
    # Generate embeddings for checklist items
    logger.info("Generating embeddings for checklist items...")
    start_time = time.time()
    
    item_embeddings = []
    for item in checklist_items:
        embedding = generate_checklist_item_embedding(item)
        item_embeddings.append((item["id"], embedding))
    
    elapsed = time.time() - start_time
    logger.info(f"Generated embeddings for {len(checklist_items)} items in {elapsed:.2f} seconds")
    
    # Perform semantic search
    query = "The withdraw function doesn't follow checks-effects-interactions pattern and can be exploited"
    logger.info(f"Searching for: '{query}'")
    
    start_time = time.time()
    matches = semantic_search(query, item_embeddings, top_k=3)
    elapsed = time.time() - start_time
    
    logger.info(f"Search completed in {elapsed:.4f} seconds")
    
    # Display results
    logger.info("Search results:")
    for i, (item_id, score) in enumerate(matches, 1):
        # Find the matching item
        item = next(item for item in checklist_items if item["id"] == item_id)
        logger.info(f"{i}. {item_id}: {item['question']} (Score: {score:.4f})")
    
    return matches

if __name__ == "__main__":
    logger.info("Starting embeddings module demonstration...")
    
    try:
        # Run demonstrations
        demo_single_embedding()
        print()
        
        demo_batch_embedding()
        print()
        
        demo_checklist_item_embedding()
        print()
        
        demo_semantic_search()
        
        logger.info("Demonstration completed successfully!")
    except Exception as e:
        logger.error(f"Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc() 