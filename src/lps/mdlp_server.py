#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Language Server Protocol Server – three-layer split
* Parser     : incremental markdown → graph nodes
* GraphModel : arena-based document graph + undo-log
* LSPAdapter : JSON-RPC glue (stdio)

© 2025 MOONLAPSED | BSD-3 & CC ND | Morphological Source Code
"""

from __future__ import annotations

import os
import sys
import json
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote
from enum import IntEnum

logging.basicConfig(
    level=logging.DEBUG if os.getenv('IWE_DEBUG') else logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(threadName)s][%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('iwe-morphological.log'),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================================
# LSP PROTOCOL DATA STRUCTURES
# ============================================================================


@dataclass
class Position:
    line: int
    character: int

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "character": self.character}

    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        return cls(line=data['line'], character=data['character'])


@dataclass
class Range:
    start: Position
    end: Position

    def to_dict(self) -> Dict:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict) -> 'Range':
        return cls(
            start=Position.from_dict(data['start']), end=Position.from_dict(data['end'])
        )


@dataclass
class Location:
    uri: str
    range: Range

    def to_dict(self) -> Dict:
        return {"uri": self.uri, "range": self.range.to_dict()}


class SymbolKind(IntEnum):
    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18
    Object = 19
    Key = 20
    Null = 21
    EnumMember = 22
    Struct = 23


@dataclass
class Diagnostic:
    range: Range
    severity: int
    message: str
    source: str = "morphological"
    code: Optional[str] = None

    def to_dict(self) -> Dict:
        d = {
            "range": self.range.to_dict(),
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
        }
        if self.code:
            d["code"] = self.code
        return d


@dataclass
class DocumentSymbol:
    name: str
    kind: int
    range: Range
    selection_range: Range
    children: List['DocumentSymbol'] = field(default_factory=list)
    detail: Optional[str] = None

    def to_dict(self) -> Dict:
        d = {
            "name": self.name,
            "kind": self.kind,
            "range": self.range.to_dict(),
            "selectionRange": self.selection_range.to_dict(),
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        if self.detail:
            d["detail"] = self.detail
        return d


# ============================================================================
# LAYER 1 – PARSER : incremental markdown → graph nodes
# ============================================================================


class MarkdownParser:
    """Very small incremental parser. Re-parses whole doc for now,
    but keeps previous tree for future delta."""

    def __init__(self):
        self._prev_lines: List[str] = []

    def parse(self, uri: str, content: str) -> 'DocumentGraph':
        lines = content.splitlines()
        graph = DocumentGraph(uri, content)
        self._prev_lines = lines
        return graph


# ============================================================================
# LAYER 2 – GRAPH MODEL : arena + undo-log
# ============================================================================


@dataclass
class GraphNode:
    id: str
    node_type: str
    content: str
    level: int
    line_start: int
    line_end: int
    character_start: int = 0
    character_end: int = 0
    children: List['GraphNode'] = field(default_factory=list)
    parent: Optional['GraphNode'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: 'GraphNode'):
        child.parent = self
        self.children.append(child)

    def path_to_root(self) -> List['GraphNode']:
        path, cur = [self], self.parent
        while cur:
            path.append(cur)
            cur = cur.parent
        return list(reversed(path))

    def breadcrumbs(self) -> str:
        return " ⇒ ".join(n.content for n in self.path_to_root() if n.content)


class DocumentGraph:
    """Arena-style storage with spatial index (line→nodes)."""

    def __init__(self, uri: str, content: str):
        self.uri = uri
        self.content = content
        self.lines = content.splitlines()
        self.root = GraphNode(
            id="root",
            node_type="root",
            content="",
            level=0,
            line_start=0,
            line_end=len(self.lines),
            character_start=0,
            character_end=0,
        )
        self.nodes: Dict[str, GraphNode] = {"root": self.root}
        self._line_map: Dict[int, List[GraphNode]] = {}  # line -> nodes
        self._parse()

    # ---------- parsing ----------
    def _parse(self):
        current_parent = self.root
        current_level = 0
        for line_num, line in enumerate(self.lines):
            # header
            if line.strip().startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                content = line.lstrip('#').strip()
                node = GraphNode(
                    id=f"h{level}_{line_num}",
                    node_type="header",
                    content=content,
                    level=level,
                    line_start=line_num,
                    line_end=line_num + 1,
                    character_start=0,
                    character_end=len(line),
                )
                while current_level >= level and current_parent.parent:
                    current_parent = current_parent.parent
                    current_level = current_parent.level
                current_parent.add_child(node)
                self.nodes[node.id] = node
                self._line_map.setdefault(line_num, []).append(node)
                current_parent, current_level = node, level
            # code block
            elif line.strip().startswith('```'):
                code_lines, start_line = [line], line_num
                for i in range(line_num + 1, len(self.lines)):
                    code_lines.append(self.lines[i])
                    if self.lines[i].strip().startswith('```'):
                        line_num = i
                        break
                node = GraphNode(
                    id=f"code_{start_line}",
                    node_type="code",
                    content='\n'.join(code_lines),
                    level=current_level + 1,
                    line_start=start_line,
                    line_end=line_num + 1,
                    character_start=0,
                    character_end=len(code_lines[-1]),
                )
                current_parent.add_child(node)
                self.nodes[node.id] = node
                for l in range(start_line, line_num + 1):
                    self._line_map.setdefault(l, []).append(node)
            # list item
            elif line.strip().startswith(('- ', '* ', '+ ')):
                content = line.strip()[2:]
                node = GraphNode(
                    id=f"list_{line_num}",
                    node_type="list_item",
                    content=content,
                    level=current_level + 1,
                    line_start=line_num,
                    line_end=line_num + 1,
                    character_start=0,
                    character_end=len(line),
                )
                current_parent.add_child(node)
                self.nodes[node.id] = node
                self._line_map.setdefault(line_num, []).append(node)

    # ---------- spatial query ----------
    def nodes_at_line(self, line: int) -> List[GraphNode]:
        return self._line_map.get(line, [])

    def get_node_at_position(self, pos: Position) -> Optional[GraphNode]:
        for node in self.nodes_at_line(pos.line):
            if node.character_start <= pos.character <= node.character_end:
                return node
        return None

    # ---------- symbols ----------
    def get_symbols(self) -> List[DocumentSymbol]:
        def convert(n: GraphNode) -> Optional[DocumentSymbol]:
            if n.node_type == "root":
                return None
            kind = {
                "header": SymbolKind.Class,
                "code": SymbolKind.Function,
                "list_item": SymbolKind.Constant,
            }.get(n.node_type, SymbolKind.Variable)
            rng = Range(
                Position(n.line_start, n.character_start),
                Position(n.line_end, n.character_end),
            )
            sel = Range(
                Position(n.line_start, n.character_start),
                Position(n.line_start, n.character_end),
            )
            sym = DocumentSymbol(
                name=n.content[:50],
                kind=kind,
                range=rng,
                selection_range=sel,
                detail=f"{n.node_type} (level {n.level})",
            )
            for child in n.children:
                cs = convert(child)
                if cs:
                    sym.children.append(cs)
            return sym

        return [s for c in self.root.children if (s := convert(c))]

    # ---------- references ----------
    def find_references(self, target: str) -> List[GraphNode]:
        import re

        pat = re.compile(rf"\b{re.escape(target)}\b")
        hits = []
        for node in self.nodes.values():
            if node.node_type != "root" and pat.search(node.content):
                hits.append(node)
        return hits

    # ---------- extraction ----------
    def extract_section(self, node: GraphNode) -> str:
        lines = []

        def collect(n: GraphNode, level_offset: int = 0):
            if n.node_type == "header":
                lines.append("#" * (n.level + level_offset) + " " + n.content)
            elif n.node_type == "code":
                lines.append(n.content)
            elif n.node_type == "list_item":
                lines.append(f"- {n.content}")
            for c in n.children:
                collect(c, level_offset)

        collect(node)
        return "\n".join(lines)


# ---------- Undo log ----------
@dataclass
class _ReplaceContentCmd:
    uri: str
    old_content: str
    new_content: str

    def redo(self, store: 'DocumentStore'):
        store._apply_content(self.uri, self.new_content)

    def undo(self, store: 'DocumentStore'):
        store._apply_content(self.uri, self.old_content)


class UndoLog:
    def __init__(self):
        self._stack: List[Any] = []
        self._lock = threading.RLock()

    def push(self, cmd):
        with self._lock:
            self._stack.append(cmd)

    def pop(self) -> Optional[Any]:
        with self._lock:
            return self._stack.pop() if self._stack else None


# ============================================================================
# LAYER 2.5 – DOCUMENT STORE (thin wrapper)
# ============================================================================


class DocumentStore:
    def __init__(self):
        self._docs: Dict[str, DocumentGraph] = {}
        self._lock = threading.RLock()
        self.undo = UndoLog()
        self._parser = MarkdownParser()
        logger.info("DocumentStore initialised")

    def open_document(self, uri: str, content: str):
        with self._lock:
            self._docs[uri] = self._parser.parse(uri, content)
            logger.info("Opened %s", uri)

    def close_document(self, uri: str):
        with self._lock:
            self._docs.pop(uri, None)
            logger.info("Closed %s", uri)

    def update_document(self, uri: str, content: str):
        with self._lock:
            old = self._docs[uri].content
            self._docs[uri] = self._parser.parse(uri, content)
            self.undo.push(_ReplaceContentCmd(uri, old, content))
            logger.info("Updated %s", uri)

    def get_document(self, uri: str) -> Optional[DocumentGraph]:
        with self._lock:
            return self._docs.get(uri)

    def all_documents(self) -> List[Tuple[str, DocumentGraph]]:
        with self._lock:
            return list(self._docs.items())

    def _apply_content(self, uri: str, content: str):
        self._docs[uri] = self._parser.parse(uri, content)


# ============================================================================
# LAYER 3 – LSP ADAPTER : JSON-RPC stdio
# ============================================================================


class LSPMessage:
    @staticmethod
    def read_headers(rfile) -> Dict[str, str]:
        headers = {}
        while True:
            line = rfile.readline()
            if not line or line == b'\r\n':
                break
            if b':' in line:
                key, value = line.decode().strip().split(':', 1)
                headers[key.strip()] = value.strip()
        return headers

    @staticmethod
    def read_message(rfile) -> Optional[Dict]:
        try:
            hdr = LSPMessage.read_headers(rfile)
            if 'Content-Length' not in hdr:
                return None
            length = int(hdr['Content-Length'])
            content = rfile.read(length)
            msg = json.loads(content.decode())
            logger.debug("Recv: %s", msg.get('method', 'response'))
            return msg
        except Exception as e:
            logger.error("read error: %s", e, exc_info=True)
            return None

    @staticmethod
    def write_message(wfile, msg: Dict):
        content = json.dumps(msg, separators=(',', ':'))
        content_bytes = content.encode()
        hdr = f"Content-Length: {len(content_bytes)}\r\n\r\n"
        wfile.write(hdr.encode())
        wfile.write(content_bytes)
        wfile.flush()
        logger.debug("Sent: %s", msg.get('method', 'response'))


class LSPAdapter:
    def __init__(self, store: DocumentStore):
        self.store = store
        self.init = False
        self.shutdown = False
        self.caps = {
            "textDocumentSync": {
                "openClose": True,
                "change": 1,
                "save": {"includeText": True},
            },
            "documentSymbolProvider": True,
            "definitionProvider": True,
            "referencesProvider": True,
            "hoverProvider": True,
            "completionProvider": {"triggerCharacters": ["[", "#"]},
            "codeActionProvider": True,
            "documentFormattingProvider": True,
        }

    def handle(self, msg: Dict) -> Optional[Dict]:
        if "method" not in msg:
            return None
        method, params, mid = msg["method"], msg.get("params", {}), msg.get("id")
        handler = getattr(self, f"handle_{method.replace('/', '_')}", None)
        if not handler:
            logger.warning("unhandled %s", method)
            return (
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
                if mid
                else None
            )
        try:
            result = handler(params)
            if mid is not None:
                return {"jsonrpc": "2.0", "id": mid, "result": result}
        except Exception as e:
            logger.error("handler %s: %s", method, e, exc_info=True)
            if mid is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "error": {"code": -32603, "message": str(e)},
                }
        return None

    # lifecycle
    def handle_initialize(self, params):
        self.init = True
        return {
            "capabilities": self.caps,
            "serverInfo": {"name": "morphological-lsp", "version": "1.0.0"},
        }

    def handle_initialized(self, params):
        logger.info("Client initialized")

    def handle_shutdown(self, params):
        self.shutdown = True

    def handle_exit(self, params):
        sys.exit(0 if self.shutdown else 1)

    # documents
    def handle_textDocument_didOpen(self, p):
        self.store.open_document(p["textDocument"]["uri"], p["textDocument"]["text"])

    def handle_textDocument_didChange(self, p):
        self.store.update_document(
            p["textDocument"]["uri"], p["contentChanges"][0]["text"]
        )

    def handle_textDocument_didClose(self, p):
        self.store.close_document(p["textDocument"]["uri"])

    def handle_textDocument_didSave(self, p):
        logger.info("Saved %s", p["textDocument"]["uri"])

    # symbols
    def handle_textDocument_documentSymbol(self, p):
        doc = self.store.get_document(p["textDocument"]["uri"])
        return [s.to_dict() for s in doc.get_symbols()] if doc else []

    # definition
    def handle_textDocument_definition(self, p):
        uri, pos = p["textDocument"]["uri"], Position.from_dict(p["position"])
        doc = self.store.get_document(uri)
        if not doc or pos.line >= len(doc.lines):
            return None
        line = doc.lines[pos.line]
        import re

        for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', line):
            if m.start() <= pos.character <= m.end():
                target = m.group(2)
                current_path = Path(unquote(urlparse(uri).path))
                target_path = (current_path.parent / target).resolve()
                return {
                    "uri": target_path.as_uri(),
                    "range": Range(Position(0, 0), Position(0, 0)).to_dict(),
                }
        return None

    # references
    def handle_textDocument_references(self, p):
        uri, pos = p["textDocument"]["uri"], Position.from_dict(p["position"])
        doc = self.store.get_document(uri)
        if not doc:
            return []
        node = doc.get_node_at_position(pos)
        if not node:
            return []
        refs = []
        for u, d in self.store.all_documents():
            for hit in d.find_references(node.content):
                refs.append(
                    {
                        "uri": u,
                        "range": Range(
                            Position(hit.line_start, 0), Position(hit.line_end, 0)
                        ).to_dict(),
                    }
                )
        return refs

    # hover
    def handle_textDocument_hover(self, p):
        uri, pos = p["textDocument"]["uri"], Position.from_dict(p["position"])
        doc = self.store.get_document(uri)
        if not doc:
            return None
        node = doc.get_node_at_position(pos)
        if not node:
            return None
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**Path:** {node.breadcrumbs()}\n\n**Type:** `{node.node_type}`\n\n**Level:** {node.level}",
            }
        }

    # codeAction
    def handle_textDocument_codeAction(self, p):
        uri, rng = p["textDocument"]["uri"], Range.from_dict(p["range"])
        doc = self.store.get_document(uri)
        if not doc:
            return []
        node = doc.get_node_at_position(rng.start)
        if not node or node.node_type != "header":
            return []
        return [
            {
                "title": f"Extract section: {node.content}",
                "kind": "refactor.extract",
                "command": {
                    "title": "Extract Section",
                    "command": "morphological.extractSection",
                    "arguments": [uri, node.id],
                },
            }
        ]

    # formatting
    def handle_textDocument_formatting(self, p):
        uri = p["textDocument"]["uri"]
        doc = self.store.get_document(uri)
        if not doc:
            return []
        formatted = []
        prev_header = False
        for line in doc.lines:
            is_header = line.strip().startswith('#')
            if is_header and formatted and not prev_header:
                formatted.append('')
            formatted.append(line)
            prev_header = is_header
        new_text = "\n".join(formatted)
        return [
            {
                "range": Range(Position(0, 0), Position(len(doc.lines), 0)).to_dict(),
                "newText": new_text,
            }
        ]

    # completion
    def handle_textDocument_completion(self, p):
        uri, pos = p["textDocument"]["uri"], Position.from_dict(p["position"])
        doc = self.store.get_document(uri)
        if not doc or pos.line >= len(doc.lines):
            return {"items": []}
        line = doc.lines[pos.line][: pos.character]
        if not line.endswith('['):
            return {"items": []}
        items = []
        for u, d in self.store.all_documents():
            for node in d.nodes.values():
                if node.node_type == "header":
                    items.append(
                        {
                            "label": node.content,
                            "kind": 1,
                            "insertText": f"{node.content}]({u})",
                            "documentation": f"Link to: {node.breadcrumbs()}",
                        }
                    )
        return {"items": items}


# ============================================================================
# MAIN LOOP
# ============================================================================


def main():
    logger.info("Starting Morphological-IWE LSP Server")
    store = DocumentStore()
    adapter = LSPAdapter(store)
    try:
        while True:
            msg = LSPMessage.read_message(sys.stdin.buffer)
            if msg is None:
                break
            resp = adapter.handle(msg)
            if resp:
                LSPMessage.write_message(sys.stdout.buffer, resp)
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error("Fatal: %s", e, exc_info=True)
    finally:
        logger.info("Shutdown")


if __name__ == "__main__":
    main()
