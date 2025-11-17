from __future__ import annotations

#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.12"
# dependencies = [
#     "uv==*.*",
# ]
# */
# Optional dependency handling (also add to '/* script..' comment, just above)
# ------------------------------
# 3.14 std libs **ONLY**      |
# Platform(s):                |
# Win11: production           |
# Ubuntu-22.04: staging       |
# ------------------------------
# > © 2025 Quineic https://github.com/Quineic/ | CC ND && BSD-3 | SEE LICENSE
# > © 2024 Phovos https://github.com/Phovos/Morphologic
# > © 2023 Moonlapsed https://github.com/MOONLAPSED/Cognosis
try:
    import flask

    USE_FLASK = True
    # if we omit "flask==*.*", or any non-std lib from the '/* script..' comment, then this should always fail
    pass
except ImportError:
    USE_FLASK = False
    coreLSP = False
# Import standard library components
import os
import sys
import ast
import json
import uuid
import time
import logging
import inspect
import hashlib
from socketserver import ThreadingMixIn
from typing import Any, Dict
from types import ModuleType
from dataclasses import dataclass
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Add a NullHandler by default


def create_module(
    module_name: str, module_code: str, main_module_path: str
) -> ModuleType | None:
    """
    Dynamically creates a module with the specified name, injects code into it,
    and adds it to sys.modules.

    Args:
        module_name (str): Name of the module to create.
        module_code (str): Source code to inject into the module.
        main_module_path (str): File path of the main module.

    Returns:
        ModuleType | None: The dynamically created module, or None if an error occurs.
    """
    dynamic_module = ModuleType(module_name)
    dynamic_module.__file__ = main_module_path or "runtime_generated"
    dynamic_module.__package__ = module_name
    dynamic_module.__path__ = None
    dynamic_module.__doc__ = None
    try:
        exec(module_code, dynamic_module.__dict__)
        sys.modules[module_name] = dynamic_module
        return dynamic_module
    except Exception as e:
        print(f"Error injecting code into module {module_name}: {e}")
        return None


def setup_logging(log_dir="logs", log_file="app.log", level=logging.INFO):
    """Sets up logging configuration and returns a logger for the calling module."""
    logs_path = Path(log_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    log_filepath = logs_path / log_file
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(levelname)s]%(asctime)s||%(name)s: %(message)s',
                'datefmt': '%Y-%m-%d~%H:%M:%S%z',
            }
        },
        'handlers': {
            'console': {
                'level': level,
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'level': level,
                'formatter': 'default',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_filepath),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
            },
        },
        'loggers': {
            __name__: {
                'level': level,
                'handlers': ['console', 'file'],
                'propagate': False,
            }
        },
        'root': {'level': level, 'handlers': ['console', 'file']},
    }
    logging.config.dictConfig(logging_config)
    frame = inspect.currentframe().f_back  # Get the name of the calling module
    module_name = frame.f_globals['__name__']
    return logging.getLogger(module_name)


# We use a custom adapter to inject the request_id into every log message.


class ContextualLogger(logging.LoggerAdapter):
    """A logger adapter to inject contextual information into log messages."""

    def process(self, msg, kwargs):
        if 'request_id' not in self.extra:
            self.extra['request_id'] = 'SYSTEM'
        return '[%s] %s' % (self.extra['request_id'], msg), kwargs


def get_logger(name: str, request_id: str = 'SYSTEM') -> ContextualLogger:
    """Configures and returns a context-aware logger."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(name)
    return ContextualLogger(logger, {'request_id': request_id})


class EngineError(Exception):
    """Base exception for all custom engine errors for clean catching."""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class InputValidationError(EngineError):
    """Raised for hostile or malformed input."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class SecurityViolationError(EngineError):
    """Raised for actions that violate security policy (e.g., path traversal)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=403)


class ResourceLimitExceededError(EngineError):
    """Raised when input exceeds configured resource limits."""

    def __init__(self, message: str):
        super().__init__(message, status_code=413)


class JsonLogFormatter(logging.Formatter):
    """
    Formats log records as JSON strings. This is non-negotiable for machine
    parsing and integration with modern log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "source": record.name,
            "context": getattr(record, 'context', {}),
        }
        return json.dumps(log_object)


def setup_logging() -> logging.Logger:
    """Configures and returns a root logger for the engine."""
    logger = logging.getLogger("HAES_Engine")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


@dataclass(frozen=True)
class InputArtifact:
    """
    An immutable data transfer object representing the validated input.
    Ensures data integrity from the point of ingestion.
    """

    correlation_id: str
    source_path: str
    content: str
    content_hash_sha256: str
    size_bytes: int

    def __post_init__(self):
        # Final integrity check upon instantiation
        actual_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
        if self.content_hash_sha256 != actual_hash:
            raise SecurityViolationError(
                "Content hash mismatch during artifact creation."
            )


@dataclass(frozen=True)
class SemanticGraph:
    """
    The final, signed output artifact. Represents the result of the analysis.
    The 'graph_data' is where the future semantic analysis output will reside.
    """

    source_artifact_hash: str
    processed_at_unix_ts: float
    engine_version: str
    graph_data: Dict[str, Any]
    signature_hmac_sha256: str

    def to_json(self) -> str:
        """Serializes the object to a JSON string for transport."""
        data = {
            "source_artifact_hash": self.source_artifact_hash,
            "processed_at_unix_ts": self.processed_at_unix_ts,
            "engine_version": "1.0.0",
            "graph_data": self.graph_data,
            "signature_hmac_sha256": self.signature_hmac_sha256,
        }
        return json.dumps(data, indent=2)


class ArtifactProcessor:
    """Encapsulates the core business logic of the engine."""

    def __init__(self, config: EngineConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def _validate_and_sanitize_path(self, path: str, correlation_id: str) -> str:
        """
        Performs rigorous validation on the input file path.
        """
        log_ctx = {"correlation_id": correlation_id, "path": path}

        if not path or not isinstance(path, str):
            raise InputValidationError("File path must be a non-empty string.")

        # Security: Prevent path traversal attacks.
        normalized_path = os.path.normpath(path)
        if os.path.isabs(normalized_path) or normalized_path.startswith(".."):
            raise SecurityViolationError("Path traversal attempt detected.")

        # Hygiene: Enforce allowed file extensions.
        _, ext = os.path.splitext(normalized_path)
        if ext not in self.config.ALLOWED_EXTENSIONS:
            raise InputValidationError(
                f"Invalid file extension. Allowed: {self.config.ALLOWED_EXTENSIONS}"
            )

        self.logger.info("Path validated and sanitized.", extra={"context": log_ctx})
        return normalized_path

    def _validate_content(self, content: bytes, correlation_id: str) -> str:
        """
        Validates the raw file content for size and syntax.
        """
        log_ctx = {"correlation_id": correlation_id, "size_bytes": len(content)}

        # Security: Enforce file size limits to prevent DoS.
        if len(content) > self.config.MAX_FILE_SIZE_BYTES:
            raise ResourceLimitExceededError(
                f"File size exceeds limit of {self.config.MAX_FILE_SIZE_BYTES} bytes."
            )

        # Hygiene: Decode and perform a preliminary syntax check.
        try:
            decoded_content = content.decode('utf-8')
            ast.parse(decoded_content)
        except UnicodeDecodeError:
            raise InputValidationError("File content is not valid UTF-8.")
        except SyntaxError as e:
            raise InputValidationError(f"Invalid Python syntax: {e}")

        self.logger.info("Content validated.", extra={"context": log_ctx})
        return decoded_content

    def process_source_file(
        self, path: str, content: bytes, correlation_id: str
    ) -> SemanticGraph:
        """
        The main entry point for processing a single source file.
        Orchestrates validation, artifact creation, and analysis.
        """
        log_ctx = {"correlation_id": correlation_id}
        self.logger.info("Beginning artifact processing.", extra={"context": log_ctx})

        # 1. Validate and create the input artifact
        sanitized_path = self._validate_and_sanitize_path(path, correlation_id)
        validated_content = self._validate_content(content, correlation_id)

        input_artifact = InputArtifact(
            correlation_id=correlation_id,
            source_path=sanitized_path,
            content=validated_content,
            content_hash_sha256=hashlib.sha256(
                validated_content.encode('utf-8')
            ).hexdigest(),
            size_bytes=len(validated_content.encode('utf-8')),
        )
        log_ctx["input_artifact_hash"] = input_artifact.content_hash_sha256
        self.logger.info("Input artifact created.", extra={"context": log_ctx})

        # 2. Perform the "semantic analysis" (placeholder)
        analysis_start_time = time.time()

        # For this scaffolding, the graph is just a metadata wrapper.
        graph_data = {
            "source_path": input_artifact.source_path,
            "size_bytes": input_artifact.size_bytes,
            "content_preview": input_artifact.content[:256] + "...",
        }

        analysis_duration_ms = (time.time() - analysis_start_time) * 1000
        log_ctx["analysis_duration_ms"] = round(analysis_duration_ms, 2)
        self.logger.info("Semantic analysis complete.", extra={"context": log_ctx})

        # 3. Create and sign the output artifact
        output_payload = {
            "source_artifact_hash": input_artifact.content_hash_sha256,
            "processed_at_unix_ts": time.time(),
            "engine_version": "1.0.0",
            "graph_data": graph_data,
        }

        # Security: Sign the payload to ensure authenticity and integrity.
        payload_bytes = json.dumps(output_payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            self.config.HMAC_SECRET_KEY, payload_bytes, hashlib.sha256
        ).hexdigest()

        semantic_graph = SemanticGraph(
            **output_payload, signature_hmac_sha256=signature
        )
        self.logger.info(
            "Semantic graph created and signed.", extra={"context": log_ctx}
        )

        return semantic_graph


class EngineRequestHandler(BaseHTTPRequestHandler):
    """
    Handles incoming HTTP requests, enforcing security and protocol hygiene.
    """

    # These are class-level to be set by the server factory
    processor: ArtifactProcessor
    config: EngineConfig
    logger: logging.Logger

    def _send_response(self, status_code: int, content_type: str, body: bytes):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Correlation-ID", self.correlation_id)
        self.end_headers()
        self.wfile.write(body)

    def _handle_error(self, e: Exception):
        if isinstance(e, EngineError):
            status_code = e.status_code
            message = str(e)
        else:
            status_code = 500
            message = "An unexpected internal error occurred."
            self.logger.error(
                "Unhandled exception.",
                exc_info=True,
                extra={"context": {"correlation_id": self.correlation_id}},
            )

        error_body = json.dumps({"error": message}).encode('utf-8')
        self._send_response(status_code, "application/json", error_body)

    def do_POST(self):
        self.correlation_id = self.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        log_ctx = {
            "correlation_id": self.correlation_id,
            "method": "POST",
            "path": self.path,
        }
        self.logger.info("Request received.", extra={"context": log_ctx})

        try:
            if self.path != "/analyze":
                raise InputValidationError("Endpoint not found. Use POST /analyze.")

            content_len = int(self.headers.get('Content-Length', 0))
            if content_len > self.config.MAX_REQUEST_BODY_SIZE:
                raise ResourceLimitExceededError("Request body too large.")

            body = self.rfile.read(content_len)
            data = json.loads(body)

            path = data.get("path")
            content_b64 = data.get("content_b64")
            if not path or not content_b64:
                raise InputValidationError(
                    "Request body must contain 'path' and 'content_b64'."
                )

            import base64

            content_bytes = base64.b64decode(content_b64)

            # Process the artifact
            result_graph = self.processor.process_source_file(
                path, content_bytes, self.correlation_id
            )

            # Send successful response
            response_body = result_graph.to_json().encode('utf-8')
            self._send_response(200, "application/json", response_body)
            self.logger.info(
                "Request processed successfully.", extra={"context": log_ctx}
            )

        except Exception as e:
            self._handle_error(e)

    def do_GET(self):
        self.correlation_id = self.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        if self.path == "/health":
            body = json.dumps({"status": "healthy", "timestamp": time.time()}).encode(
                'utf-8'
            )
            self._send_response(200, "application/json", body)
        else:
            self._handle_error(InputValidationError("Endpoint not found."))


class ThreadedEngineServer(ThreadingHTTPServer, ThreadingMixIn):
    """A ThreadingHTTPServer that allows for dependency injection."""

    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, processor, config, logger):
        RequestHandlerClass.processor = processor
        RequestHandlerClass.config = config
        RequestHandlerClass.logger = logger
        super().__init__(server_address, RequestHandlerClass)


# Example usage
module_name = "quine"
module_code = """
def greet():
    print("Hello from the Morphological Source Code module! This is Replicator-code ('Quine-like behavior')!")
"""
main_module_path = getattr(sys.modules['__main__'], '__file__', 'runtime_generated')

dynamic_module = create_module(module_name, module_code, main_module_path)
if dynamic_module:
    sys.exit(dynamic_module.greet())
