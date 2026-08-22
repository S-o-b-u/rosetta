from typing import Protocol, Any, Dict, List, Optional
from dataclasses import dataclass

class SourceAdapter(Protocol):
    """
    Interface for parsing legacy source code and extracting context.
    """
    def ingest_and_get_context(self, migration_id: str, file_path: str, target_method: str) -> dict:
        """
        Parses the source file, ingests it into Neo4j (if applicable),
        and returns the extracted AST context dictionary.
        """
        ...

class TargetGenerator(Protocol):
    """
    Interface for generating modern cloud-native service wrappers around pure logic.
    """
    def generate_service_code(self, func_source: str, method_name: str) -> str:
        """
        Generates the target framework service code wrapping the pure function.
        """
        ...

    def route_prefix_for(self, method_name: str) -> str:
        """
        Generates the standard URL route prefix for the given method name.
        """
        ...

    def file_extension(self) -> str:
        """
        Returns the appropriate file extension for the generated service file (e.g., '.py', '.js').
        """
        ...
        
    def entry_command(self) -> str:
        """
        Returns the interpreter/runtime command used to run the generated service
        (e.g., 'python', 'node'). The CLI combines this with the actual artifact
        path it wrote to disk to form the final run instruction.
        """
        ...
