# Multi-Language Code Repository Analyzer

A high-performance, language-agnostic command-line tool to parse entire code repositories, efficiently extracting defined functions, classes, and import dependencies. It is built for speed and scalability, leveraging multiprocessing and intelligent caching.

## Key Features

-   **Multilingual Support:** Out-of-the-box support for popular languages including Python, JavaScript, TypeScript, Java, and Go.
-   **High Performance:** Uses `concurrent.futures.ProcessPoolExecutor` to analyze files in parallel, taking full advantage of multi-core CPUs.
-   **Scalable:** Designed to handle large repositories by skipping gigantic files and ignoring irrelevant directories (like `node_modules`).
-   **Intelligent Caching:** Automatically caches analysis results. Subsequent runs on unchanged files are instantaneous, making it extremely fast for repeated analysis.
-   **Flexible Output:** View a summary and detailed breakdown in the console, or export the full analysis to a structured JSON file for programmatic use.
-   **Easily Extensible:** Adding support for a new language is as simple as defining its file extensions and `tree-sitter` queries in the configuration.

## How It Works

The tool recursively scans a target directory for source code files. For each supported file, it uses the powerful **[tree-sitter](https://tree-sitter.github.io/tree-sitter/)** parsing library to build an Abstract Syntax Tree (AST). It then runs optimized queries against this tree to extract:
1.  **Defined Symbols:** Functions, classes, methods, and other relevant structures defined within the file.
2.  **Import Dependencies:** The source modules or packages the file imports.

This entire process is distributed across a pool of worker processes to ensure maximum speed.

## Installation

### Prerequisites

-   Python 3.7+
-   `pip` and `venv` (recommended)

### Setup

1.  **Clone the repository (or download the script):**
    ```bash
    git clone https://github.com/drblack0/codity-assignment/ 
    cd https://github.com/drblack0/codity-assignment/ 
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The script is run from the command line, pointing it at the repository you wish to analyze.

```bash
python main.py <repo_path> [options]
```

### Arguments and Options

| Argument          | Short | Description                                                                   | Default                     |
| ----------------- | ----- | ----------------------------------------------------------------------------- | --------------------------- |
| `repo_path`       |       | **(Required)** The file path to the repository directory to analyze.          |                             |
| `--output`        | `-o`  | Save the detailed analysis results to a JSON file.                            | (Prints to console)         |
| `--max-workers`   | `-w`  | Set the maximum number of parallel processes to use.                          | (System CPU count + 4)      |
| `--max-file-size` | `-s`  | The maximum file size in bytes to process. Skips files larger than this.      | `10485760` (10 MB)          |
| `--no-cache`      |       | Disable the caching system and force re-analysis of all files.                | (Cache is enabled)          |
| `--summary-only`  |       | Display only the final summary statistics, hiding the detailed file-by-file breakdown. | (Shows details)             |
| `--verbose`       | `-v`  | Enable debug-level logging for more detailed output.                          | (Info-level logging)        |

### Examples

**1. Basic analysis of a project:**
```bash
python main.py C:\Users\karti\projects\my-cool-project
```

**2. Analyze a project and save the full results to a JSON file:**
```bash
python main.py /path/to/my/project -o analysis.json
```

**3. Run a quick analysis and only view the summary:**
```bash
python main.py /path/to/my/project --summary-only
```

**4. Analyze a very large repository with more worker processes:**
```bash
python main.py /path/to/large/repo -w 8
```

## JSON Output Format

When using the `--output` option, the tool generates a JSON file with the following structure:

```json
{
  "summary": {
    "repository": "/path/to/my/project",
    "total_files": 150,
    "total_functions": 875,
    "total_imports": 1021,
    "languages_found": ["python", "typescript", "go"],
    "processing_time": 5.78
  },
  "files": [
    {
      "file_path": "/path/to/my/project/src/api/user.ts",
      "functions": [
        "User",
        "UserService",
        "createUser",
        "getUsers"
      ],
      "imports": [
        "express",
        "../models/database.js"
      ],
      "language": "typescript",
      "file_size": 1823,
      "processing_time": 0.021
    }
    // ... more file analysis objects
  ]
}
```

## Extending with a New Language

Adding support for another language is straightforward:

1.  Open the `config.py` script and locate the `LANGUAGE_CONFIGS` dictionary.
2.  Add a new entry for your language (e.g., `"ruby"`).
3.  Fill in the required keys:
    -   `extensions`: A list of file extensions (e.g., `[".rb"]`).
    -   `language_name`: The name used by `tree-sitter-languages` (e.g., `"ruby"`).
    -   `queries`: A dictionary containing two keys:
        -   `imports`: A `tree-sitter` query string to capture import/require statements.
        -   `functions`: A `tree-sitter` query string to capture function, class, or method definitions.
4.  That's it! The tool will automatically pick up the new configuration.

*Note: Writing tree-sitter queries requires some knowledge of the target language's Abstract Syntax Tree. You can use a tool like the [tree-sitter playground](https://tree-sitter.github.io/tree-sitter/playground) to explore a language's AST and test your queries.*
