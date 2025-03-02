import sys
import importlib.util
import pathlib
from typing import Dict, Optional, Any, Union, List
from dataclasses import dataclass
import mimetypes
import hashlib
from enum import Enum
import pickle
import os

class ContentType(Enum):
    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    CODE = "code"
    UNKNOWN = "unknown"

@dataclass
class FileMetadata:
    """Metadata for a file in the filesystem"""
    path: pathlib.Path
    relative_path: pathlib.Path
    size: int
    modified_time: float
    content_hash: str
    content_type: ContentType
    extension: str
    
    @property
    def module_name(self) -> str:
        """Generate a valid Python module name from the path"""
        # Replace non-alphanumeric chars with underscores and ensure valid identifier
        clean_name = ''.join(c if c.isalnum() else '_' for c in self.relative_path.as_posix())
        return f"{clean_name}_module"

class FileSystemMemory:
    """A system to load and manage files from a filesystem into addressable memory"""
    
    def __init__(self, root_dir: Union[str, pathlib.Path]):
        self.root_dir = pathlib.Path(root_dir).resolve()
        self.metadata_cache: Dict[str, FileMetadata] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.content_cache: Dict[str, Union[str, bytes]] = {}
        self.index_file = self.root_dir / '.fsmemory_index.pkl'
        
        # Define which extensions should be treated as text
        self.text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
        self.code_extensions = {'.py', '.js', '.java', '.c', '.cpp', '.h', '.cs', '.go', '.rs', '.php', '.rb'}
        
        # Initialize mimetypes
        mimetypes.init()
    
    def _get_content_type(self, path: pathlib.Path) -> ContentType:
        """Determine content type based on mimetype and extension"""
        ext = path.suffix.lower()
        if ext in self.code_extensions:
            return ContentType.CODE
        
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            return ContentType.UNKNOWN
        
        if mime_type.startswith('text/') or ext in self.text_extensions:
            return ContentType.TEXT
        elif mime_type.startswith('image/'):
            return ContentType.IMAGE
        elif mime_type.startswith('audio/'):
            return ContentType.AUDIO
        elif mime_type.startswith('video/'):
            return ContentType.VIDEO
        else:
            return ContentType.BINARY
    
    def _compute_file_hash(self, path: pathlib.Path) -> str:
        """Compute a SHA256 hash of file contents"""
        hasher = hashlib.sha256()
        
        # Read in chunks to handle large files
        with open(path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
                
        return hasher.hexdigest()
    
    def scan_directory(self, exclude_dirs: Optional[List[str]] = None) -> None:
        """Scan directory and create metadata for all files"""
        exclude_dirs = exclude_dirs or ['.git', '__pycache__', 'venv', '.env']
        
        for file_path in self.root_dir.rglob('*'):
            # Skip excluded directories
            if any(part in exclude_dirs for part in file_path.parts):
                continue
                
            if file_path.is_file():
                try:
                    # Create relative path for module naming
                    rel_path = file_path.relative_to(self.root_dir)
                    
                    # Get file stats
                    stats = file_path.stat()
                    
                    # Create metadata
                    metadata = FileMetadata(
                        path=file_path,
                        relative_path=rel_path,
                        size=stats.st_size,
                        modified_time=stats.st_mtime,
                        content_hash=self._compute_file_hash(file_path),
                        content_type=self._get_content_type(file_path),
                        extension=file_path.suffix.lower()
                    )
                    
                    # Store metadata using module name as key
                    self.metadata_cache[metadata.module_name] = metadata
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    def save_index(self) -> None:
        """Save the metadata index to disk"""
        with open(self.index_file, 'wb') as f:
            pickle.dump(self.metadata_cache, f)
    
    def load_index(self) -> bool:
        """Load metadata index from disk if it exists"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'rb') as f:
                    self.metadata_cache = pickle.load(f)
                return True
            except Exception as e:
                print(f"Error loading index: {e}")
        return False
    
    def get_file_content(self, module_name: str) -> Optional[Union[str, bytes]]:
        """Get file content, loading from disk if necessary"""
        # Check if already in cache
        if module_name in self.content_cache:
            return self.content_cache[module_name]
            
        # Get metadata
        metadata = self.metadata_cache.get(module_name)
        if not metadata:
            return None
            
        try:
            # Read content based on type
            if metadata.content_type in (ContentType.TEXT, ContentType.CODE):
                content = metadata.path.read_text(encoding='utf-8', errors='replace')
            else:
                content = metadata.path.read_bytes()
                
            # Cache content
            self.content_cache[module_name] = content
            return content
            
        except Exception as e:
            print(f"Error reading {metadata.path}: {e}")
            return None
    
    def generate_module_code(self, metadata: FileMetadata) -> str:
        """Generate Python code for the module based on file type"""
        # Create module template with metadata
        module_code = f'''"""
Auto-generated module for: {metadata.relative_path}
Content type: {metadata.content_type.value}
Size: {metadata.size} bytes
Last modified: {metadata.modified_time}
Hash: {metadata.content_hash}
"""

import sys
from pathlib import Path

# File metadata
FILE_PATH = "{metadata.path}"
RELATIVE_PATH = "{metadata.relative_path}"
CONTENT_TYPE = "{metadata.content_type.value}" 
FILE_SIZE = {metadata.size}
EXTENSION = "{metadata.extension}"

# Functions to access content
def get_path():
    return Path("{metadata.path}")

def get_metadata():
    return {{
        "path": "{metadata.path}",
        "relative_path": "{metadata.relative_path}",
        "size": {metadata.size},
        "modified_time": {metadata.modified_time},
        "content_hash": "{metadata.content_hash}",
        "content_type": "{metadata.content_type.value}",
        "extension": "{metadata.extension}"
    }}
'''

        # Add content based on type
        if metadata.content_type in (ContentType.TEXT, ContentType.CODE):
            try:
                # Read text content and escape properly for triple quotes
                content = metadata.path.read_text(encoding='utf-8', errors='replace')
                escaped_content = content.replace('"""', '\\"\\"\\"')
                
                # Add content as string
                module_code += f'''
# File content as string
CONTENT = """
{escaped_content}
"""

def get_content():
    return CONTENT
'''
            except Exception as e:
                module_code += f'''
# Error reading content: {e}
CONTENT = ""

def get_content():
    with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()
'''
        else:
            # For binary files, provide loader function
            module_code += f'''
# Binary content - provide loader function
CONTENT = None

def get_content():
    with open(FILE_PATH, 'rb') as f:
        return f.read()
'''

        # Add instant-firing lambda
        module_code += f'''
# State tracking
__quantum_state__ = "SUPERPOSITION"

# Instant-firing function on module load
@lambda _: _()
def __on_load__():
    global __quantum_state__
    __quantum_state__ = "COLLAPSED"
    return True
'''
        return module_code
    
    def load_module(self, module_name: str) -> Optional[Any]:
        """Load a module for a file dynamically"""
        # Skip if already loaded
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
            
        # Get metadata
        metadata = self.metadata_cache.get(module_name)
        if not metadata:
            return None
            
        try:
            # Generate code for the module
            module_code = self.generate_module_code(metadata)
            
            # Create module spec
            spec = importlib.machinery.ModuleSpec(
                name=module_name, 
                loader=importlib.machinery.SourceFileLoader(module_name, str(metadata.path))
            )
            
            # Create module
            module = importlib.util.module_from_spec(spec)
            
            # Execute module code
            exec(module_code, module.__dict__)
            
            # Add to sys.modules
            sys.modules[module_name] = module
            
            # Cache module
            self.loaded_modules[module_name] = module
            
            return module
            
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return None
    
    def load_all_modules(self) -> Dict[str, Any]:
        """Load all files as modules"""
        for module_name in self.metadata_cache:
            self.load_module(module_name)
        return self.loaded_modules
    
    def get_modules_by_type(self, content_type: ContentType) -> List[str]:
        """Get module names for a specific content type"""
        return [
            module_name for module_name, metadata in self.metadata_cache.items()
            if metadata.content_type == content_type
        ]


def main():
    # Get invocation directory
    invoke_dir = pathlib.Path(__file__).resolve().parent
    
    # Create file system memory
    fs_memory = FileSystemMemory(invoke_dir)
    
    # Try to load existing index
    if not fs_memory.load_index():
        print(f"Scanning directory: {invoke_dir}")
        fs_memory.scan_directory()
        fs_memory.save_index()
    
    # Load all as modules
    modules = fs_memory.load_all_modules()
    
    # Add to global namespace
    for name, module in modules.items():
        globals()[name] = module
    
    # Show loaded modules
    print(f"Loaded {len(modules)} modules:")
    for name in sorted(modules.keys()):
        metadata = fs_memory.metadata_cache[name]
        print(f"  {name} ({metadata.content_type.value}) - {metadata.relative_path}")
    
    # Return modules for interactive use
    return fs_memory

if __name__ == "__main__":
    fs_memory = main()