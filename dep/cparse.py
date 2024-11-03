from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
import re
import shlex
import asyncio
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import ast


class CommandValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    SYNTAX_ERROR = "syntax_error"
    SECURITY_ERROR = "security_error"


@dataclass
class ParsedCommand:
    raw_input: str
    command_type: Optional[str] = None
    base_command: Optional[str] = None
    args: List[str] = None
    flags: Dict[str, Any] = None
    validation_status: CommandValidationStatus = CommandValidationStatus.PENDING
    error_message: Optional[str] = None

    def __post_init__(self):
        self.args = self.args or []
        self.flags = self.flags or {}


class CommandParser:
    """Handles parsing and validation of incoming commands."""

    KNOWN_COMMAND_PATTERNS = {
        'python': r'^python[3]?\s+(.+)$',
        'git': r'^git\s+(.+)$',
        'pip': r'^pip\s+install\s+(.+)$',
        'shell': r'^([\w\-\.]+)\s*(.*)$'  # Changed from 'bash' to be more generic
    }

    RESTRICTED_COMMANDS = {
        'rm': ['rm', 'remove', 'del', 'delete'],
        'sudo': ['sudo', 'su', 'runas'],
        'chmod': ['chmod', 'chown', 'attrib'],
        'eval': ['eval', 'exec', 'execute'],
    }

    RESTRICTED_PATTERNS = [
        r'rm\s+-[rf]+\s+.*',  # Dangerous file operations
        r'>[>&]?\s*.*',  # File redirections
        r'\|\s*(?:sh|bash)',  # Shell piping
        r'eval\s*\(',  # Python eval
        r'exec\s*\(',  # Python exec
        r'subprocess\..*',  # Direct subprocess calls
        r'os\.(system|popen|spawn|exec.*)',  # Dangerous OS operations
        r'import\s+os',  # OS import
        r'import\s+subprocess',  # Subprocess import
    ]

    def __init__(self):
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.logger = logging.getLogger(__name__)

    async def parse_and_validate(self, input_block: str) -> ParsedCommand:
        """
        Main entry point for parsing and validating commands.
        Uses blocking to ensure thread safety.
        """
        async with self._lock:
            try:
                # Initial parsing
                parsed_cmd = await self._initial_parse(input_block)

                # Security validation first
                if not await self._security_check(parsed_cmd):
                    parsed_cmd.validation_status = CommandValidationStatus.SECURITY_ERROR
                    return parsed_cmd

                # Syntax validation
                if not await self._syntax_check(parsed_cmd):
                    parsed_cmd.validation_status = CommandValidationStatus.SYNTAX_ERROR
                    return parsed_cmd

                # Command-specific validation
                await self._validate_command_specifics(parsed_cmd)

                return parsed_cmd

            except Exception as e:
                self.logger.error(f"Error parsing command: {str(e)}")
                return ParsedCommand(
                    raw_input=input_block,
                    validation_status=CommandValidationStatus.INVALID,
                    error_message=str(e)
                )

    async def _initial_parse(self, input_block: str) -> ParsedCommand:
        """Perform initial parsing of the command string."""
        input_block = input_block.strip()

        if not input_block:
            return ParsedCommand(
                raw_input=input_block,
                validation_status=CommandValidationStatus.INVALID,
                error_message="Empty command"
            )

        # First word is the base command
        try:
            words = shlex.split(input_block)
            base_cmd = words[0].lower()
        except ValueError as e:
            return ParsedCommand(
                raw_input=input_block,
                validation_status=CommandValidationStatus.INVALID,
                error_message=f"Invalid command syntax: {str(e)}"
            )

        # Check for restricted base commands
        for restricted_type, variants in self.RESTRICTED_COMMANDS.items():
            if base_cmd in variants:
                return ParsedCommand(
                    raw_input=input_block,
                    validation_status=CommandValidationStatus.SECURITY_ERROR,
                    error_message=f"Restricted command: {base_cmd}"
                )

        # Match against known patterns
        for cmd_type, pattern in self.KNOWN_COMMAND_PATTERNS.items():
            if match := re.match(pattern, input_block, re.IGNORECASE):
                try:
                    if cmd_type == 'python':
                        base_command = 'python'
                        args_str = match.group(1)
                    elif cmd_type == 'git':
                        base_command = 'git'
                        args_str = match.group(1)
                    else:
                        base_command = match.group(1)
                        args_str = match.group(2) if len(match.groups()) > 1 else ""

                    args_list = shlex.split(args_str) if args_str else []

                    return ParsedCommand(
                        raw_input=input_block,
                        command_type=cmd_type,
                        base_command=base_command,
                        args=args_list
                    )
                except ValueError as e:
                    return ParsedCommand(
                        raw_input=input_block,
                        validation_status=CommandValidationStatus.INVALID,
                        error_message=f"Invalid argument syntax: {str(e)}"
                    )

        return ParsedCommand(
            raw_input=input_block,
            validation_status=CommandValidationStatus.INVALID,
            error_message="Unknown command type"
        )

    async def _security_check(self, parsed_cmd: ParsedCommand) -> bool:
        """Check command against security restrictions."""
        if parsed_cmd.validation_status in [CommandValidationStatus.INVALID,
                                            CommandValidationStatus.SECURITY_ERROR]:
            return False

        cmd_str = f"{parsed_cmd.base_command} {' '.join(parsed_cmd.args)}"

        # Check against restricted patterns
        for pattern in self.RESTRICTED_PATTERNS:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                parsed_cmd.error_message = f"Command contains restricted operation: {pattern}"
                return False

        return True

    async def _syntax_check(self, parsed_cmd: ParsedCommand) -> bool:
        """Validate command syntax based on command type."""
        if parsed_cmd.validation_status != CommandValidationStatus.PENDING:
            return False

        if parsed_cmd.command_type == 'python':
            return await self._validate_python_syntax(parsed_cmd)
        elif parsed_cmd.command_type == 'git':
            return await self._validate_git_syntax(parsed_cmd)
        elif parsed_cmd.command_type == 'shell':
            return await self._validate_shell_syntax(parsed_cmd)
        return True

    async def _validate_python_syntax(self, parsed_cmd: ParsedCommand) -> bool:
        """Validate Python code syntax."""
        if not parsed_cmd.args:
            parsed_cmd.error_message = "No Python code or script provided"
            return False

        # Check if it's a Python file
        if parsed_cmd.args[0].endswith('.py'):
            return True

        # Otherwise, try to validate as Python code
        try:
            code = ' '.join(parsed_cmd.args)
            ast.parse(code)
            return True
        except SyntaxError as e:
            parsed_cmd.error_message = f"Python syntax error: {str(e)}"
            return False

    async def _validate_git_syntax(self, parsed_cmd: ParsedCommand) -> bool:
        """Validate Git command syntax."""
        valid_git_commands = {
            'clone', 'pull', 'push', 'commit', 'add', 'status',
            'branch', 'checkout', 'merge', 'init', 'fetch'
        }

        if not parsed_cmd.args:
            parsed_cmd.error_message = "No git subcommand provided"
            return False

        if parsed_cmd.args[0].lower() not in valid_git_commands:
            parsed_cmd.error_message = f"Invalid git subcommand: {parsed_cmd.args[0]}"
            return False

        return True

    async def _validate_shell_syntax(self, parsed_cmd: ParsedCommand) -> bool:
        """Validate shell command syntax."""
        if not parsed_cmd.base_command:
            parsed_cmd.error_message = "No shell command provided"
            return False

        # Add specific shell command validations here
        return True

    async def _validate_command_specifics(self, parsed_cmd: ParsedCommand) -> None:
        """Perform command-specific validation and cleaning."""
        if parsed_cmd.validation_status != CommandValidationStatus.PENDING:
            return

        if parsed_cmd.command_type == 'python':
            if len(parsed_cmd.args) > 0 and (
                    parsed_cmd.args[0].endswith('.py') or
                    await self._validate_python_syntax(parsed_cmd)
            ):
                parsed_cmd.validation_status = CommandValidationStatus.VALID
            else:
                parsed_cmd.validation_status = CommandValidationStatus.SYNTAX_ERROR

        elif parsed_cmd.command_type == 'git':
            if await self._validate_git_syntax(parsed_cmd):
                parsed_cmd.validation_status = CommandValidationStatus.VALID
            else:
                parsed_cmd.validation_status = CommandValidationStatus.INVALID

        elif parsed_cmd.command_type == 'shell':
            if await self._validate_shell_syntax(parsed_cmd):
                parsed_cmd.validation_status = CommandValidationStatus.VALID
            else:
                parsed_cmd.validation_status = CommandValidationStatus.INVALID
        else:
            parsed_cmd.validation_status = CommandValidationStatus.INVALID
            parsed_cmd.error_message = "Unsupported command type"


class SemanticTerminal:
    def __init__(self):
        self.command_parser = CommandParser()
        self.env = {
            "SHELL": "/bin/bash",
            "PYTHON_VERSION": "3.12",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PWD": "/home/project"
        }

    async def process_input(self, input_block: str) -> ParsedCommand:
        """
        Process input through the command parser with proper locking and validation.
        """
        parsed_cmd = await self.command_parser.parse_and_validate(input_block)

        if parsed_cmd.validation_status == CommandValidationStatus.VALID:
            return parsed_cmd
        else:
            # Log invalid commands
            if parsed_cmd.error_message:
                self.command_parser.logger.warning(
                    f"Invalid command attempted: {input_block}\n"
                    f"Error: {parsed_cmd.error_message}"
                )
            return parsed_cmd


async def main():
    terminal = SemanticTerminal()

    # Example commands to test
    test_commands = [
        "python script.py --arg1 value1",
        "python print('Hello, World!')",
        "git status",
        "git invalidcommand",
        "rm -rf /",
        "sudo apt-get update",
        "echo 'Hello World'",
        "invalid command",
        "",  # Empty command
    ]

    for cmd in test_commands:
        result = await terminal.process_input(cmd)
        print(f"\nCommand: {cmd}")
        print(f"Status: {result.validation_status}")
        if result.error_message:
            print(f"Error: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())