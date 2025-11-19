import os
import uuid
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import weakref
import logging
import subprocess
from enum import Enum, auto

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msc-knowledge")

class MemoryState(Enum):
    """Represents possible states of quantum memory cells"""
    CLASSICAL = auto()  # Concrete, committed state
    QUANTUM = auto()    # Superposition state with multiple potentials
    CACHED = auto()     # Temporarily loaded but not committed
    SHARED = auto()     # Entangled with other memory spaces
    PAGED = auto()      # Written to disk due to low coherence
    DEALLOCATED = auto() # Released memory

@dataclass
class MemoryVector:
    """Vector representation of memory state characteristics"""
    size: int
    state: MemoryState = MemoryState.CLASSICAL
    coherence: float = 1.0  # 0.0-1.0 representing state certainty
    entanglement: float = 0.0  # Degree of entanglement with other memory

@dataclass
class QuantumCell:
    """Represents a single quantum memory cell"""
    address: int
    segment: int
    value: bytes
    state: MemoryState = MemoryState.CLASSICAL
    commit_hash: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class QuantumPage:
    """Represents a contiguous block of quantum memory"""
    vector: MemoryVector
    data: bytearray
    references: Dict[int, weakref.ReferenceType] = field(default_factory=dict)
    
    def __init__(self, size: int):
        self.vector = MemoryVector(size=size)
        self.data = bytearray(size)
        self.references = {}

@dataclass
class KnowledgeAtom:
    """Self-referential unit encapsulating knowledge fragments"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    connections: Dict[str, List[str]] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    atom_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    
    def fingerprint(self) -> str:
        """Generate a unique fingerprint based on content"""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def quine(self) -> str:
        """Return a self-referential representation"""
        return f"KnowledgeAtom(id={self.atom_id}, updated={self.last_updated.isoformat()})\nTags: {', '.join(self.tags)}\n\n{self.content[:200]}..."
    
    def update(self, new_content: str) -> None:
        """Update the atom's content"""
        self.content = new_content
        self.last_updated = datetime.now()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this knowledge atom"""
        self.tags.add(tag)
    
    def connect_to(self, other_id: str, relationship: str = "related") -> None:
        """Create a connection to another knowledge atom"""
        if relationship not in self.connections:
            self.connections[relationship] = []
        if other_id not in self.connections[relationship]:
            self.connections[relationship].append(other_id)
    
    def extract_frontmatter(self) -> Dict[str, Any]:
        """Extract frontmatter from content if present"""
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', self.content, re.DOTALL)
        if fm_match:
            try:
                import yaml
                frontmatter = yaml.safe_load(fm_match.group(1))
                # Update metadata with frontmatter
                self.metadata.update(frontmatter)
                # Extract tags if present
                if 'tags' in frontmatter:
                    for tag in frontmatter['tags']:
                        self.add_tag(tag)
                # Extract links if present
                if 'linklist' in frontmatter:
                    for link in frontmatter['linklist']:
                        if isinstance(link, str) and link.startswith("[[") and link.endswith("]]"):
                            link_id = link[2:-2]  # Remove [[ and ]]
                            self.connect_to(link_id)
                return frontmatter
            except Exception as e:
                logger.error(f"Error parsing frontmatter: {e}")
        return {}
    
    def extract_wikilinks(self) -> List[str]:
        """Extract wiki-style links from content"""
        links = re.findall(r'\[\[(.*?)\]\]', self.content)
        for link in links:
            self.connect_to(link)
        return links
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.atom_id,
            "content": self.content,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "connections": self.connections,
            "last_updated": self.last_updated.isoformat(),
            "fingerprint": self.fingerprint()
        }

class MorphologicalKnowledgeBase:
    """
    A knowledge base that organizes data using Morphological Source Code principles,
    where knowledge fragments evolve and self-organize through quantum-inspired state management.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or os.path.join(os.getcwd(), 'msc_knowledge'))
        self.repo_id = uuid.uuid4().hex
        self.atoms: Dict[str, KnowledgeAtom] = {}
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> set of atom_ids
        self.connection_index: Dict[str, Dict[str, Set[str]]] = {}  # atom_id -> {relationship -> set of atom_ids}
        self.embedding_cache: Dict[str, List[float]] = {}
        
        # Initialize repository structure
        self._init_repository()
    
    def _init_repository(self):
        """Initialize the knowledge repository structure"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Set up standard directories
        (self.base_path / "atoms").mkdir(exist_ok=True)
        (self.base_path / "indices").mkdir(exist_ok=True)
        (self.base_path / "embeddings").mkdir(exist_ok=True)
        (self.base_path / "metadata").mkdir(exist_ok=True)
        
        # Initialize Git for version control if not already a repository
        if not (self.base_path / ".git").exists():
            subprocess.run(['git', 'init', '--quiet'], cwd=str(self.base_path))
            subprocess.run(['git', 'config', 'user.name', 'MSC Knowledge Manager'], cwd=str(self.base_path))
            subprocess.run(['git', 'config', 'user.email', 'msc@knowledge.local'], cwd=str(self.base_path))
            
            # Create initial README
            readme = self.base_path / 'README.md'
            readme.write_text(
                f'# Morphological Source Code Knowledge Base\n'
                f'ID: {self.repo_id}\n'
                f'Initialized: {datetime.now().isoformat()}\n\n'
                f'This repository organizes knowledge using MSC principles,\n'
                f'treating knowledge fragments as quantum-inspired, evolving entities.'
            )
            subprocess.run(['git', 'add', 'README.md'], cwd=str(self.base_path))
            subprocess.run(['git', 'commit', '-m', 'Initialize MSC knowledge base', '--quiet'], cwd=str(self.base_path))
    
    def _run_git(self, args: list) -> Optional[str]:
        """Helper to run git commands"""
        try:
            result = subprocess.check_output(['git'] + args, cwd=str(self.base_path))
            return result.decode().strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command error: {e} with args: {args}")
            return None
    
    def create_atom(self, content: str, metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> KnowledgeAtom:
        """Create a new knowledge atom"""
        atom = KnowledgeAtom(
            content=content,
            metadata=metadata or {},
            tags=set(tags or [])
        )
        
        # Extract frontmatter and wikilinks
        atom.extract_frontmatter()
        atom.extract_wikilinks()
        
        # Add to in-memory indices
        self.atoms[atom.atom_id] = atom
        for tag in atom.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(atom.atom_id)
        
        # Save to disk
        self._save_atom(atom)
        
        return atom
    
    def _save_atom(self, atom: KnowledgeAtom) -> None:
        """Save an atom to the repository"""
        # Save atom content
        atom_path = self.base_path / "atoms" / f"{atom.atom_id}.md"
        atom_path.write_text(atom.content)
        
        # Save metadata
        metadata_path = self.base_path / "metadata" / f"{atom.atom_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(atom.to_dict(), f, indent=2)
        
        # Commit to repository
        self._run_git(['add', str(atom_path), str(metadata_path)])
        self._run_git(['commit', '-m', f'Update atom {atom.atom_id[:8]}', '--quiet'])
    
    def load_atom(self, atom_id: str) -> Optional[KnowledgeAtom]:
        """Load a knowledge atom"""
        if atom_id in self.atoms:
            return self.atoms[atom_id]
        
        metadata_path = self.base_path / "metadata" / f"{atom_id}.json"
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
                
            atom = KnowledgeAtom(
                content=data['content'],
                metadata=data['metadata'],
                tags=set(data['tags']),
                connections=data['connections'],
                last_updated=datetime.fromisoformat(data['last_updated']),
                atom_id=data['id']
            )
            
            self.atoms[atom_id] = atom
            return atom
        except Exception as e:
            logger.error(f"Error loading atom {atom_id}: {e}")
            return None
    
    def update_atom(self, atom_id: str, new_content: str) -> Optional[KnowledgeAtom]:
        """Update an existing atom's content"""
        atom = self.load_atom(atom_id)
        if not atom:
            return None
        
        # Store old connections and tags
        old_tags = set(atom.tags)
        
        # Update content
        atom.update(new_content)
        
        # Extract frontmatter and wikilinks again
        atom.extract_frontmatter()
        atom.extract_wikilinks()
        
        # Update tag indices
        for tag in atom.tags - old_tags:  # New tags
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(atom_id)
        
        for tag in old_tags - atom.tags:  # Removed tags
            if tag in self.tag_index:
                self.tag_index[tag].discard(atom_id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]
        
        # Save to disk
        self._save_atom(atom)
        
        return atom
    
    def find_by_tag(self, tag: str) -> List[str]:
        """Find atom IDs with a specific tag"""
        return list(self.tag_index.get(tag, set()))
    
    def find_connected(self, atom_id: str, relationship: Optional[str] = None) -> Dict[str, List[str]]:
        """Find atoms connected to the given atom"""
        atom = self.load_atom(atom_id)
        if not atom:
            return {}
        
        if relationship:
            return {relationship: atom.connections.get(relationship, [])}
        return atom.connections
    
    def get_atom_history(self, atom_id: str) -> List[Dict[str, Any]]:
        """Get the version history of an atom"""
        atom_path = self.base_path / "atoms" / f"{atom_id}.md"
        if not atom_path.exists():
            return []
        
        log_entries = self._run_git(['log', '--pretty=format:%H|%an|%at|%s', '--', str(atom_path)])
        if not log_entries:
            return []
        
        history = []
        for entry in log_entries.split('\n'):
            commit_hash, author, timestamp, message = entry.split('|')
            history.append({
                'commit_hash': commit_hash,
                'author': author,
                'timestamp': datetime.fromtimestamp(int(timestamp)),
                'message': message
            })
        
        return history
    
    def suggest_connections(self, atom_id: str) -> List[Tuple[str, float]]:
        """Suggest potential connections based on content similarity"""
        target_atom = self.load_atom(atom_id)
        if not target_atom:
            return []
        
        # Simple text-based similarity for now
        # In a more advanced implementation, use embeddings for similarity
        suggestions = []
        target_words = set(re.findall(r'\b\w+\b', target_atom.content.lower()))
        
        for other_id, other_atom in self.atoms.items():
            if other_id == atom_id:
                continue
                
            other_words = set(re.findall(r'\b\w+\b', other_atom.content.lower()))
            if not other_words:
                continue
                
            # Calculate Jaccard similarity
            similarity = len(target_words.intersection(other_words)) / len(target_words.union(other_words))
            if similarity > 0.1:  # Only suggest if some meaningful similarity
                suggestions.append((other_id, similarity))
        
        return sorted(suggestions, key=lambda x: x[1], reverse=True)
    
    def import_file(self, file_path: str) -> Optional[KnowledgeAtom]:
        """Import a file into the knowledge base"""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        try:
            content = path.read_text(encoding='utf-8')
            
            # Generate metadata from file
            metadata = {
                "source_file": str(path),
                "file_type": path.suffix,
                "import_date": datetime.now().isoformat()
            }
            
            # Create atom with file contents
            return self.create_atom(content, metadata=metadata)
        except Exception as e:
            logger.error(f"Error importing file {file_path}: {e}")
            return None
    
    def extract_clusters(self) -> Dict[str, List[str]]:
        """Identify clusters of related knowledge atoms"""
        # Build a graph of connections
        graph = {}
        for atom_id, atom in self.atoms.items():
            graph[atom_id] = set()
            for connections in atom.connections.values():
                for connected_id in connections:
                    graph[atom_id].add(connected_id)
        
        # Find connected components (simple cluster algorithm)
        clusters = {}
        visited = set()
        
        def dfs(node, cluster_id):
            visited.add(node)
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor in self.atoms and neighbor not in visited:
                    dfs(neighbor, cluster_id)
        
        cluster_id = 0
        for atom_id in self.atoms:
            if atom_id not in visited:
                dfs(atom_id, f"cluster_{cluster_id}")
                cluster_id += 1
        
        return clusters
    
    def extract_category_hierarchy(self) -> Dict[str, Set[str]]:
        """Extract hierarchical categories from tags and connections"""
        hierarchy = {}
        
        # Find parent-child relationships between tags
        for tag in self.tag_index:
            parts = tag.split('/')
            if len(parts) > 1:
                parent = '/'.join(parts[:-1])
                child = tag
                
                if parent not in hierarchy:
                    hierarchy[parent] = set()
                hierarchy[parent].add(child)
        
        # Add nodes with no children
        for tag in self.tag_index:
            if tag not in hierarchy:
                hierarchy[tag] = set()
        
        return hierarchy
        
    def generate_knowledge_map(self) -> Dict[str, Any]:
        """Generate a map of the knowledge base structure"""
        map_data = {
            "atoms": len(self.atoms),
            "tags": {tag: len(atoms) for tag, atoms in self.tag_index.items()},
            "clusters": self.extract_clusters(),
            "hierarchy": {parent: list(children) for parent, children in self.extract_category_hierarchy().items()}
        }
        
        # Save map to disk
        map_path = self.base_path / "knowledge_map.json"
        with open(map_path, 'w') as f:
            json.dump(map_data, f, indent=2)
        
        return map_data
    
    def bulk_import_directory(self, directory_path: str, file_extensions: Optional[List[str]] = None) -> List[str]:
        """Import multiple files from a directory"""
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            logger.error(f"Directory not found: {directory_path}")
            return []
        
        extensions = file_extensions or ['.md', '.txt', '.py', '.json']
        imported_ids = []
        
        for file_path in path.glob('**/*'):
            if file_path.is_file() and file_path.suffix in extensions:
                atom = self.import_file(str(file_path))
                if atom:
                    imported_ids.append(atom.atom_id)
                    logger.info(f"Imported {file_path}")
        
        # Generate knowledge map after import
        self.generate_knowledge_map()
        
        return imported_ids

# Initialize the knowledge base
kb = MorphologicalKnowledgeBase()

# Bulk import your existing files
imported_ids = kb.bulk_import_directory(".\\src\\", ['.md', '.txt', '.py'])
print(f"Imported {len(imported_ids)} knowledge atoms")

# Generate a map of the knowledge
knowledge_map = kb.generate_knowledge_map()
print(f"Discovered {len(knowledge_map['clusters'])} concept clusters")

# Find knowledge related to "quantum"
quantum_atoms = kb.find_by_tag("quantum")
print(f"Found {len(quantum_atoms)} atoms about quantum concepts")