#!/usr/bin/env -S uv run
from __future__ import annotations

# /* script
# requires-python = ">=3.12"
# dependencies = [
#     "uv==*.*",
# ]
# */
# Optional dependency handling (also add to '/* script..' comment, just above)
#   "© 2026 `Phovos` (phovos@outlook.com)":
#     - "Morphological Source Code: MSC&QSD"
#     - https://gitlab.com/morphological/source/code
#     - https://github.com/Morphological-Source-Code
#     - https://reddit.com/r/morphological
# © 2024-2026 https://github.com/Phovos/Morphological-Source-Code
# © 2023-2026 https://github.com/MOONLAPSED/cognosis
"""
Morphological Shell - A REPL that speaks C, Python, OCaml, Racket, and Fossil.
Each input is a *morphism* across language boundaries.
"""

import code
import subprocess
import sys
import os
import readline
import glob
from pathlib import Path
from typing import Dict, Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class Language(Enum):
    PYTHON = "python"
    OCAML = "ocaml"
    RACKET = "racket"
    FOSSIL = "fossil"
    SHELL = "shell"
    MULTILINE = "multiline"
    BLOB = "blob"

@dataclass
class DispatchRule:
    """A single morphological transformation rule"""
    pattern: str
    language: Language
    handler: Callable[[str], Optional[str]]
    requires_continuation: bool = False

class MorphologicalKernel(code.InteractiveConsole):
    """
    A REPL kernel that dispatches to multiple language runtimes.
    Each line is a potential *morphism* across language boundaries.
    """
    
    def __init__(self, locals=None, filename="<morph-shell>"):
        super().__init__(locals=locals, filename=filename)
        self.multiline_buffer = []
        self.current_language = Language.PYTHON
        self.project_root = Path.cwd()
        self.agents = {}  # Loaded OCaml agents via FFI
        
        # Define dispatch rules in order of precedence
        self.dispatch_rules = [
            # OCaml patterns (statements end with ;; in OCaml's REPL)
            DispatchRule(r"^\s*let\s+\w+\s*=.*;;\s*$", Language.OCAML, self.dispatch_ocaml),
            DispatchRule(r"^\s*module\s+\w+\s*=.*;;\s*$", Language.OCAML, self.dispatch_ocaml),
            
            # Racket patterns (#lang, @ syntax, require)
            DispatchRule(r"^\s*#lang\s+\w+", Language.RACKET, self.dispatch_racket),
            DispatchRule(r"^\s*@\(.*\)\s*$", Language.RACKET, self.dispatch_racket),
            DispatchRule(r"^\s*\(\s*require\s+", Language.RACKET, self.dispatch_racket),
            
            # Fossil commands
            DispatchRule(r"^\s*fossil\s+", Language.FOSSIL, self.dispatch_fossil),
            
            # Shell commands (explicit ! prefix)
            DispatchRule(r"^\s*!\s*", Language.SHELL, self.dispatch_shell),
            
            # OCaml toplevel directive
            DispatchRule(r"^\s*#\w+", Language.OCAML, self.dispatch_ocaml),
            
            # CPython FFI calls to loaded agents
            DispatchRule(r"^\s*load_agent\s+", Language.OCAML, self.dispatch_agent_loader),
            DispatchRule(r"^\s*agent\..+", Language.OCAML, self.dispatch_agent_call),
        ]
        
        # Multi-line triggers (need continuation)
        self.multiline_triggers = [
            (r"^\s*#lang", Language.RACKET),
            (r"^\s*@\(.*$", Language.RACKET, "  "),  # Indent next line
            (r"^\s*\(\s*define\s+", Language.RACKET),
            (r"^\s*\(\s*let\b", Language.RACKET),
            (r"^\s*module\s+\w+\s*=\s*struct\s*$", Language.OCAML),
            (r"^\s*let\s+.*=\s*$", Language.OCAML),  # Incomplete let binding
        ]
    
    def dispatch_ocaml(self, line: str) -> Optional[str]:
        """Send a line to OCaml toplevel (ocaml -init)"""
        # Strip trailing ;; if present
        code = line.rstrip(';').strip()
        try:
            # Use ocaml -e to evaluate one-liners
            result = subprocess.run(
                ["ocaml", "-e", code],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                print(f"\033[36m[OCaml]\033[0m {result.stdout}")
            if result.stderr:
                print(f"\033[31m[OCaml Error]\033[0m {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            print("\033[31m[OCaml] Evaluation timed out\033[0m")
        except FileNotFoundError:
            print("\033[31m[OCaml] 'ocaml' command not found. Install OCaml 5+\033[0m")
        return None
    
    def dispatch_racket(self, line: str) -> Optional[str]:
        """Dispatch to Racket (raco or racket -e)"""
        # Strip leading/trailing whitespace
        code = line.strip()
        
        # Handle explicit #lang blocks (multi-line)
        if code.startswith("#lang"):
            self.current_language = Language.RACKET
            self.multiline_buffer = [code]
            print("\033[35m[Racket multi-line mode] Enter your code, end with '}' on its own line\033[0m")
            return None  # Signal that we need more input
        
        # Single-line Racket eval
        try:
            result = subprocess.run(
                ["racket", "-e", code],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                print(f"\033[35m[Racket]\033[0m {result.stdout}")
            if result.stderr:
                print(f"\033[31m[Racket Error]\033[0m {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            print("\033[31m[Racket] Evaluation timed out\033[0m")
        except FileNotFoundError:
            print("\033[31m[Racket] 'racket' command not found. Install Racket\033[0m")
        return None
    
    def dispatch_fossil(self, line: str) -> Optional[str]:
        """Run Fossil SCM command in the current project repo"""
        cmd = line.strip()
        try:
            # Find nearest Fossil repo
            repo_path = self.find_fossil_repo()
            if repo_path:
                result = subprocess.run(
                    cmd.split(), cwd=repo_path,
                    capture_output=True, text=True
                )
            else:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"\033[33m[Fossil]\033[0m {result.stderr}")
            return result.stdout
        except Exception as e:
            print(f"\033[31m[Fossil Error]\033[0m {e}")
        return None
    
    def dispatch_shell(self, line: str) -> Optional[str]:
        """Run shell command (lines starting with !)"""
        cmd = line.lstrip('!').strip()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"\033[33m[Shell]\033[0m {result.stderr}")
            return result.stdout
        except Exception as e:
            print(f"\033[31m[Shell Error]\033[0m {e}")
        return None
    
    def dispatch_agent_loader(self, line: str) -> Optional[str]:
        """Load an OCaml agent via FFI (ctypes binding to compiled .so)"""
        import ctypes
        agent_name = line.split()[-1]
        try:
            lib = ctypes.CDLL(f"./_build/default/libagent_{agent_name}.so")
            # Assume the agent exports `init` symbol
            lib.init.argtypes = [ctypes.c_void_p]
            lib.init.restype = ctypes.c_int
            
            # Create runtime handle (placeholder)
            self.agents[agent_name] = lib
            print(f"\033[32m✓ Agent '{agent_name}' loaded\033[0m")
        except Exception as e:
            print(f"\033[31m✗ Failed to load agent '{agent_name}': {e}\033[0m")
        return None
    
    def dispatch_agent_call(self, line: str) -> Optional[str]:
        """Call a method on a loaded OCaml agent"""
        # Syntax: agent.quantum_monoid.compute(2,3)
        if not line.startswith("agent."):
            return None
        
        parts = line.split('.')
        if len(parts) < 2:
            return None
        
        agent_name = parts[1]
        if agent_name not in self.agents:
            print(f"\033[31mAgent '{agent_name}' not loaded. Use 'load_agent {agent_name}'\033[0m")
            return None
        
        # Call the agent's method (simplified)
        print(f"\033[36m[Agent {agent_name}]\033[0m Dispatching to OCaml FFI...")
        # Actual dispatch would go here
        return None
    
    def find_fossil_repo(self) -> Optional[Path]:
        """Walk up directory tree to find a .fslckout or _FOSSIL_ file"""
        path = self.project_root
        while path != path.parent:
            if (path / ".fslckout").exists() or (path / "_FOSSIL_").exists():
                return path
            path = path.parent
        return None
    
    def push(self, line: str) -> bool:
        """
        Push a line to the morphological kernel.
        Returns True if more input is needed (multiline mode).
        """
        line = line.strip()
        
        # Handle empty line in multiline mode (end of block)
        if self.multiline_buffer and not line:
            return self._execute_multiline_block()
        
        # Collect multiline input
        if self.multiline_buffer:
            self.multiline_buffer.append(line)
            if line == "}" or line == ";;":
                return self._execute_multiline_block()
            return True  # Still need more lines
        
        # Check dispatch rules first
        for rule in self.dispatch_rules:
            import re
            if re.match(rule.pattern, line):
                result = rule.handler(line)
                if result is not None:
                    return False  # Command handled
                break  # Try normal Python exec if handler returned None
        
        # Check if this line starts a multi-line block
        for trigger in self.multiline_triggers:
            import re
            if re.match(trigger[0], line):
                self.current_language = trigger[1]
                self.multiline_buffer = [line]
                indent = trigger[2] if len(trigger) > 2 else ""
                if indent:
                    print(f"  {indent}", end="")
                return True
        
        # Fallback to normal Python execution
        return super().push(line)
    
    def _execute_multiline_block(self) -> bool:
        """Execute a collected multiline block in the appropriate language"""
        if not self.multiline_buffer:
            return False
        
        block = "\n".join(self.multiline_buffer)
        
        if self.current_language == Language.RACKET:
            # Save to temp file and evaluate
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rkt', delete=False) as f:
                f.write(block)
                temp_file = f.name
            try:
                result = subprocess.run(
                    ["racket", temp_file],
                    capture_output=True, text=True
                )
                if result.stdout:
                    print(f"\033[35m[Racket result]\033[0m\n{result.stdout}")
                if result.stderr:
                    print(f"\033[31m[Racket error]\033[0m\n{result.stderr}")
            finally:
                os.unlink(temp_file)
        elif self.current_language == Language.OCAML:
            # OCaml multiline (module definitions, etc.)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ml', delete=False) as f:
                f.write(block)
                temp_file = f.name
            try:
                result = subprocess.run(
                    ["ocamlc", "-c", temp_file],  # Just compile to check
                    capture_output=True, text=True
                )
                if result.stderr:
                    print(f"\033[31m[OCaml error]\033[0m\n{result.stderr}")
                else:
                    print("\033[32m[OCaml] Module compiled successfully\033[0m")
            finally:
                os.unlink(temp_file)
        
        self.multiline_buffer = []
        self.current_language = Language.PYTHON
        return False
    
    def interact(self, banner: str = None, exitmsg: str = None):
        """Start the morphological REPL with custom completion"""
        if banner is None:
            banner = """
╔══════════════════════════════════════════════════════════════╗
║  Morphological Shell - Multi-Language REPL                  ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  Languages: Python, OCaml, Racket, Fossil, Shell            ║
║                                                             ║
║  Try these:                                                 ║
║    • 2 + 2                           (Python)               ║
║    • let x = 5;;                     (OCaml)                ║
║    • #lang racket/base               (Racket multi-line)    ║
║    • fossil timeline                 (Fossil)               ║
║    • ! ls -la                        (Shell)                ║
║    • load_agent quantum_monoid       (OCaml FFI)            ║
║                                                             ║
║  Tab completion: project commands, agents, languages        ║
╚══════════════════════════════════════════════════════════════╝
"""
        super().interact(banner=banner, exitmsg=exitmsg)


# -----------------------------------------------------------------------------
# Tab Completion Across All Languages
# -----------------------------------------------------------------------------

class MorphologicalCompleter:
    """Tab completion for the multi-language REPL"""
    
    def __init__(self, kernel: MorphologicalKernel):
        self.kernel = kernel
        self.commands = [
            # Language switchers
            ":python", ":ocaml", ":racket", ":fossil", ":shell",
            # Project commands
            "build", "test", "clean", "repl",
            # Racket specific
            "raco pollen render", "raco test", "raco setup",
            # OCaml specific
            "dune build", "dune runtest", "ocamlopt -c",
            # Fossil specific
            "fossil timeline", "fossil commit -m", "fossil branch", "fossil ui",
            # Agent commands
            "load_agent", "agent.", "list_agents",
            # Utility
            "clear", "exit", "help"
        ]
    
    def complete(self, text: str, state: int) -> Optional[str]:
        """Return the state-th completion for text"""
        line = readline.get_line_buffer()
        if not line:
            return None
        
        # Path completion for arguments
        if " " in line and not line.endswith(" "):
            # We're completing a file path
            parts = line.split()
            if len(parts) > 1:
                last_part = parts[-1]
                matches = glob.glob(last_part + "*")
                if matches and state < len(matches):
                    return matches[state]
        
        # Command completion
        matches = [cmd for cmd in self.commands if cmd.startswith(text)]
        if state < len(matches):
            return matches[state] + " "
        
        return None


def setup_completion(kernel: MorphologicalKernel):
    """Configure readline with morphological completion"""
    completer = MorphologicalCompleter(kernel)
    readline.set_completer(completer.complete)
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set show-all-if-ambiguous on")

if __name__ == "__main__":
    kernel = MorphologicalKernel()
    setup_completion(kernel)
    kernel.interact()
