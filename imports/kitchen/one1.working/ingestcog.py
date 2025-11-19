from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import re
import subprocess
from io import StringIO
import shutil
import json

class GitInterface:
    """Pure stdlib git interface using subprocess."""
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def _run_git(self, *args) -> str:
        """Run git command and return output."""
        try:
            result = subprocess.run(
                ['git'] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")

    def add(self, pattern: str) -> None:
        self._run_git('add', pattern)

    def commit(self, message: str) -> None:
        self._run_git('commit', '-m', message)

    def status(self) -> str:
        return self._run_git('status')

class MarkdownParser:
    """Pure stdlib markdown frontmatter parser."""
    @staticmethod
    def parse(content: str) -> tuple[dict, str]:
        """Parse markdown content with YAML frontmatter."""
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    content = parts[2].strip()
                except yaml.YAMLError:
                    metadata = {}
                    content = content
            else:
                metadata = {}
        else:
            metadata = {}
        return metadata, content

@dataclass
class KnowledgeNode:
    """Represents a single node of knowledge, mapping to an Obsidian markdown file."""
    title: str
    content: str
    path: Path
    py_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_md_file(cls, md_path: Path) -> 'KnowledgeNode':
        """Create a KnowledgeNode from an existing markdown file."""
        content = md_path.read_text(encoding='utf-8')
        metadata, content = MarkdownParser.parse(content)
        py_path = md_path.with_suffix('.py')
        
        # Extract wiki-style links
        links = re.findall(r'\[\[(.*?)\]\]', content)
        
        # Extract tags
        tags = [tag.strip('#') for tag in re.findall(r'#(\w+)', content)]
        
        # Get file modification time
        last_modified = datetime.fromtimestamp(md_path.stat().st_mtime)
        
        return cls(
            title=md_path.stem,
            content=content,
            path=md_path,
            py_path=py_path,
            metadata=metadata,
            links=links,
            tags=tags,
            last_modified=last_modified
        )
    
    def to_python_file(self) -> None:
        """Convert the markdown content to a Python representation."""
        python_content = f'''"""
{self.content}
"""

from dataclasses import dataclass
from datetime import datetime

@dataclass
class {self.title.replace(" ", "_")}Node:
    """Auto-generated from Obsidian note: {self.title}"""
    content: str = """{self.content}"""
    metadata: dict = {self.metadata}
    links: list = {self.links}
    tags: list = {self.tags}
    last_modified: datetime = datetime.fromisoformat("{self.last_modified.isoformat()}")
    
    def get_backlinks(self, kb):
        """Get all nodes that link to this one."""
        return [node for node in kb.nodes.values() if self.title in node.links]
        
    def to_json(self) -> str:
        """Serialize node to JSON."""
        return json.dumps({
            "title": "{self.title}",
            "content": self.content,
            "metadata": self.metadata,
            "links": self.links,
            "tags": self.tags,
            "last_modified": self.last_modified.isoformat()
        }, indent=2)
'''
        self.py_path.write_text(python_content)

class KnowledgeBase:
    """Represents the entire knowledge base, managing the collection of KnowledgeNodes."""
    def __init__(self, obsidian_path: Path, git_enabled: bool = True):
        self.obsidian_path = obsidian_path
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.git_enabled = git_enabled
        self.git = GitInterface(obsidian_path) if git_enabled else None
        
    def ingest(self) -> None:
        """Ingest all markdown files from the Obsidian vault."""
        for md_file in self.obsidian_path.glob('**/*.md'):
            if '.git' not in md_file.parts:  # Skip .git directory
                node = KnowledgeNode.from_md_file(md_file)
                self.nodes[node.title] = node
                node.to_python_file()
            
    def commit_changes(self, message: str = "Auto-update from Cognosis") -> None:
        """Commit changes to git if enabled."""
        if self.git_enabled and self.git:
            self.git.add('*.py')
            self.git.commit(message)

class PlatformCommands:
    """Platform-specific command execution."""
    @staticmethod
    def run_command(command: list[str]) -> str:
        """Run a platform command and return output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed: {e.stderr}")

class WindowsPlatform(PlatformCommands):
    """Windows-specific implementations using PowerShell."""
    @classmethod
    def copy_file(cls, src: Path, dst: Path) -> None:
        cls.run_command(['powershell', '-Command', f'Copy-Item -Path "{src}" -Destination "{dst}"'])

class LinuxPlatform(PlatformCommands):
    """Linux-specific implementations using bash."""
    @classmethod
    def copy_file(cls, src: Path, dst: Path) -> None:
        cls.run_command(['cp', str(src), str(dst)])

class CognosisRuntime:
    """Main runtime environment for the Cognosis system."""
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.bases: Dict[str, KnowledgeBase] = {}
        # Determine platform
        self.platform = WindowsPlatform if self._is_windows() else LinuxPlatform
        
    @staticmethod
    def _is_windows() -> bool:
        """Check if running on Windows."""
        return subprocess.run(['systeminfo'], capture_output=True).returncode == 0
    
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


if __name__ == "__main__":
    from pathlib import Path

    # Initialize with platform awareness
    runtime = CognosisRuntime(Path(".\\cognosis"))
    print(f'runtime: {runtime.base_path}')
    # Add and ingest knowledge base
    kb = runtime.add_base("kb", Path("\\Documents\\abraxus"))
    kb.ingest()
    print(f'kb as dict: {kb.__dict__}')