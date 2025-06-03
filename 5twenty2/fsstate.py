from __future__ import annotations
import asyncio
import time
import array
import json
import math
import http.client
import os
import ast
import hashlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    TypeVar, Generic, Callable, Dict, Any, Optional, Set, Union,
    Awaitable, List, Tuple
)
class __Atom__(ABC):
    __slots__ = ("_refcount",)

    def __init__(self):
        self._refcount = 1

    def inc_ref(self) -> None:
        self._refcount += 1

    def dec_ref(self) -> None:
        self._refcount -= 1
        if self._refcount <= 0:
            self.cleanup()

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources when the atom is no longer referenced."""
        pass
T_co = TypeVar('T_co', covariant=True)
V_co = TypeVar('V_co', covariant=True)
C_co = TypeVar('C_co', bound=Callable, covariant=True)
class AsyncAtom(__Atom__, Generic[T_co, V_co, C_co], ABC):
    __slots__ = (
        '_code', '_value', '_local_env', '_ttl', '_created_at',
        '_last_access_time', 'request_data', 'session', 'runtime_namespace',
        'security_context', '_pending_tasks', '_lock', '_buffer_size', '_buffer'
    )
    _start_delimiter: str = "<<CONTENT>>"
    _end_delimiter: str = "<<END_CONTENT>>"

    def __init__(
        self,
        code: str, # This 'code' is now the raw content string
        value: Optional[V_co] = None,
        ttl: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        buffer_size: int = 1024 * 64,
        # Add KnowledgeEntry specific fields here or in the subclass
        atom_id: Optional[str] = None, # Allow setting ID, maybe hash-based later
        title: str = "Untitled",
        content_type: str = "text/markdown",
        last_updated: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        related_entries: Optional[List[str]] = None, # Links found in content
        keywords: Optional[List[str]] = None,
    ):
        # Initialize the base AsyncAtom (which calls the refcounted __Atom__ init)
        # The 'code' parameter in the base AsyncAtom will now store the *delimited* content
        delimited_code = self._start_delimiter + code + self._end_delimiter
        super().__init__(
            code=delimited_code, # Store the delimited content here
            value=value,
            ttl=ttl,
            request_data=request_data,
            buffer_size=buffer_size
        )

        # Initialize KnowledgeEntry specific fields
        self.id = atom_id if atom_id is not None else uuid.uuid4().hex # Use provided ID or generate UUID
        self.title = title
        self.content_type = content_type
        self.last_updated = last_updated if last_updated is not None else datetime.now()
        self.metadata = metadata or {}
        self.tags = tags or set()
        self.references = set() # What is the purpose of 'references' vs 'related_entries'? Clarify.
        self.embeddings = None # Placeholder

        # Store the *parsed* content separately for easier access
        self._parsed_content = self._parse_delimited_content(self._code)

        # Initialize related entries and keywords (will be populated by parsing)
        self.related_entries: List[str] = related_entries or []
        self.keywords: List[str] = keywords or []

        # Perform initial parsing to populate knowledge fields
        self._extract_knowledge_fields()


    async def __aenter__(self) -> AsyncAtom[T_co, V_co, C_co]:
        self.inc_ref()
        self._last_access_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.dec_ref()
        return False  # Propagate exceptions

    async def cleanup(self) -> None:
        print(f"Cleaning up atom {id(self)}")
        for task in list(self._pending_tasks): # Iterate over a copy as set is modified
            if not task.done():
                task.cancel()
                try:
                    await task # Await cancellation if needed, handle CancelledError
                except asyncio.CancelledError:
                    pass
        self._pending_tasks.clear() # Ensure set is empty
        self._buffer = bytearray(0)
        self._local_env.clear()

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._last_access_time = time.time()
        async with self._lock:
            # Create a controlled environment
            execution_namespace: Dict[str, Any] = {
                '__builtins__': __builtins__, # Or a restricted set
                'asyncio': asyncio,
                'time': time, # Example: expose some modules
                '__atom_self__': self, # Allow access to the atom instance itself
                # Add other necessary imports/objects here
            }
            # Copy local state into the execution namespace
            execution_namespace.update(self._local_env)

        try:
            # Wrap the user code in a standard async function definition
            # This assumes the user code is the *body* of the function
            # A more robust approach would be to require the user code *define* the function
            # For simplicity here, let's assume the code *is* the function body
            # This is still risky if the code isn't just a function body
            # A better way: require the code string *define* `async def atom_entrypoint(...)`
            wrapped_code = f"async def atom_entrypoint(__atom_self__, *args, **kwargs):\n{self._code}"

            code_obj = compile(wrapped_code, '<atom>', 'exec')

            # Execute the definition in the controlled namespace
            exec(code_obj, execution_namespace)

            # Get the defined function
            main_func = execution_namespace.get('atom_entrypoint')

            if not main_func or not asyncio.iscoroutinefunction(main_func):
                raise ValueError("Code must define an async function 'atom_entrypoint'")

            # Call the function, passing necessary context
            result = await main_func(__atom_self__=self, *args, **kwargs)

            async with self._lock:
                # Update shared local environment from the execution namespace
                # Be explicit about what state is shared/persisted
                # Maybe only update keys that were explicitly marked for persistence?
                # Or update all keys *except* builtins, args, kwargs, etc.
                # Let's update all keys except the ones we injected for execution context
                reserved_keys = {'__builtins__', 'asyncio', 'time', '__atom_self__', 'atom_entrypoint', 'args', 'kwargs'} # Add others as needed
                for k, v in execution_namespace.items():
                    if k not in reserved_keys:
                        self._local_env[k] = v # This now allows new variables to persist

            return result
        except Exception as e:
            print(f"Error executing AsyncAtom code: {e}") # Use a proper logger
            raise RuntimeError(f"Error executing AsyncAtom code: {e}") from e # Chain exception

    def _is_async_code(self, code: str) -> bool:
        try:
            parsed = ast.parse(code)
            for node in ast.walk(parsed):
                if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                    return True
            return False
        except SyntaxError:
            return False

    async def spawn_task(self, coro: Awaitable) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task

    async def handle_request(self, *args: Any, **kwargs: Any) -> Any:
        self._last_access_time = time.time()
        if not await self.is_authenticated():
            return {"status": "error", "message": "Authentication failed"}
        await self.log_request()
        request_context = {
            "session": self.session,
            "request_data": self.request_data,
            "runtime_namespace": self.runtime_namespace,
            "security_context": self.security_context,
            "timestamp": time.time()
        }
        try:
            if "operation" in self.request_data:
                operation = self.request_data["operation"]
                if operation == "execute_atom":
                    result = await self.execute_atom(request_context)
                elif operation == "query_memory":
                    result = await self.query_memory(request_context)
                else:
                    result = {"status": "error",
                              "message": "Unknown operation"}
            else:
                result = await self.process_request(request_context)
        except Exception as e:
            result = {"status": "error", "message": str(e)}
        await self.save_session()
        await self.log_response(result)
        return result

    @abstractmethod
    async def is_authenticated(self) -> bool:
        pass

    @abstractmethod
    async def log_request(self) -> None:
        pass

    @abstractmethod
    async def execute_atom(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def query_memory(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def process_request(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def save_session(self) -> None:
        pass

    @abstractmethod
    async def log_response(self, result: Any) -> None:
        pass

    async def preload_buffer(self, data: bytes) -> None:
        async with self._lock:
            if len(data) <= self._buffer_size:
                self._buffer[:len(data)] = data
            else:
                self._buffer = bytearray(data)
                self._buffer_size = len(data)

    async def get_buffer(self, offset: int = 0, length: Optional[int] = None) -> memoryview:
        async with self._lock:
            if length is None:
                return memoryview(self._buffer)[offset:]
            return memoryview(self._buffer)[offset:offset+length]

    def is_expired(self) -> bool:
        if self._ttl is None:
            return False
        now = time.time()
        return now - self._created_at > self._ttl

    @property
    def code(self) -> str:
        return self._code

    @property
    def value(self) -> Optional[V_co]:
        return self._value

    @property
    def ob_refcnt(self) -> int:
        return self._refcount

    @property
    def ob_ttl(self) -> Optional[int]:
        return self._ttl

    @ob_ttl.setter
    def ob_ttl(self, value: Optional[int]) -> None:
        self._ttl = value

    def _parse_delimited_content(self, raw_content: str) -> str:
        """Parse the raw content between the defined delimiters."""
        start_index = raw_content.find(self._start_delimiter)
        end_index = raw_content.rfind(self._end_delimiter)
        if start_index == -1 or end_index == -1 or start_index >= end_index:
             # Handle error: Maybe log a warning or raise a specific error
             # For now, let's return the raw content if delimiters aren't found,
             # or raise if strict framing is required. Let's raise for now.
            raise ValueError("Invalid content format: delimiters not found or mismatched.")
        return raw_content[start_index + len(self._start_delimiter):end_index]

    def _wrap_content_with_delimiters(self, content: str) -> str:
         """Wrap content with delimiters."""
         return self._start_delimiter + content + self._end_delimiter

    def update_content(self, new_parsed_content: str) -> None:
        """Update the atom's content and re-parse knowledge fields."""
        # Wrap the new content with delimiters
        new_delimited_content = self._wrap_content_with_delimiters(new_parsed_content)

        # Update the internal _code (which holds the delimited version)
        self._code = new_delimited_content
        self._parsed_content = new_parsed_content
        self.last_updated = datetime.now()

        # Re-extract knowledge fields from the new content
        self._extract_knowledge_fields()

        # Note: This update doesn't automatically save to the KnowledgeBase.
        # The KnowledgeBase would need a method like `kb.update_entry(atom_id, new_content)`
        # which calls this method and then saves to disk.

    def _extract_knowledge_fields(self) -> None:
        """Extract frontmatter, links, etc. from the parsed content."""
        content = self._parsed_content

        # Clear previous extractions before re-populating
        self.related_entries = []
        # self.keywords = [] # Decide if keywords are only from frontmatter or also extracted?
        # self.tags = set() # Decide if tags are only from frontmatter or also extracted?

        # Extract Frontmatter (using the logic from KnowledgeEntry)
        frontmatter = {}
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            try:
                # Simple parsing - consider using PyYAML for robustness
                for line in frontmatter_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        frontmatter[key] = value

                # Update fields from frontmatter
                if 'name' in frontmatter:
                    self.title = frontmatter['name']
                if 'tags' in frontmatter:
                    # Assuming tags are comma-separated string like "tag1, tag2"
                    self.tags = set(t.strip() for t in frontmatter['tags'].split(','))
                if 'keywords' in frontmatter:
                     # Assuming keywords are comma-separated string
                    self.keywords = [k.strip() for k in frontmatter['keywords'].split(',')]
                if 'link' in frontmatter:
                    self.related_entries.append(frontmatter['link'])
                if 'linklist' in frontmatter:
                    links_str = frontmatter['linklist']
                    # Assuming linklist is a string like "[[Link1]], [[Link2]]"
                    link_matches = re.findall(r'\[\[(.*?)\]\]', links_str)
                    self.related_entries.extend(link_matches)

            except Exception as e:
                print(f"Warning: Error parsing frontmatter for atom {self.id}: {e}") # Use proper logging

        # Extract Wiki-style Links [[Link]] from the *rest* of the content
        # Need to remove frontmatter before searching for links in the body
        content_after_frontmatter = content
        if frontmatter_match:
             content_after_frontmatter = content[frontmatter_match.end():]

        links_in_body = re.findall(r'\[\[(.*?)\]\]', content_after_frontmatter)
        self.related_entries.extend(links_in_body)
        self.related_entries = list(set(self.related_entries)) # Remove duplicates

        # Note: This method populates fields based on content.
        # If you want to *manually* set tags/keywords/related_entries,
        # you should do so *after* calling this or provide separate methods.

    # Override __call__ to execute the *parsed* content
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._last_access_time = time.time()
        async with self._lock:
            # Use a copy of the local environment for execution
            local_env = self._local_env.copy()

        try:
            # A safer approach would be to define a strict API the code must adhere to.

            # Wrap the parsed content in an async function definition
            # This assumes the parsed content is the *body* of the function.
            # If the parsed content *defines* the function, the wrapping is different.
            # Let's assume the parsed content *is* the function body for now.
            wrapped_code = f"async def atom_entrypoint(__atom_self__, *args, **kwargs):\n{self._parsed_content}"

            # Create a controlled execution namespace
            execution_namespace: Dict[str, Any] = {
                '__builtins__': __builtins__, # Or a restricted set like {'print': print, 'len': len, ...}
                'asyncio': asyncio,
                'time': time,
                're': re, # Expose modules the code might need
                'json': json,
                'math': math,
                '__atom_self__': self, # Allow access to the atom instance
                # Add other necessary imports/objects here
            }
            # Add the atom's persistent local state to the execution namespace
            execution_namespace.update(local_env)

            code_obj = compile(wrapped_code, f'<atom_{self.id}>', 'exec')

            # Execute the function definition in the controlled namespace
            exec(code_obj, execution_namespace)

            # Get the defined function
            main_func = execution_namespace.get('atom_entrypoint')

            if not main_func or not asyncio.iscoroutinefunction(main_func):
                 # If the code didn't define the expected async function,
                 # maybe try executing it directly if it's not async?
                 # Or enforce the async function signature. Let's enforce.
                 raise ValueError(f"Atom {self.id} code must define an async function 'atom_entrypoint'")

            # Call the function, passing necessary context
            # The executed code can access/modify variables in execution_namespace
            # and access the atom instance via __atom_self__
            result = await main_func(__atom_self__=self, *args, **kwargs)

            async with self._lock:
                # Update the atom's persistent local environment from the execution namespace
                # Only persist keys that are not part of the execution context setup
                reserved_keys = {'__builtins__', 'asyncio', 'time', 're', 'json', 'math', '__atom_self__', 'atom_entrypoint', 'args', 'kwargs'} # Add others
                for k, v in execution_namespace.items():
                     if k not in reserved_keys:
                         self._local_env[k] = v # Persist changes made by the executed code

            return result
        except Exception as e:
            # Log the error properly
            print(f"Error executing AsyncAtom {self.id} code: {e}") # Use a proper logger
            # Decide how execution errors affect the atom's state or return value
            # For now, re-raise
            raise RuntimeError(f"Error executing AsyncAtom {self.id} code: {e}") from e

    # Add to_dict for serialization (similar to KnowledgeEntry)
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            # Store the *delimited* content in the file
            "content": self._code,
            "content_type": self.content_type,
            "last_updated": self.last_updated.isoformat(),
            "related_entries": list(self.related_entries),
            "keywords": self.keywords,
            "metadata": self.metadata,
            "tags": list(self.tags),
            # Include persistent state
            "local_env": self._local_env,
            "ttl": self._ttl,
            "created_at": self._created_at, # Might need to store/load this
            # Note: buffer, lock, pending_tasks are runtime state, not persisted
        }

    async def is_authenticated(self) -> bool:
        # Implement auth logic based on self.request_data, self.session, self.security_context
        print(f"[{self.id}] Checking authentication...")
        return True # Demo implementation

    async def log_request(self) -> None:
        print(f"[{self.id}] Request logged at {datetime.now()} with data: {self.request_data}")

    async def execute_atom(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        # This method is called by handle_request if operation is "execute_atom"
        # It could potentially call self.__call__() or execute a specific part of the atom's code
        print(f"[{self.id}] Executing atom via handle_request...")
        try:
            # Pass request_context or parts of it to the atom's execution?
            # Let's pass it as kwargs to the atom_entrypoint
            result = await self(request_context=request_context)
            return {
                "status": "success",
                "message": "Atom code executed via handle_request",
                "result": result,
                "atom_state": self._local_env # Expose some state? Be careful.
            }
        except Exception as e:
             return {"status": "error", "message": f"Execution failed: {e}"}


    async def query_memory(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[{self.id}] Querying memory...")
        # Example: return buffer size and some local env keys
        return {
            "status": "success",
            "buffer_size": len(self._buffer),
            "local_env_keys": list(self._local_env.keys()),
            "context": request_context
        }

    async def process_request(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[{self.id}] Processing generic request...")
        # This is the default if no 'operation' is specified in request_data
        # Maybe the default processing is just calling the atom?
        try:
            result = await self(request_context=request_context)
            return {
                "status": "success",
                "message": "Atom processed generic request",
                "result": result,
                "atom_state": self._local_env
            }
        except Exception as e:
             return {"status": "error", "message": f"Processing failed: {e}"}


    async def save_session(self) -> None:
        print(f"[{self.id}] Saving session: {self.session}")
        # In a real system, this would persist self.session

    async def log_response(self, result: Any) -> None:
        print(f"[{self.id}] Response logged: {result}")

    # Add quine method from the second snippet
    def quine(self) -> str:
        """Return a self-referential representation of this AsyncAtom."""
        # Use _parsed_content for the source part of the quine
        return f"{self.__class__.__name__} (ID: {self.id}, last updated: {self.last_updated.isoformat()})\n{self._parsed_content}"

    # Add to_dict and from_dict methods for persistence (already added above)

    # Add properties for knowledge fields
    @property
    def parsed_content(self) -> str:
        return self._parsed_content

    # ob_refcnt property is already in the base AsyncAtom

class AsyncKnowledgeBase:
    """
    An asynchronous knowledge base system that organizes and manages AsyncAtom objects.
    Integrates persistence and indexing with async operations.
    """

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.join(os.getcwd(), 'async_knowledge_base'))
        self.base_path.mkdir(parents=True, exist_ok=True)
        # Store atoms in memory. Consider a cache or lazy loading for large bases.
        self.entries: Dict[str, AsyncAtom] = {}
        self.index: Dict[str, Any] = { # Refine index structure
            "title": {},      # Index by normalized title: { "normalized title": [id1, id2] }
            "keywords": defaultdict(list),   # Index by keywords: { "keyword": [id1, id2] }
            "tags": defaultdict(list),       # Index by tags: { "tag": [id1, id2] }
            "links": defaultdict(list)       # Index by links: { "link_text": [id1, id2] }
        }
        # Need a way to manage atom lifecycle and cleanup based on refcount/TTL
        self._active_atoms: Dict[str, AsyncAtom] = {} # Atoms currently in use (e.g., in a request)
        self._cleanup_task: Optional[asyncio.Task] = None # Task for periodic cleanup

        # Do not load entries here; caller must call async_init explicitly

    async def async_init(self):
        """Async initializer to load entries from disk."""
        await self._load_all_entries()

    async def _load_all_entries(self):
        """Asynchronously load all entries from disk into memory."""
        print(f"Loading knowledge base from {self.base_path}...")
        loop = asyncio.get_running_loop()
        # Use run_in_executor for blocking file system operations
        await loop.run_in_executor(None, self._blocking_load_all_entries)
        print("Knowledge base loaded.")

    def _blocking_load_all_entries(self):
         """Blocking function to load entries from disk."""
         for dir1 in self.base_path.iterdir():
             if dir1.is_dir():
                 for dir2 in dir1.iterdir():
                     if dir2.is_dir():
                         # Look for the current version file (e.g., *.json)
                         for entry_file in dir2.glob("*.json"):
                             if entry_file.name != "history": # Avoid history directory
                                 try:
                                     with open(entry_file, 'r') as f:
                                         data = json.load(f)
                                     # Use the from_dict class method
                                     atom = AsyncAtom.from_dict(data)
                                     self.entries[atom.id] = atom
                                     self._update_indices(atom) # Rebuild indices on load
                                 except Exception as e:
                                     print(f"Error loading file {entry_file}: {e}") # Use proper logging


    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for a content entry based on its hash."""
        # Use SHA256 for better collision resistance than MD5
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

    async def add_entry(self, content: str, title: str = None, content_type: str = "text/markdown") -> str:
        """Add a new knowledge entry to the base."""
        # Generate ID based on content hash (content-addressable)
        # Or use UUID? Let's stick to UUID from the atom for now, but hash is an option.
        # entry_id = self._generate_id(content) # If using hash-based ID

        # Create async knowledge atom
        # The constructor handles wrapping content and initial parsing
        atom = AsyncAtom(
            code=content, # Pass the raw content
            title=title or "Untitled",
            content_type=content_type
            # id=entry_id # If using hash-based ID
        )

        # If using hash-based ID, check for duplicates
        # if entry_id in self.entries:
        #     print(f"Warning: Entry with this content already exists (ID: {entry_id}). Not adding.")
        #     return entry_id # Return existing ID

        # Store entry in memory
        self.entries[atom.id] = atom

        # Update indices
        self._update_indices(atom)

        # Save to disk asynchronously
        await self._save_entry(atom)

        return atom.id

    async def update_entry(self, entry_id: str, new_content: str) -> Optional[str]:
        """Update an existing entry's content."""
        atom = self.get_entry(entry_id) # This might load from disk
        if not atom:
            print(f"Error: Entry {entry_id} not found for update.")
            return None

        try:
            # Update the atom's content and re-parse knowledge fields
            atom.update_content(new_content)

            # Re-index the updated atom (remove old index entries, add new ones)
            # This is complex - a simpler approach is to clear and re-add indices for this atom
            self._remove_from_indices(atom.id)
            self._update_indices(atom)

            # Save the updated entry to disk asynchronously
            await self._save_entry(atom)

            print(f"Entry {entry_id} updated successfully.")
            return entry_id

        except ValueError as e:
            print(f"Error updating entry {entry_id}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred updating entry {entry_id}: {e}")
            return None


    def _update_indices(self, entry: AsyncAtom) -> None:
        """Update all indices with the entry."""
        # Title index (using normalized title for lookup)
        normalized_title = entry.title.lower().strip()
        if normalized_title not in self.index["title"]:
             self.index["title"][normalized_title] = []
        if entry.id not in self.index["title"][normalized_title]:
             self.index["title"][normalized_title].append(entry.id)

        # Keywords index
        for keyword in entry.keywords:
            normalized_keyword = keyword.lower().strip()
            if entry.id not in self.index["keywords"][normalized_keyword]:
                self.index["keywords"][normalized_keyword].append(entry.id)

        # Tags index
        for tag in entry.tags:
            normalized_tag = tag.lower().strip()
            if entry.id not in self.index["tags"][normalized_tag]:
                self.index["tags"][normalized_tag].append(entry.id)

        # Links index (entries *linking to* this entry are found by searching other entries' related_entries)
        # This index should probably map link_text -> list of entry_ids *containing* that link text
        # The current implementation in the second snippet's KB does this. Let's keep it.
        for link_text in entry.related_entries:
             normalized_link_text = link_text.lower().strip()
             if entry.id not in self.index["links"][normalized_link_text]:
                 self.index["links"][normalized_link_text].append(entry.id)

    def _remove_from_indices(self, entry_id: str) -> None:
        """Remove an entry's ID from all indices."""
        # This is needed before re-indexing after an update
        entry = self.entries.get(entry_id)
        if not entry:
            return # Nothing to remove if entry isn't in memory

        # Remove from title index
        normalized_title = entry.title.lower().strip()
        if normalized_title in self.index["title"] and entry_id in self.index["title"][normalized_title]:
            self.index["title"][normalized_title].remove(entry_id)
            if not self.index["title"][normalized_title]:
                del self.index["title"][normalized_title] # Clean up empty lists

        # Remove from keywords index
        for keyword in entry.keywords:
            normalized_keyword = keyword.lower().strip()
            if normalized_keyword in self.index["keywords"] and entry_id in self.index["keywords"][normalized_keyword]:
                self.index["keywords"][normalized_keyword].remove(entry_id)
                if not self.index["keywords"][normalized_keyword]:
                    del self.index["keywords"][normalized_keyword]

        # Remove from tags index
        for tag in entry.tags:
            normalized_tag = tag.lower().strip()
            if normalized_tag in self.index["tags"] and entry_id in self.index["tags"][normalized_tag]:
                self.index["tags"][normalized_tag].remove(entry_id)
                if not self.index["tags"][normalized_tag]:
                    del self.index["tags"][normalized_tag]

        # Remove from links index
        for link_text in entry.related_entries:
            normalized_link_text = link_text.lower().strip()
            if normalized_link_text in self.index["links"] and entry_id in self.index["links"][normalized_link_text]:
                self.index["links"][normalized_link_text].remove(entry_id)
                if not self.index["links"][normalized_link_text]:
                    del self.index["links"][normalized_link_text]


    async def _save_entry(self, entry: AsyncAtom) -> None:
        """Save an entry to disk with versioning asynchronously."""
        loop = asyncio.get_running_loop()
        # Use run_in_executor for blocking file system operations
        await loop.run_in_executor(None, self._blocking_save_entry, entry)

    def _blocking_save_entry(self, entry: AsyncAtom) -> None:
        """Blocking function to save an entry to disk."""
        entry_dir = self.base_path / entry.id[:2] / entry.id[2:4]
        entry_dir.mkdir(parents=True, exist_ok=True)

        data_to_save = entry.to_dict()

        # Save current version
        entry_file = entry_dir / f"{entry.id}.json"
        with open(entry_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)

        # Save version history (append timestamp)
        history_dir = entry_dir / "history"
        history_dir.mkdir(exist_ok=True)
        # Use a file-system safe timestamp format
        timestamp_str = entry.last_updated.isoformat().replace(':', '-').replace('.', '-')
        history_file = history_dir / f"{entry.id}_{timestamp_str}.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)


    def get_entry(self, entry_id: str) -> Optional[AsyncAtom]:
        """
        Retrieve an entry by ID. Loads from disk if not in memory.
        Note: This is still synchronous for now, but could be made async.
        """
        if entry_id in self.entries:
            return self.entries[entry_id]

        # Try to load from disk if not in memory (Blocking operation!)
        entry_dir = self.base_path / entry_id[:2] / entry_id[2:4]
        entry_file = entry_dir / f"{entry_id}.json"

        if entry_file.exists():
            try:
                with open(entry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Use the from_dict class method
                atom = AsyncAtom.from_dict(data)

                self.entries[entry_id] = atom # Add to memory cache
                self._update_indices(atom) # Ensure it's indexed after loading
                return atom
            except Exception as e:
                print(f"Error loading entry {entry_id} from disk: {e}") # Use proper logging
                return None

        return None

    # Consider making get_entry async if disk access is frequent in async contexts
    async def get_entry_async(self, entry_id: str) -> Optional[AsyncAtom]:
         """Asynchronously retrieve an entry by ID."""
         if entry_id in self.entries:
             return self.entries[entry_id]

         loop = asyncio.get_running_loop()
         # Run the blocking get_entry in a thread pool
         atom = await loop.run_in_executor(None, self.get_entry, entry_id)
         return atom


    def search(self, query: str) -> List[AsyncAtom]:
        """
        Search for entries matching a query using indices and simple text search.
        Note: This is synchronous. For large bases, consider async search or indexing.
        """
        query_lower = query.lower().strip()
        matching_ids = set()

        # Search by title (exact match on normalized title)
        if query_lower in self.index["title"]:
            matching_ids.update(self.index["title"][query_lower])

        # Search by keywords (substring match)
        for keyword, ids in self.index["keywords"].items():
            if query_lower in keyword:
                matching_ids.update(ids)

        # Search by tags (substring match)
        for tag, ids in self.index["tags"].items():
            if query_lower in tag:
                matching_ids.update(ids)

        # Search by links (substring match on link text)
        for link_text, ids in self.index["links"].items():
             if query_lower in link_text:
                 matching_ids.update(ids)

        # Fallback/supplementary: Simple text search in content for non-indexed matches
        # This can be slow for large bases
        for entry_id, entry in self.entries.items():
             if entry_id not in matching_ids: # Avoid re-checking already found entries
                 if query_lower in entry.title.lower() or query_lower in entry.parsed_content.lower():
                     matching_ids.add(entry_id)


        # Retrieve matching entries (use async getter if needed)
        # For now, using the sync getter as search itself is sync
        return [self.get_entry(entry_id) for entry_id in matching_ids if self.get_entry(entry_id)]


    async def search_async(self, query: str) -> List[AsyncAtom]:
        matching_ids = await asyncio.get_running_loop().run_in_executor(None, self.search, query)
        # Need to fetch atoms asynchronously based on IDs
        atoms = [await self.get_entry_async(id) for id in matching_ids]
        return [atom for atom in atoms if atom]


    def get_related(self, entry_id: str) -> List[AsyncAtom]:
        """
        Get entries related to a given entry (entries that link to it).
        Note: This is synchronous.
        """
        entry = self.get_entry(entry_id)
        if not entry:
            return []

        related_ids = set()
        # Find entries that contain links matching this entry's title or ID?
        # The original logic used the 'links' index, which maps link_text -> entry_ids containing that text.
        # So, to find entries *linking to* entry X, we need to find entries whose related_entries list
        # contains X's title or ID. The current 'links' index doesn't directly support this efficiently.
        # It supports finding entries *containing* a specific link text.

        # Let's reinterpret "related" as entries whose `related_entries` list contains *this* entry's ID or title.
        # This requires iterating through all entries or building a reverse index.
        # Building a reverse index (entry_id -> list of entry_ids that link to it) would be more efficient.

        # For now, let's use the existing 'links' index to find entries that contain a link *matching this entry's title*.
        # This is what the original code did.
        normalized_title = entry.title.lower().strip()
        if normalized_title in self.index["links"]:
             related_ids.update(self.index["links"][normalized_title])

        # Also check if other entries link using the ID
        normalized_id = entry_id.lower().strip()
        if normalized_id in self.index["links"]:
             related_ids.update(self.index["links"][normalized_id])


        # Remove self-reference
        if entry_id in related_ids:
            related_ids.remove(entry_id)

        # Load entries (using sync getter)
        return [self.get_entry(rid) for rid in related_ids if self.get_entry(rid)]

    # Consider an async get_related method


    def build_graph(self) -> Dict[str, Any]:
        """
        Build a knowledge graph representation.
        Note: This is synchronous.
        """
        nodes = []
        edges = []

        # Create nodes for each entry
        for entry_id, entry in self.entries.items():
            nodes.append({
                "id": entry_id,
                "label": entry.title,
                "type": "atom", # Use "atom" or "knowledge_entry"
                "tags": list(entry.tags),
                "content_type": entry.content_type,
                # Add other relevant metadata
            })

            # Create edges for related entries (links *from* this entry)
            for related_text in entry.related_entries:
                # Find entries whose ID or title matches the related_text
                target_ids = set()
                normalized_related_text = related_text.lower().strip()

                # Check title index
                if normalized_related_text in self.index["title"]:
                    target_ids.update(self.index["title"][normalized_related_text])

                # Check if the link text is itself an ID
                if normalized_related_text in self.entries:
                     target_ids.add(normalized_related_text)


                for target_id in target_ids:
                    if target_id != entry_id:  # Avoid self-loops
                        edges.append({
                            "source": entry_id,
                            "target": target_id,
                            "label": "links_to", # More descriptive label
                            "link_text": related_text # Store the original link text
                        })

        return {
            "nodes": nodes,
            "edges": edges
        }

    # Consider an async build_graph method


    async def import_markdown_file(self, file_path: str) -> str:
        """Import a markdown file into the knowledge base asynchronously."""
        path = Path(file_path)
        if not await asyncio.get_running_loop().run_in_executor(None, path.exists):
            raise ValueError(f"File {file_path} does not exist")

        # Read file content asynchronously (requires aiofiles or run in executor)
        # Using run_in_executor for simplicity with stdlib Path
        content = await asyncio.get_running_loop().run_in_executor(None, path.read_text, 'utf-8')
        title = path.stem  # Use filename as default title

        return await self.add_entry(content, title=title, content_type="text/markdown")

    async def bulk_import(self, directory: str, pattern: str = "*.md") -> List[str]:
        """Import all files matching pattern from a directory asynchronously."""
        dir_path = Path(directory)
        loop = asyncio.get_running_loop()

        if not await loop.run_in_executor(None, dir_path.exists) or not await loop.run_in_executor(None, dir_path.is_dir):
            raise ValueError(f"Directory {directory} does not exist or is not a directory")

        imported_ids = []
        # glob is blocking, run in executor
        file_paths = await loop.run_in_executor(None, list, dir_path.glob(pattern))

        # Import files concurrently
        import_tasks = [self.import_markdown_file(str(file_path)) for file_path in file_paths]
        results = await asyncio.gather(*import_tasks, return_exceptions=True)

        for file_path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                print(f"Error importing {file_path}: {result}") # Use proper logging
            else:
                imported_ids.append(result)
                print(f"Imported {file_path} as {result}")

        return imported_ids

    # --- Atom Lifecycle Management and Metaprogramming Hook ---

    # This is where the manual refcounting becomes relevant.
    # How does the KB know when an atom is "in use" by an external process/request?
    # The __aenter__/__aexit__ on the atom itself handles usage within a specific 'async with' block.
    # But if the KB hands out an atom reference, the KB needs to know it's being used.

    # Option: The KB provides a method to get an atom for use, which increments refcount.
    # The caller must then explicitly release it, or use a context manager provided by the KB.

    async def get_atom_for_use(self, entry_id: str) -> Optional[AsyncAtom]:
        """Retrieve an atom and increment its reference count for active use."""
        atom = await self.get_entry_async(entry_id) # Use async getter
        if atom:
            atom.inc_ref()
            self._active_atoms[atom.id] = atom # Keep track of actively used atoms
            print(f"[{atom.id}] Refcount incremented. New count: {atom.ob_refcnt}")
        return atom

    async def release_atom(self, entry_id: str) -> None:
        """Decrement an atom's reference count."""
        atom = self.entries.get(entry_id) # Get from memory (should be there if active)
        if atom:
            atom.dec_ref()
            print(f"[{atom.id}] Refcount decremented. New count: {atom.ob_refcnt}")
            if atom.ob_refcnt <= 0:
                print(f"[{atom.id}] Refcount zero, initiating cleanup.")
                await atom.cleanup()
                # Decide if atom should be removed from self.entries when refcount hits zero
                # Usually, GC handles this. Manual refcount means *you* decide.
                # If it's removed, subsequent get_entry will load from disk.
                # del self.entries[atom.id] # Optional: remove from memory cache
                if atom.id in self._active_atoms:
                     del self._active_atoms[atom.id] # Remove from active tracking

    # Context manager for easier atom usage
    # async def use_atom(self, entry_id: str):
    #     atom = await self.get_atom_for_use(entry_id)
    #     if not atom:
    #         raise ValueError(f"Atom {entry_id} not found")
    #     try:
    #         yield atom
    #     finally:
    #         await self.release_atom(entry_id)


    # Metaprogramming Hook Idea:
    # The executed code within an atom could call a special function provided
    # in the execution namespace, which interacts with the atom's refcount or state.
    # Example:
    # In AsyncAtom.__call__, add to execution_namespace:
    # 'pause_self': lambda duration: asyncio.get_running_loop().create_task(asyncio.sleep(duration)) # Simple pause
    # Or something more complex:
    # 'wait_for_refcount': lambda target_count: __atom_self__._wait_for_refcount(target_count)

    # async def _wait_for_refcount(self, target_count: int):
    #     """Waits until the atom's refcount reaches or drops below target_count."""
    #     while self.ob_refcnt > target_count:
    #         print(f"[{self.id}] Waiting for refcount to drop below {target_count}. Current: {self.ob_refcnt}")
    #         await asyncio.sleep(0.1) # Wait a bit before checking again
    #     print(f"[{self.id}] Refcount condition met ({self.ob_refcnt}). Continuing.")

    # Then, in the atom's code string:
    # async def atom_entrypoint(__atom_self__, *args, **kwargs):
    #     print("Starting operation...")
    #     # Do some work...
    #     await __atom_self__._wait_for_refcount(1) # Wait until only the KB holds a reference
    #     print("Refcount dropped, continuing after pause...")
    #     # Do more work...
    #     return "Operation complete"

    # This allows the *executed code* to control its flow based on the atom's external usage count.
    # This is a plausible interpretation of your metaprogramming idea using refcount.

    # Need a cleanup task to periodically check for expired atoms with zero refcount
    async def _run_cleanup_loop(self, interval: int = 60):
        """Periodically checks for expired atoms with zero refcount and cleans them up."""
        print("Starting KB cleanup loop...")
        while True:
            await asyncio.sleep(interval)
            print("Running KB cleanup check...")
            atoms_to_clean = []
            # Iterate over a copy of entries as we might remove from self.entries
            for atom_id, atom in list(self.entries.items()):
                # Check if expired AND no external references (refcount is 1 because KB holds one)
                # If KB holds a reference in self.entries, refcount will be >= 1.
                # If it's only held by the KB and is expired, refcount would be 1.
                # If it's held by KB *and* actively used elsewhere, refcount > 1.
                # We want to clean up if expired AND only held by the KB (refcount == 1)
                # OR if refcount is 0 (meaning KB didn't hold a reference, which shouldn't happen if in self.entries)
                # Let's clean up if expired AND refcount <= 1 (assuming KB holds one reference in self.entries)
                # If you remove from self.entries on release_atom when refcount hits 0,
                # then the check should be just `atom.is_expired() and atom.ob_refcnt <= 0`
                # Let's stick to the simpler model where KB keeps a cache reference until cleanup.
                # Clean up if expired AND only the KB's cache reference remains (refcount == 1)
                # Or if somehow refcount dropped below 1 (error state)
                if atom.is_expired() and atom.ob_refcnt <= 1:
                     atoms_to_clean.append(atom_id)
                     print(f"[{atom_id}] Marked for cleanup (expired and refcount <= 1).")

            for atom_id in atoms_to_clean:
                atom = self.entries.get(atom_id)
                if atom:
                    try:
                        # Ensure refcount is still <= 1 before cleaning
                        if atom.ob_refcnt <= 1:
                            print(f"[{atom_id}] Cleaning up...")
                            await atom.cleanup()
                            del self.entries[atom_id] # Remove from KB's memory cache
                            self._remove_from_indices(atom_id) # Remove from indices
                            if atom_id in self._active_atoms:
                                del self._active_atoms[atom_id] # Should not be in active if refcount <= 1, but safety check
                            print(f"[{atom_id}] Cleanup complete.")
                        else:
                             print(f"[{atom_id}] Refcount increased before cleanup, skipping for now. Current: {atom.ob_refcnt}")
                    except Exception as e:
                        print(f"Error during cleanup of atom {atom_id}: {e}") # Log cleanup errors

    def start_cleanup_loop(self, interval: int = 60):
        """Starts the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._run_cleanup_loop(interval))
            print("KB cleanup loop started.")

    async def stop_cleanup_loop(self):
        """Stops the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            print("Stopping KB cleanup loop...")
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                print("KB cleanup loop stopped.")



async def main():
    """Demo of the asynchronous knowledge base system."""
    # Initialize KB (this will load existing data)
    kb = AsyncKnowledgeBase()  # instantiate the knowledge base
    await kb.async_init()  # explicitly load entries asynchronously

    # Start the background cleanup task
    kb.start_cleanup_loop(interval=10)  # Check every 10 seconds for demo

    # Add some sample entries asynchronously
    # Content can now include executable Python code within the delimiters
    quantum_code = """---
name: "Quantum Computing Basics"
tags: ["quantum", "computing", "theory"]
---
<<CONTENT>>
async def atom_entrypoint(__atom_self__, *args, **kwargs):
    print(f"Executing Quantum Computing atom! Args: {args}, Kwargs: {kwargs}")
    # Access atom state
    print(f"Current state: {__atom_self__._local_env}")
    __atom_self__._local_env['executed_count'] = __atom_self__._local_env.get('executed_count', 0) + 1

    # Access request data if available via handle_request
    request_context = kwargs.get('request_context', {})
    if request_context:
        print(f"Request context session: {request_context.get('session')}")

    # Example of metaprogramming hook: wait until refcount is low
    # await __atom_self__._wait_for_refcount(1) # Uncomment if _wait_for_refcount is added

    return f"Hello from Quantum Atom! Executed {__atom_self__._local_env['executed_count']} times."
<<END_CONTENT>>
"""

    hilbert_code = """---
name: "Hilbert Space"
tags: ["mathematics", "quantum"]
---
<<CONTENT>>
async def atom_entrypoint(__atom_self__, *args, **kwargs):
    print("Executing Hilbert Space atom!")
    # Link to Quantum Computing Basics (using its title or ID)
    # How to find the linked atom? Need KB access.
    # Maybe the KB or a context object is passed to the executed code?
    # Let's assume KB is available via __atom_self__._kb (need to add this link)
    # Or pass KB as a kwarg? Let's pass KB as a kwarg for now.
    kb = kwargs.get('kb_instance')
    if kb:
        print("KB instance available in atom execution.")
        # Find the Quantum Computing atom by title
        quantum_atoms = kb.search("Quantum Computing Basics")
        if quantum_atoms:
            quantum_atom = quantum_atoms[0]
            print(f"Found related atom: {quantum_atom.title} ({quantum_atom.id})")
            # Example: Call the related atom (this increments its refcount temporarily)
            # async with kb.use_atom(quantum_atom.id) as q_atom: # If using KB context manager
            #    related_result = await q_atom()
            #    print(f"Result from related atom: {related_result}")
            # Or just call it directly if its __call__ handles refcounting internally (less explicit)
            related_result = await quantum_atom() # This uses the atom's own __aenter__/__aexit__
            print(f"Result from related atom: {related_result}")
        else:
            print("Could not find related Quantum Computing atom.")

    return "Hello from Hilbert Space Atom!"
<<END_CONTENT>>
"""
    # Add atoms to KB
    quantum_id = await kb.add_entry(quantum_code)
    hilbert_id = await kb.add_entry(hilbert_code)

    # Retrieve and display entries (using async getter)
    quantum_atom = await kb.get_entry_async(quantum_id)
    if quantum_atom:
        print(f"\nEntry: {quantum_atom.title}")
        print(f"ID: {quantum_atom.id}")
        print(f"Tags: {quantum_atom.tags}")
        print(f"Links extracted: {quantum_atom.related_entries}")
        print(f"Initial local_env: {quantum_atom._local_env}")

    hilbert_atom = await kb.get_entry_async(hilbert_id)
    if hilbert_atom:
        print(f"\nEntry: {hilbert_atom.title}")
        print(f"ID: {hilbert_atom.id}")
        print(f"Links extracted: {hilbert_atom.related_entries}")


    # --- Demonstrate Execution and State ---

    print("\n--- Executing Atoms ---")

    # Execute the quantum atom directly via its __call__ method
    # This uses the atom's internal __aenter__/__aexit__ for refcounting within the call scope
    print(f"\nCalling Quantum Atom ({quantum_id})...")
    result1 = await quantum_atom()
    print(f"Call result 1: {result1}")
    print(f"Quantum Atom local_env after call 1: {quantum_atom._local_env}")

    print(f"\nCalling Quantum Atom ({quantum_id}) again...")
    result2 = await quantum_atom()
    print(f"Call result 2: {result2}")
    print(f"Quantum Atom local_env after call 2: {quantum_atom._local_env}")

    # Execute the hilbert atom, which calls the quantum atom
    print(f"\nCalling Hilbert Atom ({hilbert_id})...")
    # Pass KB instance so Hilbert atom can find/call Quantum atom
    result3 = await hilbert_atom(kb_instance=kb)
    print(f"Call result 3: {result3}")
    print(f"Quantum Atom local_env after Hilbert call: {quantum_atom._local_env}") # Check if state persisted

    # --- Demonstrate Request Handling ---
    print("\n--- Handling Request ---")
    # Simulate a request for the quantum atom
    request_data = {
        "operation": "execute_atom",
        "session": {"user": "test_user", "session_id": "abc123"}
    }
    # Need to get the atom for handling the request.
    # Use the KB's get_atom_for_use/release_atom or the atom's context manager.
    # Let's use the atom's context manager for simplicity here, assuming handle_request is called within it.
    async with quantum_atom: # This increments refcount via __aenter__
        print(f"\nHandling request for Quantum Atom ({quantum_id})...")
        # Manually set request_data and session for this specific request simulation
        quantum_atom.request_data = request_data
        quantum_atom.session = request_data.get("session", {})
        request_result = await quantum_atom.handle_request()
        print(f"Request handling result: {request_result}")
    # __aexit__ is called here, decrementing refcount

    # --- Demonstrate Search and Related ---
    print("\n--- Searching and Related ---")
    search_results = kb.search("quantum")
    print(f"\nSearch results for 'quantum':")
    for entry in search_results:
        print(f"- {entry.title} ({entry.id})")

    if quantum_atom:
        related_entries = kb.get_related(quantum_atom.id)
        print(f"\nEntries linking to '{quantum_atom.title}':")
        for entry in related_entries:
             print(f"- {entry.title} ({entry.id})") # Hilbert should appear here

    # --- Demonstrate Graph Building ---
    print("\n--- Building Graph ---")
    graph = kb.build_graph()
    print(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    # print(json.dumps(graph, indent=2)) # Uncomment to see full graph structure

    # --- Demonstrate Update ---
    print("\n--- Updating Atom ---")
    new_quantum_content = """---
name: "Quantum Computing Basics - Updated"
tags: ["quantum", "computing", "theory", "update"]
---
<<CONTENT>>
async def atom_entrypoint(__atom_self__, *args, **kwargs):
    print(f"Executing UPDATED Quantum Computing atom! Args: {args}, Kwargs: {kwargs}")
    __atom_self__._local_env['executed_count'] = __atom_self__._local_env.get('executed_count', 0) + 1
    __atom_self__._local_env['status'] = 'updated and executed'
    return f"Hello from UPDATED Quantum Atom! Executed {__atom_self__._local_env['executed_count']} times."
<<END_CONTENT>>
"""
    updated_id = await kb.update_entry(quantum_id, new_quantum_content)
    if updated_id:
        print(f"Atom {quantum_id} updated.")
        updated_atom = await kb.get_entry_async(updated_id)
        if updated_atom:
            print(f"Updated title: {updated_atom.title}")
            print(f"Updated tags: {updated_atom.tags}")
            print(f"Updated local_env (should retain count): {updated_atom._local_env}") # State should persist across update

            # Execute the updated atom
            print(f"\nCalling UPDATED Quantum Atom ({updated_id})...")
            updated_result = await updated_atom()
            print(f"Call result: {updated_result}")
            print(f"Updated Quantum Atom local_env after call: {updated_atom._local_env}")


    # --- Cleanup ---
    # The cleanup loop runs in the background.
    # Atoms with TTL will eventually be cleaned up if their refcount drops to 1 (only KB holds a reference).
    # You can set a TTL when creating the atom:
    # expired_atom_id = await kb.add_entry("<<CONTENT>>async def atom_entrypoint(__atom_self__):\n return 'I will expire'<<END_CONTENT>>", ttl=5)
    # expired_atom = kb.get_entry(expired_atom_id)
    # print(f"\nAdded atom {expired_atom_id} with TTL 5s.")
    # await asyncio.sleep(6) # Wait for it to expire and cleanup loop to run
    # print(f"Checking if expired atom {expired_atom_id} is still in KB: {kb.get_entry(expired_atom_id) is not None}")


    # Stop the cleanup loop before exiting
    await kb.stop_cleanup_loop()

    # In a real application, you might want to explicitly save the state of all atoms
    # before shutting down, especially if you remove them from the KB's memory cache
    # when refcount hits zero.


if __name__ == "__main__":
    asyncio.run(main())
