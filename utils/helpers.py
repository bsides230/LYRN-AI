from pathlib import Path

def _get_file_explanation(filepath: Path) -> str:
    """Heuristic logic to generate a short file explanation."""
    name = filepath.name.lower()
    ext = filepath.suffix.lower()

    if ext == '.py':
        if 'test' in name: return "Python test script"
        if 'manager' in name or 'controller' in name: return "Python management/controller logic"
        return "Python source file"
    if ext == '.js': return "JavaScript file"
    if ext == '.html': return "HTML structure"
    if ext == '.css': return "CSS stylesheet"
    if ext == '.json': return "JSON configuration/data file"
    if ext == '.csv': return "CSV data file"
    if ext == '.md': return "Markdown documentation"
    if ext == '.txt': return "Text file"
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico']: return "Image file"

    return "Unknown file type"
