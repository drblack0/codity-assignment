from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class FileAnalysis:
    file_path: str
    functions: List[str]
    imports: List[str]
    language: str
    file_size: int
    processing_time: float


@dataclass
class RepositoryAnalysis:
    total_files: int
    total_functions: int
    total_imports: int
    languages_found: Set[str]
    processing_time: float
    files: List[FileAnalysis]
