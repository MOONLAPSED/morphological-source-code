from __future__ import annotations
import sys
import ast
import os
import pathlib
import importlib.util
import hashlib
import mimetypes
import json
from typing import Dict, Any, Optional, List, Set, Union, Tuple
from dataclasses import dataclass, field
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
import logging
import atexit
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentType(Enum):
    TEXT = auto()
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()
    BINARY = auto()
    PYTHON = auto()
    OTHER = auto()

@dataclass
class ContentMetadata:
    """Metadata for any file in the system"""
    path: pathlib.Path
    relative_path: pathlib.Path  # Path relative to root
    file_size: int
    last_modified: float
    content_hash: str
    mime_type: str
    content_type: ContentType
    extension: str
    is_loadable: bool = False  # Can be loaded as a Python module

@dataclass
class FileSystem:
    """Manager for the real filesystem content"""
    root_dir: pathlib.Path
    exclude_dirs: Set[str] = field(default_factory=lambda: {'.git', '__pycache__', '.venv', 'node_modules'})
    exclude_files: Set[str] = field(default_factory=lambda: {'.DS_Store', 'thumbs.db'})
    max_workers: int = 8
    chunk_size: int = 1024 * 1024  # 1MB for reading large files
    max_cache_size: int = 100 * 1024 * 1024  # 100MB default max cache size
    metadata_cache: Dict[str, ContentMetadata] = field(default_factory=dict)
    content_cache: Dict[str, Any] = field(default_factory=dict)
    content_cache_size: int = field(default_factory=int)  # Current cache size in bytes
    loaded_modules: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _executor: ThreadPoolExecutor = None
    _file_watchers: Dict[str, float] = field(default_factory=dict)  # Path -> last check time

    def __post_init__(self):
        """Initialize the ThreadPoolExecutor and other setup"""
        # Initialize executor
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        # Register shutdown at exit
        atexit.register(self._shutdown_executor)
        
        # Ensure root directory exists and is absolute
        self.root_dir = pathlib.Path(self.root_dir).resolve()
        if not self.root_dir.exists():
            raise FileNotFoundError(f"Root directory {self.root_dir} does not exist")
        
        # Initialize mimetypes
        mimetypes.init()

    def _shutdown_executor(self):
        """Ensure executor is properly shut down"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def scan_directory(self, refresh: bool = False) -> None:
        """Scan the directory tree and build metadata cache"""
        if self.metadata_cache and not refresh:
            logger.info(f"Using cached metadata for {len(self.metadata_cache)} files")
            return

        logger.info(f"Scanning directory: {self.root_dir}")
        scanned_paths = []
        
        for file_path in self.root_dir.rglob('*'):
            # Skip excluded directories and files
            if any(part in self.exclude_dirs for part in file_path.parts):
                continue
            if file_path.name in self.exclude_files:
                continue
            
            if file_path.is_file():
                scanned_paths.append(file_path)
        
        # Process files in parallel
        futures = [self._executor.submit(self._process_file, path) for path in scanned_paths]
        for future in futures:
            try:
                metadata = future.result()
                if metadata:
                    rel_path_str = str(metadata.relative_path)
                    with self._lock:
                        self.metadata_cache[rel_path_str] = metadata
            except Exception as e:
                logger.error(f"Error processing file future: {e}")
        
        logger.info(f"Indexed {len(self.metadata_cache)} files")

    def _process_file(self, file_path: pathlib.Path) -> Optional[ContentMetadata]:
        """Process a single file and create metadata"""
        try:
            stat = file_path.stat()
            rel_path = file_path.relative_to(self.root_dir)
            
            # Determine content type
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or 'application/octet-stream'
            
            # Determine content classification
            content_type = self._classify_content(file_path, mime_type)
            
            # Compute hash for smaller files, use sampled hash for larger ones
            content_hash = ""
            if stat.st_size < 10 * 1024 * 1024:  # 10MB
                content_hash = self._compute_file_hash(file_path, sample_only=False)
            else:
                content_hash = self._compute_file_hash(file_path, sample_only=True)
            
            # Check if file can be loaded as Python module
            is_loadable = self._is_loadable(file_path)
            
            return ContentMetadata(
                path=file_path,
                relative_path=rel_path,
                file_size=stat.st_size,
                last_modified=stat.st_mtime,
                content_hash=content_hash,
                mime_type=mime_type,
                content_type=content_type,
                extension=file_path.suffix.lower(),
                is_loadable=is_loadable
            )
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None

    def _classify_content(self, file_path: pathlib.Path, mime_type: str) -> ContentType:
        """Classify file content type using more robust methods"""
        # First, check extension for Python files
        if file_path.suffix.lower() == '.py':
            return ContentType.PYTHON
        
        # Then check MIME type
        if mime_type:
            if mime_type.startswith('text/'):
                return ContentType.TEXT
            if mime_type.startswith('image/'):
                return ContentType.IMAGE
            if mime_type.startswith('audio/'):
                return ContentType.AUDIO
            if mime_type.startswith('video/'):
                return ContentType.VIDEO
        
        # Last resort: analyze content for text vs binary
        if file_path.stat().st_size < 2 * 1024 * 1024:  # 2MB max for text detection
            if self._is_likely_text(file_path):
                return ContentType.TEXT
        
        return ContentType.BINARY

    def _is_likely_text(self, file_path: pathlib.Path) -> bool:
        """More robust text file detection"""
        try:
            # Read a sample of the file
            with open(file_path, 'rb') as f:
                sample = f.read(4096)  # Read 4KB sample
                
            if not sample:  # Empty file
                return True
                
            # Check for NULL bytes (common in binary files)
            if b'\x00' in sample:
                return False
                
            # Count printable ASCII and common whitespace characters
            printable_count = sum(32 <= b <= 126 or b in (9, 10, 13) for b in sample)
            if len(sample) == 0:
                return True
            return printable_count / len(sample) > 0.8  # 80% threshold
        except Exception as e:
            logger.warning(f"Error detecting text for {file_path}: {e}")
            return False

    def _compute_file_hash(self, file_path: pathlib.Path, sample_only: bool = False) -> str:
        """Compute SHA-256 hash of file contents with sampling option for large files"""
        hasher = hashlib.sha256()
        file_size = file_path.stat().st_size
        
        try:
            with open(file_path, 'rb') as f:
                if sample_only and file_size > 10 * 1024 * 1024:
                    # Sample beginning, middle, and end for large files
                    # First 1MB
                    f.seek(0)
                    hasher.update(f.read(1024 * 1024))
                    
                    # Middle 1MB
                    middle_pos = file_size // 2 - 512 * 1024  # Middle position
                    f.seek(max(0, middle_pos))
                    hasher.update(f.read(1024 * 1024))
                    
                    # Last 1MB
                    f.seek(max(0, file_size - 1024 * 1024))
                    hasher.update(f.read(1024 * 1024))
                    
                    # Add size and mtime info to the hash for completeness
                    hasher.update(f"size:{file_size}-mtime:{file_path.stat().st_mtime}".encode())
                else:
                    # Full hash for smaller files
                    for chunk in iter(lambda: f.read(self.chunk_size), b''):
                        hasher.update(chunk)
                        
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            return f"error:{str(e)}"

    def _is_loadable(self, file_path: pathlib.Path) -> bool:
        """Check if file can be loaded as a Python module"""
        if file_path.suffix.lower() == '.py':
            return True
        # Additional checks could be added here for other loadable formats
        return False

    def _manage_cache_size(self, new_content_size: int = 0) -> None:
        """Manage cache size, evicting items if necessary"""
        with self._lock:
            # If adding new content would exceed max size, evict oldest items
            if self.content_cache_size + new_content_size > self.max_cache_size:
                items = [(k, v) for k, v in self.content_cache.items()]
                # Sort by access time (assuming content is strings)
                items.sort(key=lambda x: len(x[1]) if isinstance(x[1], (str, bytes)) else 0)
                
                # Evict until we have enough space
                space_needed = (self.content_cache_size + new_content_size) - self.max_cache_size
                space_freed = 0
                evicted_count = 0
                
                for k, v in items:
                    item_size = len(v) if isinstance(v, (str, bytes)) else 0
                    if space_freed >= space_needed:
                        break
                        
                    del self.content_cache[k]
                    space_freed += item_size
                    evicted_count += 1
                    
                self.content_cache_size -= space_freed
                if evicted_count > 0:
                    logger.debug(f"Evicted {evicted_count} items from cache, freed {space_freed} bytes")

    def _check_file_changed(self, rel_path: str) -> bool:
        """Check if a file has changed on disk since last loaded"""
        metadata = self.metadata_cache.get(rel_path)
        if not metadata:
            return True  # If no metadata, consider changed
            
        try:
            current_mtime = metadata.path.stat().st_mtime
            return current_mtime > metadata.last_modified
        except Exception:
            return True  # If error accessing file, consider changed

    def load_content(self, rel_path: Union[str, pathlib.Path], force_reload: bool = False) -> Optional[Any]:
        """Load file content, with caching and change detection"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        
        # Check if file has changed if in cache
        if rel_path_str in self.content_cache and not force_reload:
            # Periodically check if file has changed on disk (not every access)
            now = time.time()
            last_check = self._file_watchers.get(rel_path_str, 0)
            
            if now - last_check > 5.0:  # Check every 5 seconds max
                self._file_watchers[rel_path_str] = now
                if self._check_file_changed(rel_path_str):
                    logger.info(f"File changed on disk: {rel_path_str}")
                    force_reload = True
                    # Update metadata too
                    if rel_path_str in self.metadata_cache:
                        metadata = self.metadata_cache[rel_path_str]
                        self._executor.submit(self._refresh_metadata, metadata.path)
            
            if not force_reload:
                return self.content_cache[rel_path_str]
        
        metadata = self.metadata_cache.get(rel_path_str)
        if not metadata:
            logger.warning(f"No metadata found for {rel_path_str}")
            return None
        
        content = None
        try:
            if metadata.content_type == ContentType.TEXT or metadata.content_type == ContentType.PYTHON:
                with open(metadata.path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Cache text content
                with self._lock:
                    # Check if this would exceed cache size
                    content_size = len(content) if content else 0
                    self._manage_cache_size(content_size)
                    
                    self.content_cache[rel_path_str] = content
                    self.content_cache_size += content_size
                    
            elif metadata.content_type == ContentType.BINARY:
                # For binary files, optionally cache based on size
                with open(metadata.path, 'rb') as f:
                    content = f.read()
                
                # Only cache smaller binary files
                if metadata.file_size < 1024 * 1024:  # 1MB threshold for binary caching
                    with self._lock:
                        self._manage_cache_size(len(content))
                        self.content_cache[rel_path_str] = content
                        self.content_cache_size += len(content)
                        
            else:
                # For other types, read but don't cache
                with open(metadata.path, 'rb') as f:
                    content = f.read()
                    
            return content
        except Exception as e:
            logger.error(f"Error loading content for {rel_path_str}: {e}")
            return None

    def _refresh_metadata(self, file_path: pathlib.Path) -> None:
        """Refresh metadata for a single file"""
        try:
            metadata = self._process_file(file_path)
            if metadata:
                rel_path_str = str(metadata.relative_path)
                with self._lock:
                    self.metadata_cache[rel_path_str] = metadata
                logger.debug(f"Refreshed metadata for {rel_path_str}")
        except Exception as e:
            logger.error(f"Error refreshing metadata for {file_path}: {e}")

    def load_module(self, rel_path: Union[str, pathlib.Path], force_reload: bool = False) -> Optional[Any]:
        """Load a Python module from a file"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        
        # Return from cache if available and not force_reload
        if rel_path_str in self.loaded_modules and not force_reload:
            # Check if file has changed
            if self._check_file_changed(rel_path_str):
                logger.info(f"Module source changed on disk: {rel_path_str}")
                force_reload = True
            else:
                return self.loaded_modules[rel_path_str]
        
        metadata = self.metadata_cache.get(rel_path_str)
        if not metadata or not metadata.is_loadable:
            logger.warning(f"File {rel_path_str} cannot be loaded as a module")
            return None
        
        try:
            # Create a unique and valid module name from the relative path
            path_parts = metadata.relative_path.parts
            module_name = f"fs_module_{'_'.join(path_parts)}"
            
            # Remove invalid characters and ensure it's a valid identifier
            module_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in module_name)
            
            # Try to load the module
            spec = importlib.util.spec_from_file_location(module_name, str(metadata.path))
            if spec is None or spec.loader is None:
                logger.error(f"Could not create module spec for {rel_path_str}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            # Remove from sys.modules if reloading
            if module_name in sys.modules and force_reload:
                del sys.modules[module_name]
                
            sys.modules[module_name] = module  # Add to sys.modules
            
            # Inject metadata into module
            module.__file_metadata__ = metadata
            
            # Execute the module
            spec.loader.exec_module(module)
            
            # Cache the module
            with self._lock:
                self.loaded_modules[rel_path_str] = module
                
            return module
        except Exception as e:
            logger.error(f"Error loading module {rel_path_str}: {e}", exc_info=True)
            return None

    def generate_content_module(self, rel_path: Union[str, pathlib.Path]) -> Optional[str]:
        """Generate a Python module string for non-Python content"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        metadata = self.metadata_cache.get(rel_path_str)
        
        if not metadata:
            logger.warning(f"No metadata found for {rel_path_str}")
            return None
        
        if metadata.content_type == ContentType.PYTHON:
            # Just return the original content for Python files
            return self.load_content(rel_path_str)
        
        # For text files
        if metadata.content_type == ContentType.TEXT:
            content = self.load_content(rel_path_str)
            if content is None:
                return None
                
            # Escape triple quotes in content
            content = content.replace('"""', '\\"\\"\\"')
            
            return f'''"""
Auto-generated content module for: {metadata.relative_path}
Content type: {metadata.content_type.name}
MIME type: {metadata.mime_type}
File size: {metadata.file_size} bytes
Last modified: {metadata.last_modified}
"""

# File metadata
FILE_PATH = "{metadata.path}"
RELATIVE_PATH = "{metadata.relative_path}"
CONTENT_TYPE = "{metadata.content_type.name}"
MIME_TYPE = "{metadata.mime_type}"

# Original content as string
CONTENT = """
{content}
"""

# Quantum state marker
__quantum_state__ = "SUPERPOSITION"

def get_content() -> str:
    """Returns the original content."""
    return CONTENT

def get_metadata() -> dict:
    """Returns metadata about the file."""
    return {{
        "path": "{metadata.path}",
        "relative_path": "{metadata.relative_path}",
        "file_size": {metadata.file_size},
        "last_modified": {metadata.last_modified},
        "content_type": "{metadata.content_type.name}",
        "mime_type": "{metadata.mime_type}"
    }}

# Immediate execution upon loading
@lambda _: _()
def __quantum_collapse__():
    global __quantum_state__
    __quantum_state__ = "COLLAPSED"
    return True
'''
        
        # For binary files, just include metadata and methods to load content
        return f'''"""
Auto-generated content module for: {metadata.relative_path}
Content type: {metadata.content_type.name}
MIME type: {metadata.mime_type}
File size: {metadata.file_size} bytes
Last modified: {metadata.last_modified}
"""

# File metadata
FILE_PATH = "{metadata.path}"
RELATIVE_PATH = "{metadata.relative_path}"
CONTENT_TYPE = "{metadata.content_type.name}"
MIME_TYPE = "{metadata.mime_type}"

# Binary content not included in module
def get_content_bytes() -> bytes:
    """Load and return binary content."""
    with open("{metadata.path}", "rb") as f:
        return f.read()
        
def get_content_chunk(start: int = 0, size: int = 1024 * 1024) -> bytes:
    """Load and return a chunk of binary content."""
    with open("{metadata.path}", "rb") as f:
        f.seek(start)
        return f.read(size)
        
def get_metadata() -> dict:
    """Returns metadata about the file."""
    return {{
        "path": "{metadata.path}",
        "relative_path": "{metadata.relative_path}",
        "file_size": {metadata.file_size},
        "last_modified": {metadata.last_modified},
        "content_type": "{metadata.content_type.name}",
        "mime_type": "{metadata.mime_type}"
    }}

# Immediate execution upon loading
@lambda _: _()
def __quantum_collapse__():
    global __quantum_state__
    __quantum_state__ = "COLLAPSED"
    return True
'''

    def create_dynamic_module(self, rel_path: Union[str, pathlib.Path]) -> Optional[Any]:
        """Create a dynamic module for any file, even non-Python files"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        
        # Check if we already have this module and it's up to date
        if rel_path_str in self.loaded_modules:
            if not self._check_file_changed(rel_path_str):
                return self.loaded_modules[rel_path_str]
            else:
                logger.info(f"Dynamic module source changed: {rel_path_str}")
            
        metadata = self.metadata_cache.get(rel_path_str)
        if not metadata:
            logger.warning(f"No metadata found for {rel_path_str}")
            return None
            
        # For Python files, load normally
        if metadata.is_loadable:
            return self.load_module(rel_path_str, force_reload=True)
            
        # Generate module content for non-Python files
        module_code = self.generate_content_module(rel_path_str)
        if not module_code:
            return None
            
        # Create a unique module name
        path_parts = metadata.relative_path.parts
        module_name = f"fs_content_{'_'.join(path_parts)}"
        module_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in module_name)
        
        # Clean up old module if reloading
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # Create module
        module = type(sys)(module_name)
        module.__file__ = str(metadata.path)
        module.__file_metadata__ = metadata
        
        # Execute the generated code in the module's namespace
        try:
            exec(module_code, module.__dict__)
            
            # Store in the loaded modules cache
            with self._lock:
                self.loaded_modules[rel_path_str] = module
                
            return module
        except Exception as e:
            logger.error(f"Error creating dynamic module for {rel_path_str}: {e}")
            return None

    def _format_file_info(self, path: pathlib.Path, metadata: ContentMetadata) -> Dict[str, Any]:
        """Format file information for listings"""
        return {
            "name": path.name,
            "path": str(path),
            "size": metadata.file_size,
            "type": metadata.content_type.name,
            "mime_type": metadata.mime_type,
            "last_modified": metadata.last_modified,
            "is_loadable": metadata.is_loadable
        }

    def get_file_listing(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get a listing of files with metadata in the specified directory"""
        result = []
        
        # Convert directory path to Path object, using root if None
        prefix = pathlib.Path(directory) if directory else pathlib.Path("")
        
        for rel_path_str, metadata in self.metadata_cache.items():
            path = pathlib.Path(rel_path_str)
            
            # Files in the requested directory (or root)
            if directory is None and path.parent == pathlib.Path(""):
                # Root directory files
                result.append(self._format_file_info(path, metadata))
            elif directory is not None and path.parent == prefix:
                # Files in specific directory
                result.append(self._format_file_info(path, metadata))
                
        # Sort by name
        result.sort(key=lambda x: x["name"])
        return result
    
    def get_directory_tree(self) -> Dict[str, Any]:
        """Generate a nested tree representation of the filesystem"""
        root = {"name": self.root_dir.name, "type": "directory", "children": {}}
        
        for rel_path_str, metadata in self.metadata_cache.items():
            current = root
            path = pathlib.Path(rel_path_str)
            parts = path.parts
            
            # Build the directory structure
            for i, part in enumerate(parts[:-1]):
                if part not in current["children"]:
                    current["children"][part] = {"name": part, "type": "directory", "children": {}}
                current = current["children"][part]
            
            # Add the file
            filename = parts[-1] if parts else path.name
            current["children"][filename] = {
                "name": filename,
                "type": "file",
                "content_type": metadata.content_type.name,
                "size": metadata.file_size,
                "is_loadable": metadata.is_loadable
            }
            
        return root
    
    def search_files(self, query: str, content_search: bool = False) -> List[Dict[str, Any]]:
        """Search for files by name and/or content"""
        results = []
        query = query.lower()
        
        for rel_path_str, metadata in self.metadata_cache.items():
            match_types = []
            
            # Search in filename
            if query in str(metadata.relative_path).lower():
                match_types.append("filename")
                
            # Search in content for text files if requested
            if content_search and metadata.content_type in [ContentType.TEXT, ContentType.PYTHON]:
                content = self.load_content(rel_path_str)
                if content and query in content.lower():
                    match_types.append("content")
                    
            # Add to results if any matches found
            if match_types:
                results.append({
                    "path": str(metadata.relative_path),
                    "match_types": match_types,
                    "metadata": {
                        "size": metadata.file_size,
                        "type": metadata.content_type.name,
                        "mime_type": metadata.mime_type
                    }
                })
                    
        return results
    
    def find_similar_files(self, target_path: Union[str, pathlib.Path], threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find files similar to the target file by name, extension, and size"""
        target_path_str = str(target_path) if isinstance(target_path, pathlib.Path) else target_path
        target_metadata = self.metadata_cache.get(target_path_str)
        
        if not target_metadata:
            logger.warning(f"No metadata found for target file: {target_path_str}")
            return []
            
        target_name = target_metadata.path.stem.lower()
        target_ext = target_metadata.extension.lower()
        target_size = target_metadata.file_size
        
        results = []
        for rel_path_str, metadata in self.metadata_cache.items():
            if rel_path_str == target_path_str:
                continue  # Skip the target file itself
                
            name = metadata.path.stem.lower()
            ext = metadata.extension.lower()
            
            # Calculate similarity score
            score = 0.0
            
            # Same extension: +0.3
            if ext == target_ext:
                score += 0.3
                
            # Similar name: up to +0.4
            name_similarity = self._calculate_string_similarity(name, target_name)
            score += name_similarity * 0.4
            
            # Similar size: up to +0.3
            if target_size > 0 and metadata.file_size > 0:
                size_ratio = min(target_size, metadata.file_size) / max(target_size, metadata.file_size)
                score += size_ratio * 0.3
            
            if score >= threshold:
                results.append({
                    "path": str(metadata.relative_path),
                    "similarity_score": round(score, 2),
                    "metadata": {
                        "size": metadata.file_size,
                        "type": metadata.content_type.name,
                    }
                })
                
        # Sort by similarity score, descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results
        
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity ratio"""
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
            
        # Simple Levenshtein-inspired approach
        m = len(str1)
        n = len(str2)
        
        # Initialize matrix of zeros
        d = [[0 for _ in range(n+1)] for _ in range(m+1)]
        
        # Source prefixes can be transformed into empty string by dropping chars
        for i in range(1, m+1):
            d[i][0] = i
            
        # Target prefixes can be reached from empty source by inserting chars
        for j in range(1, n+1):
            d[0][j] = j
            
        for j in range(1, n+1):
            for i in range(1, m+1):
                if str1[i-1] == str2[j-1]:
                    # If the characters match
                    d[i][j] = d[i-1][j-1]
                else:
                    # If they don't match, take min of delete, insert, substitute
                    d[i][j] = min(d[i-1][j] + 1,      # deletion
                                  d[i][j-1] + 1,      # insertion
                                  d[i-1][j-1] + 1)    # substitution

        # Convert edit distance to similarity ratio
        max_len = max(m, n)
        if max_len == 0:
            return 1.0
        similarity = 1.0 - (d[m][n] / max_len)
        return similarity
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the filesystem"""
        content_type_counts = {}
        extension_counts = {}
        total_size = 0
        largest_file_size = 0
        largest_file_path = ""
        
        for rel_path_str, metadata in self.metadata_cache.items():
            # Content type stats
            content_type = metadata.content_type.name
            content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            # Extension stats
            ext = metadata.extension
            if ext:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
                
            # Size stats
            total_size += metadata.file_size
            if metadata.file_size > largest_file_size:
                largest_file_size = metadata.file_size
                largest_file_path = str(metadata.relative_path)
                
        return {
            "total_files": len(self.metadata_cache),
            "content_types": content_type_counts,
            "extensions": extension_counts,
            "total_size_bytes": total_size,
            "largest_file": {
                "path": largest_file_path,
                "size_bytes": largest_file_size
            },
            "cache_stats": {
                "metadata_cache_size": len(self.metadata_cache),
                "content_cache_size_bytes": self.content_cache_size,
                "loaded_modules": len(self.loaded_modules)
            }
        }

    def create_file(self, rel_path: Union[str, pathlib.Path], content: Union[str, bytes]) -> bool:
        """Create a new file with the given content"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        file_path = self.root_dir / pathlib.Path(rel_path_str)
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write content based on type
            if isinstance(content, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            # Update metadata cache
            self._executor.submit(self._process_file, file_path)
            return True
        except Exception as e:
            logger.error(f"Error creating file {rel_path_str}: {e}")
            return False

    def update_file(self, rel_path: Union[str, pathlib.Path], content: Union[str, bytes]) -> bool:
        """Update an existing file with new content"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        file_path = self.root_dir / pathlib.Path(rel_path_str)
        
        if not file_path.exists():
            logger.warning(f"File {rel_path_str} does not exist for update")
            return False
            
        try:
            # Write content based on type
            if isinstance(content, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            # Update cache entries
            with self._lock:
                if rel_path_str in self.content_cache:
                    # Update content cache size tracking
                    old_size = len(self.content_cache[rel_path_str]) if isinstance(self.content_cache[rel_path_str], (str, bytes)) else 0
                    new_size = len(content)
                    self.content_cache_size = self.content_cache_size - old_size + new_size
                    self.content_cache[rel_path_str] = content
                
                # Remove from loaded modules to force reload
                if rel_path_str in self.loaded_modules:
                    del self.loaded_modules[rel_path_str]
            
            # Update metadata async
            self._executor.submit(self._refresh_metadata, file_path)
            return True
        except Exception as e:
            logger.error(f"Error updating file {rel_path_str}: {e}")
            return False

    def delete_file(self, rel_path: Union[str, pathlib.Path]) -> bool:
        """Delete a file from the filesystem"""
        rel_path_str = str(rel_path) if isinstance(rel_path, pathlib.Path) else rel_path
        file_path = self.root_dir / pathlib.Path(rel_path_str)
        
        if not file_path.exists():
            logger.warning(f"File {rel_path_str} does not exist for deletion")
            return False
            
        try:
            # Delete the file
            file_path.unlink()
            
            # Update caches
            with self._lock:
                # Update content cache size tracking if in cache
                if rel_path_str in self.content_cache:
                    content = self.content_cache[rel_path_str]
                    self.content_cache_size -= len(content) if isinstance(content, (str, bytes)) else 0
                    del self.content_cache[rel_path_str]
                
                # Remove from other caches
                if rel_path_str in self.metadata_cache:
                    del self.metadata_cache[rel_path_str]
                if rel_path_str in self.loaded_modules:
                    del self.loaded_modules[rel_path_str]
                if rel_path_str in self._file_watchers:
                    del self._file_watchers[rel_path_str]
                    
            return True
        except Exception as e:
            logger.error(f"Error deleting file {rel_path_str}: {e}")
            return False

    def export_metadata(self, output_path: Optional[Union[str, pathlib.Path]] = None) -> str:
        """Export metadata cache to JSON"""
        export_data = {
            "root_dir": str(self.root_dir),
            "scan_time": time.time(),
            "files": {}
        }
        
        for rel_path_str, metadata in self.metadata_cache.items():
            # Convert metadata to serializable dict
            export_data["files"][rel_path_str] = {
                "path": str(metadata.path),
                "relative_path": str(metadata.relative_path),
                "file_size": metadata.file_size,
                "last_modified": metadata.last_modified,
                "content_hash": metadata.content_hash,
                "mime_type": metadata.mime_type,
                "content_type": metadata.content_type.name,
                "extension": metadata.extension,
                "is_loadable": metadata.is_loadable
            }
            
        # Convert to JSON
        json_data = json.dumps(export_data, indent=2)
        
        # Write to file if path provided
        if output_path:
            path = pathlib.Path(output_path) if isinstance(output_path, str) else output_path
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json_data)
                
        return json_data


def main():
    """Demonstrative main function to show FileSystem usage"""
    # Get the directory to scan
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        # Use the current script's directory as default
        root_dir = pathlib.Path(__file__).parent
    
    print(f"Initializing FileSystem with root directory: {root_dir}")
    fs = FileSystem(root_dir=root_dir)
    
    # Scan the directory and build metadata cache
    print("Scanning directory...")
    fs.scan_directory()
    
    print("\n===== File System Statistics =====")
    stats = fs.get_stats()
    print(f"Total files indexed: {stats['total_files']}")
    print(f"Total size: {stats['total_size_bytes'] / (1024*1024):.2f} MB")
    print("\nContent Types:")
    for content_type, count in stats['content_types'].items():
        print(f"  {content_type}: {count} files")
    
    print("\nTop 5 Extensions:")
    extensions = sorted(stats['extensions'].items(), key=lambda x: x[1], reverse=True)[:5]
    for ext, count in extensions:
        print(f"  {ext}: {count} files")
    
    # Show root directory listing
    print("\n===== Root Directory Contents =====")
    root_files = fs.get_file_listing()
    for file_info in root_files[:10]:  # Show first 10 files
        print(f"{file_info['name']} ({file_info['type']}, {file_info['size']} bytes)")
    
    if len(root_files) > 10:
        print(f"...and {len(root_files) - 10} more files")
    
    # Demo searching
    print("\n===== Search Demo =====")
    search_term = "test" if len(sys.argv) <= 2 else sys.argv[2]
    print(f"Searching for files containing '{search_term}'...")
    search_results = fs.search_files(search_term, content_search=True)
    
    print(f"Found {len(search_results)} matches:")
    for i, result in enumerate(search_results[:5]):
        match_types = ", ".join(result["match_types"])
        print(f"{i+1}. {result['path']} (matched in: {match_types})")
    
    if len(search_results) > 5:
        print(f"...and {len(search_results) - 5} more matches")
    
    # Demo loading file content
    if search_results:
        print("\n===== Content Loading Demo =====")
        sample_file = search_results[0]["path"]
        print(f"Loading content from: {sample_file}")
        
        content = fs.load_content(sample_file)
        if content:
            if isinstance(content, str):
                # Show first few lines of text content
                preview = "\n".join(content.split("\n")[:5])
                print(f"Content preview (first 5 lines):\n{preview}")
                if len(content.split("\n")) > 5:
                    print(f"...and {len(content.split('\n')) - 5} more lines")
            else:
                print(f"Binary content loaded: {len(content)} bytes")
    
    # Demo Python module loading for .py files
    print("\n===== Python Module Loading Demo =====")
    python_files = [rel_path for rel_path, metadata in fs.metadata_cache.items() 
                   if metadata.extension == '.py']
    
    if python_files:
        sample_py = python_files[0]
        print(f"Loading Python module: {sample_py}")
        module = fs.load_module(sample_py)
        
        if module:
            print(f"Module loaded successfully:")
            print(f"  Module name: {module.__name__}")
            print(f"  Module attributes: {', '.join(sorted([attr for attr in dir(module) 
                                                         if not attr.startswith('__')]))}")
        else:
            print("Failed to load module")
    else:
        print("No Python files found for module loading demo")
    
    # Demo dynamic module for non-Python files
    print("\n===== Dynamic Module Demo =====")
    non_py_files = [rel_path for rel_path, metadata in fs.metadata_cache.items() 
                   if metadata.extension != '.py' and metadata.content_type == ContentType.TEXT]
    
    if non_py_files:
        sample_file = non_py_files[0]
        print(f"Creating dynamic module for: {sample_file}")
        dynamic_module = fs.create_dynamic_module(sample_file)
        
        if dynamic_module:
            print(f"Dynamic module created successfully:")
            print(f"  Module name: {dynamic_module.__name__}")
            print(f"  Available functions: {', '.join([attr for attr in dir(dynamic_module) 
                                                    if callable(getattr(dynamic_module, attr)) 
                                                    and not attr.startswith('__')])}")
        else:
            print("Failed to create dynamic module")
    else:
        print("No suitable text files found for dynamic module demo")
    
    # Demo file similarity
    print("\n===== File Similarity Demo =====")
    if python_files and len(python_files) > 1:
        target_file = python_files[0]
        print(f"Finding files similar to: {target_file}")
        
        similar_files = fs.find_similar_files(target_file)
        if similar_files:
            print(f"Found {len(similar_files)} similar files:")
            for i, result in enumerate(similar_files[:5]):
                print(f"{i+1}. {result['path']} (similarity: {result['similarity_score']:.2f})")
        else:
            print("No similar files found")

    # Export metadata demonstration
    print("\n===== Metadata Export Demo =====")
    export_file = "filesystem_metadata.json"
    fs.export_metadata(export_file)
    print(f"Metadata exported to: {export_file}")
    
    print("\nFileSystem demonstration complete!")

# Folding function to strip class/method bodies while preserving structure
def fold_source(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines()
    output_lines = lines.copy()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.body[0].lineno - 1
            end = node.body[-1].end_lineno
            folded_lines = end - start
            # Replace lines with a placeholder for folding
            output_lines[start:end] = [
                f"    ...  # {folded_lines} lines folded"
            ]

    return '\n'.join(output_lines)

if __name__ == "__main__":
    main()
    script_path = pathlib.Path(sys.argv[0])
    raw_code = script_path.read_text()

    folded_code = fold_source(raw_code)

    print("Folded source code for context injection:")
    print(folded_code)
