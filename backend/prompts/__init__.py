import os
from pathlib import Path

def load_prompt(prompt_path: str) -> str:
    """
    Load a prompt from a file.
    
    Args:
        prompt_path: Path to the prompt file relative to the prompts directory
        
    Returns:
        The prompt text
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    base_path = Path(__file__).parent
    full_path = base_path / prompt_path

    if not full_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(full_path, 'r') as f:
        return f.read().strip()

# Pre-load all prompts
PROMPTS = {
    'generate': load_prompt('checklist/generate.txt'),
    'validate': load_prompt('checklist/validate.txt'),
    'improve': load_prompt('checklist/improve.txt')
}