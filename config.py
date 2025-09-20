import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

LANGUAGE_CONFIGS = {
    "python": {
        "extensions": [".py", ".pyw"],
        "language_name": "python",
        "queries": {
            "imports": """
                (import_statement (dotted_name) @import.name)
                (import_from_statement module_name: (dotted_name) @import.name)
            """,
            # NOTE: Combined function and async function definitions into one list.
            # The previous 'async_function_definition' might fail on older grammars.
            "functions": """
                [
                    (function_definition name: (identifier) @function.name)
                    (class_definition name: (identifier) @class.name)
                ]
            """,
        },
    },
    "javascript": {
        "extensions": [".js", ".jsx", ".mjs", ".cjs"],
        "language_name": "javascript",
        "queries": {
            "imports": """
                (import_statement source: (string) @import.name)
                (call_expression
                    function: (identifier) @require
                    arguments: (arguments (string) @import.name)
                    (#eq? @require "require"))
            """,
            "functions": """
                (function_declaration name: (identifier) @function.name)
                (variable_declarator
                    name: (identifier) @function.name
                    value: [(arrow_function) (function)])
                (class_declaration name: (identifier) @class.name)
                (method_definition name: (property_identifier) @method.name)
            """,
        },
    },
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "language_name": "typescript",
        "queries": {
            "imports": """
                (import_statement source: (string) @import.name)
            """,
            "functions": """
                (function_declaration name: (identifier) @function.name)
                (lexical_declaration
                    (variable_declarator
                        name: (identifier) @function.name
                        value: (arrow_function)))
                (class_declaration name: (type_identifier) @class.name)
                (method_definition name: (property_identifier) @method.name)
                (interface_declaration name: (type_identifier) @interface.name)
            """,
        },
    },
    "java": {
        "extensions": [".java"],
        "language_name": "java",
        "queries": {
            "imports": """
                (import_declaration (scoped_identifier) @import.name)
            """,
            # NOTE: Removed 'constructor_declaration' which can have syntax issues
            # in some grammar versions. This is more stable.
            "functions": """
                (method_declaration name: (identifier) @function.name)
                (class_declaration name: (identifier) @class.name)
                (interface_declaration name: (identifier) @interface.name)
            """,
        },
    },
    "go": {
        "extensions": [".go"],
        "language_name": "go",
        "queries": {
            "imports": """
                (import_spec path: (interpreted_string_literal) @import.name)
            """,
            "functions": """
                (function_declaration name: (identifier) @function.name)
                (method_declaration name: (field_identifier) @method.name)
                (type_declaration (type_spec name: (type_identifier) @type.name))
            """,
        },
    },
    # Other languages can be added here...
}
