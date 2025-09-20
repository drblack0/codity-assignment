import logging
import json
import argparse
from dataclasses import asdict
from repo_parser import PerformantRepositoryParser
from config import logger


def main():
    parser = argparse.ArgumentParser(
        description="Analyze repository for functions and imports"
    )
    parser.add_argument("repo_path", help="Path to the repository to analyze")
    parser.add_argument("--output", "-o", help="Output file for results (JSON format)")
    parser.add_argument(
        "--max-workers", "-w", type=int, help="Maximum number of worker processes"
    )
    parser.add_argument(
        "--max-file-size",
        "-s",
        type=int,
        default=10 * 1024 * 1024,
        help="Maximum file size to process in bytes (default: 10MB)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--summary-only", action="store_true", help="Show only summary statistics"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize parser
    analyzer = PerformantRepositoryParser(
        max_workers=args.max_workers,
        max_file_size=args.max_file_size,
        use_cache=not args.no_cache,
    )

    try:
        # Analyze repository
        result = analyzer.analyze_repository(args.repo_path)

        # Display results
        print(f"\n{'=' * 60}")
        print("REPOSITORY ANALYSIS SUMMARY")
        print(f"{'=' * 60}")
        print(f"Repository: {args.repo_path}")
        print(f"Total files processed: {result.total_files}")
        print(f"Total functions found: {result.total_functions}")
        print(f"Total imports found: {result.total_imports}")
        print(
            f"Languages detected: {', '.join(sorted(result.languages_found)) if result.languages_found else 'None'}"
        )
        print(f"Processing time: {result.processing_time:.2f} seconds")
        if result.total_files > 0:
            print(
                f"Average time per file: {result.processing_time / result.total_files:.4f} seconds"
            )

        if not args.summary_only and result.files:
            print(f"\n{'=' * 60}")
            print("DETAILED RESULTS BY FILE")
            print(f"{'=' * 60}")

            # Group by language
            by_language = {}
            for file_analysis in result.files:
                lang = file_analysis.language
                if lang not in by_language:
                    by_language[lang] = []
                by_language[lang].append(file_analysis)

            for language in sorted(by_language.keys()):
                files = by_language[language]
                print(f"\n--- {language.upper()} FILES ---")

                for file_analysis in sorted(files, key=lambda x: x.file_path):
                    print(f"\nFile: {file_analysis.file_path}")
                    print(f"  Size: {file_analysis.file_size:,} bytes")
                    print(f"  Processing time: {file_analysis.processing_time:.4f}s")
                    if file_analysis.functions:
                        print(
                            f"  Functions ({len(file_analysis.functions)}): {', '.join(file_analysis.functions[:5])}{'...' if len(file_analysis.functions) > 5 else ''}"
                        )
                    if file_analysis.imports:
                        print(
                            f"  Imports ({len(file_analysis.imports)}): {', '.join(file_analysis.imports[:5])}{'...' if len(file_analysis.imports) > 5 else ''}"
                        )

        # Save to file if requested
        if args.output:
            output_data = {
                "summary": {
                    "repository": args.repo_path,
                    "total_files": result.total_files,
                    "total_functions": result.total_functions,
                    "total_imports": result.total_imports,
                    "languages_found": sorted(list(result.languages_found)),
                    "processing_time": result.processing_time,
                },
                "files": [asdict(f) for f in result.files],
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\nDetailed results saved to: {args.output}")

    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
