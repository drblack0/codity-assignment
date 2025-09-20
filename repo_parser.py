from dataclasses import asdict
import os
import json
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from data_classes import FileAnalysis, RepositoryAnalysis
from config import LANGUAGE_CONFIGS, logger

try:
    from tree_sitter import Parser
    from tree_sitter_languages import get_language
except ImportError:
    print("Required dependencies not found. Please install:")
    print("pip install tree-sitter tree-sitter-languages")
    exit(1)

WORKER_LANGUAGES = {}


def _get_language_for_worker(lang_name: str):
    """
    Loads and caches a tree-sitter language and its queries within a worker process.
    This prevents re-loading from disk for every file.
    """
    if lang_name not in WORKER_LANGUAGES:
        try:
            config = LANGUAGE_CONFIGS[lang_name]
            language = get_language(config["language_name"])
            WORKER_LANGUAGES[lang_name] = {
                "parser_lang": language,
                "queries": {
                    "imports": language.query(config["queries"]["imports"]),
                    "functions": language.query(config["queries"]["functions"]),
                },
            }
        except Exception as e:
            # If loading fails, store None to avoid retrying
            WORKER_LANGUAGES[lang_name] = None
            logger.warning(f"Worker failed to load language '{lang_name}': {e}")

    return WORKER_LANGUAGES[lang_name]


class PerformantRepositoryParser:
    def __init__(
        self,
        max_workers: Optional[int] = None,
        max_file_size: int = 10 * 1024 * 1024,
        use_cache: bool = True,
        cache_dir: str = ".repo_cache",
    ):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.max_file_size = max_file_size
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir)

        # Create a simple mapping from extension to language name.
        # This data IS pickle-able and safe to have here.
        self.extension_to_lang_name = {
            ext: name
            for name, config in LANGUAGE_CONFIGS.items()
            for ext in config["extensions"]
        }

        if self.use_cache:
            self.cache_dir.mkdir(exist_ok=True)

    def _get_file_hash(self, file_path: Path) -> str:
        stat = file_path.stat()
        content = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()

    def _load_from_cache(self, file_path: Path) -> Optional[FileAnalysis]:
        if not self.use_cache:
            return None
        cache_file = self.cache_dir / f"{self._get_file_hash(file_path)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return FileAnalysis(**json.load(f))
            except Exception as e:
                logger.debug(f"Cache load failed for {file_path}: {e}")
        return None

    def _save_to_cache(self, analysis: FileAnalysis):
        if not self.use_cache:
            return
        try:
            cache_file = (
                self.cache_dir / f"{self._get_file_hash(Path(analysis.file_path))}.json"
            )
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(asdict(analysis), f, indent=2)
        except Exception as e:
            logger.debug(f"Cache save failed for {analysis.file_path}: {e}")

    def _should_process_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        if file_path.stat().st_size > self.max_file_size:
            return False, None
        ext = file_path.suffix.lower()
        lang_name = self.extension_to_lang_name.get(ext)
        return lang_name is not None, lang_name

    def _collect_files(
        self, repo_path: Path, exclude_patterns: Set[str] = None
    ) -> List[str]:
        if exclude_patterns is None:
            exclude_patterns = {
                ".git",
                "node_modules",
                "__pycache__",
                "build",
                "dist",
                ".venv",
            }

        files = []
        for root, dirs, filenames in os.walk(repo_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                if self.extension_to_lang_name.get(file_path.suffix.lower()):
                    files.append(str(file_path))
        return files

    def analyze_repository(
        self, repo_path: str, exclude_patterns: Set[str] = None
    ) -> RepositoryAnalysis:
        start_time = time.time()
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        logger.info(f"Starting analysis of repository: {repo_path}")
        files_to_process = self._collect_files(repo_path_obj, exclude_patterns)
        logger.info(f"Found {len(files_to_process)} files to analyze")

        if not files_to_process:
            return RepositoryAnalysis(0, 0, 0, set(), 0.0, [])

        analyses = []
        languages_found = set()

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                # Pass simple, pickle-able types to the static method
                executor.submit(
                    PerformantRepositoryParser._analyze_single_file,
                    file_path,
                    self.extension_to_lang_name,
                    self.cache_dir,
                    self.use_cache,
                    self.max_file_size,
                ): file_path
                for file_path in files_to_process
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    if result:
                        analyses.append(result)
                        languages_found.add(result.language)
                except Exception as e:
                    file_path = future_to_file[future]
                    logger.error(
                        f"A worker process failed for {file_path}: {e}", exc_info=True
                    )

        total_time = time.time() - start_time
        total_functions = sum(len(a.functions) for a in analyses)
        total_imports = sum(len(a.imports) for a in analyses)

        logger.info(f"Analysis completed in {total_time:.2f}s")
        return RepositoryAnalysis(
            len(analyses),
            total_functions,
            total_imports,
            languages_found,
            total_time,
            analyses,
        )

    @staticmethod
    def _analyze_single_file(
        file_path: str,
        extension_to_lang_name: Dict,
        cache_dir: Path,
        use_cache: bool,
        max_file_size: int,
    ) -> Optional[FileAnalysis]:
        path_obj = Path(file_path)

        # File size check
        if path_obj.stat().st_size > max_file_size:
            return None

        # Language check
        lang_name = extension_to_lang_name.get(path_obj.suffix.lower())
        if not lang_name:
            return None

        # --- Caching logic (duplicated from instance methods for static context) ---
        if use_cache:
            stat = path_obj.stat()
            content = f"{path_obj}:{stat.st_mtime}:{stat.st_size}"
            hash_id = hashlib.md5(content.encode()).hexdigest()
            cache_file = cache_dir / f"{hash_id}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return FileAnalysis(**json.load(f))
                except Exception:
                    pass  # Cache invalid, proceed to parse

        # --- Main parsing logic ---
        start_time = time.time()
        try:
            with open(file_path, "rb") as f:
                code_bytes = f.read()
        except IOError as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return None

        # Load language/queries here, inside the worker
        lang_data = _get_language_for_worker(lang_name)
        if lang_data is None:
            return None  # Failed to load language

        parser = Parser()
        parser.set_language(lang_data["parser_lang"])
        tree = parser.parse(code_bytes)

        # Extract definitions
        functions = PerformantRepositoryParser._extract_definitions(
            lang_data["queries"]["functions"], tree.root_node, code_bytes
        )
        imports = PerformantRepositoryParser._extract_definitions(
            lang_data["queries"]["imports"], tree.root_node, code_bytes
        )

        analysis = FileAnalysis(
            file_path=file_path,
            functions=functions,
            imports=imports,
            language=lang_name,
            file_size=len(code_bytes),
            processing_time=time.time() - start_time,
        )

        # Save to cache
        if use_cache:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(analysis), f, indent=2)
            except Exception:
                pass  # Non-critical error

        return analysis

    @staticmethod
    def _extract_definitions(query, root_node, code_bytes) -> List[str]:
        definitions = set()
        captures = query.captures(root_node)
        for node, _ in captures:
            name = code_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="ignore"
            )
            definitions.add(name.strip().strip("\"'"))
        return sorted(list(definitions))
