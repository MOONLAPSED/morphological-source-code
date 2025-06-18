from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import re
import shutil
import subprocess
import platform
import json
from contextlib import contextmanager
import os


class GitCommands:
    """Platform-specific Git command executor with Windows path handling."""
    
    @staticmethod
    def get_platform_cmd():
        if platform.system() == "Windows":
            return ["powershell.exe", "-Command"]
        return ["/bin/bash", "-c"]

    @staticmethod
    def run_git(cmd: str, path: Path) -> subprocess.CompletedProcess:
        # Ensure path is absolute and exists
        abs_path = path.resolve()
        if not abs_path.exists():
            raise ValueError(f"Path does not exist: {abs_path}")
            
        # Convert to string and ensure forward slashes for Git
        path_str = str(abs_path).replace('\\', '/')
        print(f"Executing git command: {cmd} in directory: {path_str}")  # Debug log
        
        platform_cmd = GitCommands.get_platform_cmd()
        return subprocess.run(
            [*platform_cmd, cmd],
            cwd=path_str,
            capture_output=True,
            text=True
        )

    @staticmethod
    def init(path: Path) -> None:
        print(f"Initializing git repo in: {path}")  # Debug log
        GitCommands.run_git("git init", path)

    @staticmethod
    def add(path: Path, pattern: str) -> None:
        print(f"Adding files matching {pattern} in: {path}")  # Debug log
        GitCommands.run_git(f"git add {pattern}", path)

    @staticmethod
    def commit(path: Path, message: str) -> None:
        print(f"Committing changes in: {path}")  # Debug log
        GitCommands.run_git(f'git commit -m "{message}"', path)
class FrontmatterParser:
    """Pure Python frontmatter parser using standard library."""
    
    @staticmethod
    def parse(content: str) -> tuple[dict, str]:
        """Parse frontmatter and content from markdown string."""
        if not content.startswith('---'):
            return {}, content
            
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content
            
        try:
            metadata = {}
            for line in parts[1].strip().splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            return metadata, parts[2].strip()
        except Exception:
            return {}, content

@dataclass
class KnowledgeNode:
    """Represents a single node of knowledge, mapping to an Obsidian markdown file."""
    title: str
    content: str
    path: Path
    py_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_md_file(cls, md_path: Path) -> 'KnowledgeNode':
        """Create a KnowledgeNode from an existing markdown file."""
        content = md_path.read_text(encoding='utf-8')
        metadata, content = FrontmatterParser.parse(content)
        py_path = md_path.with_suffix('.py')
        
        # Extract wiki-style links
        links = re.findall(r'\[\[(.*?)\]\]', content)
        
        # Extract tags
        tags = [tag.strip('#') for tag in re.findall(r'#(\w+)', content)]
        
        return cls(
            title=md_path.stem,
            content=content,
            path=md_path,
            py_path=py_path,
            metadata=metadata,
            links=links,
            tags=tags,
            last_modified=datetime.fromtimestamp(md_path.stat().st_mtime)
        )
    
    def to_python_file(self) -> None:
        """Convert the markdown content to a Python representation."""
        python_content = f'''"""
{self.content}
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any

@dataclass
class {self.title.replace(" ", "_")}Node:
    """Auto-generated from Obsidian note: {self.title}"""
    content: str = """{self.content}"""
    metadata: Dict[str, Any] = {self.metadata}
    links: List[str] = {self.links}
    tags: List[str] = {self.tags}
    last_modified: datetime = datetime.fromisoformat("{self.last_modified.isoformat()}")
    
    def get_backlinks(self, kb) -> List["KnowledgeNode"]:
        """Get all nodes that link to this one."""
        return [node for node in kb.nodes.values() if self.title in node.links]

    def regenerate_source(self) -> str:
        """Regenerate the source markdown for this node."""
        if self.metadata:
            metadata_str = "---\\n"
            for key, value in self.metadata.items():
                metadata_str += f"{key}: {value}\\n"
            metadata_str += "---\\n\\n"
        else:
            metadata_str = ""
            
        return f"{metadata_str}{self.content}"
'''
        self.py_path.write_text(python_content, encoding='utf-8')

class KnowledgeBase:
    """Represents the entire knowledge base, managing the collection of KnowledgeNodes."""
    def __init__(self, obsidian_path: Path, git_enabled: bool = True):
        self.obsidian_path = Path(obsidian_path).resolve()
        print(f"Initializing KnowledgeBase with path: {self.obsidian_path}")  # Debug log
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.git_enabled = git_enabled
        
        # Ensure the directory exists
        if not self.obsidian_path.exists():
            print(f"Creating directory: {self.obsidian_path}")  # Debug log
            self.obsidian_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize git if enabled
        if git_enabled and not (self.obsidian_path / '.git').exists():
            GitCommands.init(self.obsidian_path)
    
    def ingest(self) -> None:
        """Ingest all markdown files from the Obsidian vault."""
        print(f"Ingesting markdown files from: {self.obsidian_path}")  # Debug log
        for md_file in self.obsidian_path.glob('**/*.md'):
            if md_file.is_file():  # Skip directories
                print(f"Processing file: {md_file}")  # Debug log
                node = KnowledgeNode.from_md_file(md_file)
                self.nodes[node.title] = node
                node.to_python_file()
        print(f"Ingested {len(self.nodes)} nodes")  # Debug log
            
    def commit_changes(self, message: str = "Auto-update from Cognosis") -> None:
        """Commit changes to git if enabled."""
        if self.git_enabled:
            print(f"Committing changes in: {self.obsidian_path}")  # Debug log
            GitCommands.add(self.obsidian_path, "*.py")
            GitCommands.commit(self.obsidian_path, message)

class CognosisRuntime:
    """Main runtime environment for the Cognosis system."""
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()
        print(f"Initializing CognosisRuntime with path: {self.base_path}")  # Debug log
        self.bases: Dict[str, KnowledgeBase] = {}
        
        # Ensure the base directory exists
        if not self.base_path.exists():
            print(f"Creating base directory: {self.base_path}")  # Debug log
            self.base_path.mkdir(parents=True, exist_ok=True)
        
    def add_base(self, name: str, path: Path) -> KnowledgeBase:
        """Add a new knowledge base to the runtime."""
        kb = KnowledgeBase(path)
        self.bases[name] = kb
        return kb
    
    def get_node(self, base_name: str, node_title: str) -> Optional[KnowledgeNode]:
        """Retrieve a specific node from a knowledge base."""
        base = self.bases.get(base_name)
        if base:
            return base.nodes.get(node_title)
        return None

    @contextmanager
    def transaction(self, base_name: str, commit_message: Optional[str] = None):
        """Context manager for making changes to a knowledge base."""
        base = self.bases.get(base_name)
        if not base:
            raise ValueError(f"Base {base_name} not found")
            
        try:
            yield base
            if commit_message:
                base.commit_changes(commit_message)
        except Exception as e:
            print(f"Transaction failed: {e}")
            raise

if __name__ == "__main__":
    from pathlib import Path

    runtime = CognosisRuntime(Path(".\\cognosis"))
    kb = runtime.add_base("kb", Path(".\\cognosis"))

    # Using the transaction context manager
    with runtime.transaction("kb", commit_message="Updated Zettelkasten notes"):
        kb.ingest()
        node = runtime.get_node("kb", "Zettelkasten")
        # Make changes to node if needed
        print(f'node(s) in kb: {kb.nodes}')