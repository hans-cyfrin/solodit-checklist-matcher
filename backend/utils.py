def clean_json_response(raw_response: str) -> str:
    """
    Clean and extract valid JSON from a raw text response.
    
    Args:
        raw_response (str): Raw text that may contain JSON
        
    Returns:
        str: Cleaned text containing only the JSON portion
    """
    # Remove any text before the first '['
    start_idx = raw_response.find('[')
    if start_idx == -1:
        # If no array found, look for single object
        start_idx = raw_response.find('{')
    if start_idx != -1:
        raw_response = raw_response[start_idx:]

    # Remove any text after the last ']' or '}'
    end_idx = max(raw_response.rfind(']'), raw_response.rfind('}')) + 1
    if end_idx > 0:
        raw_response = raw_response[:end_idx]

    # Fix common JSON formatting issues
    raw_response = raw_response.replace('\\n', ' ')
    raw_response = raw_response.replace('\n', ' ')
    raw_response = raw_response.replace('""', '"')
    raw_response = raw_response.replace(',,', ',')

    return raw_response