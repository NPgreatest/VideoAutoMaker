def split_script_to_chunks(script):
    # Simple sentence splitter by newline or punctuation
    import re
    raw_chunks = re.split(r'[\n]', script)
    return [chunk.strip() for chunk in raw_chunks if chunk.strip()]