#!/usr/bin/env python3
"""
This sample builds a simple knowledge base quine system that using
the T, V, C FrameModel and __Atom__.
- Reads a markdown file (a KB entry)
- Wraps content with delimiters (defining a "frame")
- Creates a __Atom__ that encapsulates the frame (knowledge as code & data)
- Provides self-referential behavior via a quine method
- Allows content updates if they pass validation
`Ω = (λx. x x) (λx. x x)`, or the omega combinator, is the fundemental feed-
back loop associated with exploration/energy/knowledge/motility/etc.
"""

import os
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
from datetime import datetime
import re

# Optional: Use PyYAML for frontmatter parsing if needed.
try:
    import yaml
except ImportError:
    yaml = None  # If unavailable, you can skip YAML-based frontmatter parsing.

# Define type variables for Type, Value, and Computation spaces.
T = TypeVar("T")
V = TypeVar("V")
C = TypeVar("C")

# ------------------------------------------------------------------------------
# FrameModel: Represents a frame with delimited content.
# ------------------------------------------------------------------------------


class FrameModel(Generic[T, V, C], ABC):
    def init(self, start_delimiter: str = "<<CONTENT>>", end_delimiter: str = "<<END_CONTENT>>"):
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter

    @abstractmethod
    def to_bytes(self) -> bytes:
        """Return the frame data as bytes."""
        pass

    @abstractmethod
    def parse_content(self, raw_content: str) -> str:
        """Parse the raw content between the defined delimiters."""
        pass

    def validate_content(self, content: str) -> bool:
        """Validate that content is wrapped with the proper delimiters."""
        return content.startswith(self.start_delimiter) and content.endswith(self.end_delimiter)


@dataclass
class CustomDelimiterFrame(FrameModel[str, str, Any]):
    content: str
    start_delimiter: str = field(init=False, default="<<CONTENT>>")
    end_delimiter: str = field(init=False, default="<<END_CONTENT>>")

    def __post_init__(self):
        self.init()

    def to_bytes(self) -> bytes:
        return self.content.encode("utf-8")

    def parse_content(self, raw_content: str) -> str:
        start_index = raw_content.find(self.start_delimiter)
        end_index = raw_content.rfind(self.end_delimiter)
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            raise ValueError(
                "Invalid content format: delimiters not found or mismatched.")
        # Extract and return the content between delimiters.
        return raw_content[start_index + len(self.start_delimiter):end_index]

# ------------------------------------------------------------------------------
# __Atom__: Self-referential unit that encapsulates a FrameModel.
# ------------------------------------------------------------------------------


class __Atom__(Generic[T, V, C]):
    def __init__(self, frame: FrameModel[T, V, C]):
        self.frame = frame
        self.source = frame.content  # Represents the "knowledge" source code.
        self.last_updated = datetime.now()

    def quine(self) -> str:
        """Return a self-referential representation of this __Atom__."""
        return f"{self.__class__.__name__} (last updated: {self.last_updated.isoformat()})\nContent:\n{self.source}"

    def update(self, new_content: str) -> None:
        """
        Update the __Atom__'s content if it passes validation.
        The new content must be wrapped in the correct delimiters.
        """
        if self.frame.validate_content(new_content):
            self.frame.content = new_content
            self.source = new_content
            self.last_updated = datetime.now()
        else:
            raise ValueError("New content does not pass delimiter validation.")

    def execute(self) -> None:
        """For demonstration: 'execute' the content (here, simply print it)."""
        print("Executing __Atom__ content:")
        print(self.source)

# ------------------------------------------------------------------------------
# Utility functions for file handling and content wrapping.
# ------------------------------------------------------------------------------


def load_markdown_file(file_path: str) -> str:
    """Load the entire content of a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def wrap_content_with_delimiters(content: str, start: str = "<<CONTENT>>", end: str = "<<END_CONTENT>>") -> str:
    """Wrap raw content with start and end delimiters."""
    return f"{start}{content}{end}"

# ------------------------------------------------------------------------------
# Main execution: Demonstrate loading, quining, and updating knowledge.
# ------------------------------------------------------------------------------


def main():
    kb_file = "example.md"

    # Create a sample KB entry if it doesn't exist.
    if not os.path.exists(kb_file):
        sample_content = "This is a sample knowledge base entry."
        with open(kb_file, "w", encoding="utf-8") as f:
            f.write(wrap_content_with_delimiters(sample_content))

    # Load the KB content.
    content = load_markdown_file(kb_file)

    # Create a CustomDelimiterFrame instance with the loaded content.
    frame = CustomDelimiterFrame(content=content)

    # Instantiate an __Atom__ with the frame.
    atom = __Atom__(frame=frame)

    # Print the quine (self-referential representation).
    print(atom.quine())

    # "Execute" the atom (simulate processing the knowledge).
    atom.execute()

    # Update the atom's content.
    new_content = wrap_content_with_delimiters("Updated knowledge base entry.")
    atom.update(new_content)

    print("\nAfter update:")
    print(atom.quine())


if __name__ == "__main__":
    main()
