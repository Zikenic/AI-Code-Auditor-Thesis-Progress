# Engineering Python Static Code Analysis: AST Parsing, Symbol Extraction, Import Graph Construction, and Cross-File Call Graph Retrieval for Code Review

Static code analysis plays a critical role in modern software engineering, automated code review, and automated architectural introspection. Rather than executing untrusted or incomplete source code, static analysis engines inspect source code semantics at compile or parse time, providing a safe, deterministic, and scalable mechanism for detecting architectural bottlenecks, circular module dependencies, and regression impacts ([Modulegraph2 Development Team, 2025](https://pypi.org/project/modulegraph2/)). 

To conduct effective cross-file code reviews, a static analysis system must move beyond basic regex-based pattern matching. It requires a structured pipeline that parses Python Abstract Syntax Trees (ASTs), extracts scoped symbol metadata, builds inter-module import dependency graphs, and resolves static call target edges across cross-file boundaries. 

This report provides an in-depth analysis of the pipeline required for cross-file static code analysis in Python. It evaluates the AST parsing mechanism, scope tracking, import dependency graph topology, receiver-type inference algorithms, and graph query patterns used to implement static call graph retrieval for automated code reviews.

---

## 1. Concrete Architecture for Static Cross-File Code Analysis

A high-precision static code analysis framework cannot rely on single-pass heuristic analysis. Static call graph generation across multi-file repositories requires a formal, multi-pass architecture that strictly decouples lexical parsing, symbol indexing, dependency mapping, and bottom-up target resolution.

```
+-----------------------------------------------------------------------------------+
|                                 BUILD STAGE (Pass 1)                              |
| Source Files  -->  compile(..., PyCF_ONLY_AST)  -->  AST Nodes (_ast / ASDL)     |
|                                                                                   |
|  * Extract ClassDef, FunctionDef, AsyncFunctionDef, Import, ImportFrom            |
|  * Populate File-Local & Cross-File Symbol Tables (TypeRegistry)                  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                RESOLVE STAGE (Pass 2)                             |
| Scope Chain Traversals  <-->  Import Graph Mapper (DAG & Module Resolution)       |
|                                                                                   |
|  * Resolve Relative / Aliased Imports (ast.ImportFrom)                            |
|  * Infer Receiver Types (self/cls qualifiers, MRO Traversal)                      |
|  * Filter Builtin Noise & Disambiguate Identifiers                                |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 GRAPH STAGE (Pass 3)                              |
| Unified Cross-File Knowledge Graph (Nodes & Edges)                                |
|                                                                                   |
|  * Nodes: Files, Modules, Declarations, External Entities                         |
|  * Edges: CONTAINS, IMPORTS, CALLS (Extracted vs. Inferred Confidence)            |
|  * Retrieval Queries: Recursive CTEs / Path Queries for Automated Code Review    |
+-----------------------------------------------------------------------------------+
```

### Architectural Principles
1. **Multi-Pass Separation:** Parsing and symbol extraction (Pass 1) must be distinct from import linkage and receiver type evaluation (Pass 2). Pass 1 collects local structural facts without assuming that dependencies are resolved. Pass 2 unifies these symbol tables across files to resolve types and call target identifiers.
2. **Deterministic Safety:** Code must never be imported or executed dynamically via standard Python import mechanics (`importlib` or `eval`). AST generation must rely strictly on static parsing engines ([Python Software Foundation, 2026a](https://docs.python.org/3/library/ast.html)).
3. **Explicit Confidence Scoring:** Call graph edges must be tagged with explicit confidence markers. Static analysis produces both *extracted* edges (unambiguous, file-local call targets) and *inferred* edges (cross-file targets resolved via type heuristics or structural name matching).

---

## 2. Python AST Parsing Mechanics and Symbol Extraction

The Python standard library provides built-in facilities for AST parsing via the `ast` module and the core C-level compiler infrastructure.

### Parsing Source Code to AST

To construct an AST safely without compiling source code into executable bytecode, static analyzers invoke Python's standard `compile()` function or `ast.parse()`, specifying the `ast.PyCF_ONLY_AST` compiler flag ([Python Software Foundation, 2026a](https://docs.python.org/3/library/ast.html)):

```python
import ast

def parse_source_to_ast(source_code: str, filename: str = "<unknown>") -> ast.AST:
    return compile(source_code, filename, "exec", flags=ast.PyCF_ONLY_AST)
```

The returned tree consists of instances derived from the CPython parser grammar schema defined in `Parser/Python.asdl` ([Python Software Foundation, 2026b](https://github.com/python/cpython/blob/main/Parser/Python.asdl)). Each abstract grammar symbol (e.g., statements like `stmt`, expressions like `expr`) maps to a class defined in the `_ast` C extension module and re-exported through the `ast` Python module ([Python Software Foundation, 2026a](https://docs.python.org/3/library/ast.html)).

### Symbol Extraction Pipeline

The extraction stage traverses the AST to identify global and local definitions, such as packages, modules, classes, functions, and assignment bindings. During this pass, a specialized AST visitor constructs symbol table records for each file.

```python
class SymbolExtractor(ast.NodeVisitor):
    def __init__(self, module_path: str):
        self.module_path = module_path
        self.scope_stack = [module_path]
        self.symbols = []
        self.imports = []

    def visit_ClassDef(self, node: ast.ClassDef):
        qualified_name = f"{'.'.join(self.scope_stack)}.{node.name}"
        self.symbols.append({
            "type": "class",
            "name": node.name,
            "qualified_name": qualified_name,
            "bases": [ast.unparse(b) for b in node.bases],
            "line": node.lineno
        })
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._extract_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._extract_function(node)

    def _extract_function(self, node):
        qualified_name = f"{'.'.join(self.scope_stack)}.{node.name}"
        args = [arg.arg for arg in node.args.args]
        self.symbols.append({
            "type": "function",
            "name": node.name,
            "qualified_name": qualified_name,
            "args": args,
            "line": node.lineno
        })
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
```

### AST Node Metadata Schema

The table below outlines the core AST nodes evaluated during symbol extraction, along with their derived lexical properties:

| AST Node Class | Abstract Category | Extracted Properties | Analysis Purpose |
| :--- | :--- | :--- | :--- |
| `ast.Module` | Modifiers / Root | Module filename, docstring, top-level exports (`__all__`) | Establishes top-level module namespace boundary. |
| `ast.ClassDef` | Statements (`stmt`) | Class name, bases expressions, decorators, body statements | Defines class scope, object inheritance hierarchy, and method receiver context. |
| `ast.FunctionDef` / `ast.AsyncFunctionDef` | Statements (`stmt`) | Name, position/keyword positional arguments, type annotations, return hint | Identifies executable block boundaries, local lexical variable scopes, and signature constraints. |
| `ast.Import` | Statements (`stmt`) | Module names, optional alias names (`asname`) | Maps direct external module dependencies. |
| `ast.ImportFrom` | Statements (`stmt`) | Target module name, imported symbol names, relative import `level` integer | Resolves explicitly imported symbols, aliased local imports, and relative package paths. |
| `ast.Assign` / `ast.AnnAssign` | Statements (`stmt`) | Variable targets, assigned value expression, type annotation | Tracks variable bindings, local scope updates, and explicit type declarations. |
| `ast.Call` | Expressions (`expr`) | Func identifier/attribute, positional arguments, keyword arguments | Defines call sites, method dispatch targets, and dynamic invocation points. |

---

## 3. Import Graph Construction and Cross-Module Topology

To resolve symbols across multiple files, static engines must build an explicit import dependency graph. An import dependency graph is a directed graph $G = (V, E)$, where $V$ represents individual Python modules or files, and $E$ represents directed import dependencies ($v_i \xrightarrow{\text{imports}} v_j$).

### Import Resolution Semantics

In Python, imports fall into three categories: absolute imports, relative imports, and aliased imports.

1. **Absolute Imports:** Explicitly specify the complete package trajectory (e.g., `import pkg.module_a`).
2. **Relative Imports:** Uses leading dots (represented by the `level` attribute on `ast.ImportFrom`) to traverse upward relative to the declaring file's package path.
   - `level = 1`: Same package directory (`from . import module_b`)
   - `level = 2`: Parent package directory (`from .. import module_c`)
3. **Aliased Imports:** Bind external symbols to local names (`import numpy as np`, `from auth import verify_token as check_auth`).

```python
class ImportResolver(ast.NodeVisitor):
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.import_edges = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.import_edges.append({
                "source": self.current_module,
                "target": alias.name,
                "alias": alias.asname or alias.name,
                "type": "absolute"
            })

    def visit_ImportFrom(self, node: ast.ImportFrom):
        target_base = node.module or ""
        if node.level > 0:
            # Resolve relative import based on current module path depth
            parts = self.current_module.split(".")
            if len(parts) >= node.level:
                base_pkg = ".".join(parts[:-node.level])
                target_base = f"{base_pkg}.{target_base}" if target_base else base_pkg

        for alias in node.names:
            full_imported_symbol = f"{target_base}.{alias.name}" if target_base else alias.name
            self.import_edges.append({
                "source": self.current_module,
                "target": full_imported_symbol,
                "alias": alias.asname or alias.name,
                "type": "relative" if node.level > 0 else "absolute"
            })
```

### Import Graph Analysis and Graph Algorithms

Once the import dependency graph is constructed, static analysis tools apply topological algorithms to analyze system structure ([DependencyGraph Analysis Tools, 2024](https://pypi.org/project/modulegraph2/)):

* **Cycle Detection (Tarjan's Strong Connection Algorithm):** Detects circular import dependencies (`A -> B -> C -> A`), which often cause dynamic import errors or runtime `ImportError` exceptions at startup.
* **PageRank for Structural Importance:** Computes module importance based on incoming import dependencies, identifying core utility modules and central framework abstraction boundaries.
* **Community Detection (Louvain / Infomap):** Clusters tightly coupled modules into logical architectural domain boundaries, highlighting modules that violate clean architecture boundaries during code reviews.

---

## 4. Scope Tracking, Receiver Type Inference, and Static Call Graph Retrieval

Resolving call targets within a single file is simple. In contrast, inter-file method invocation static resolution—such as resolving `self.service.process()` across multiple modules—requires bottom-up receiver type inference and scope resolution.

```
                  +-----------------------------------+
                  |      Call Site: receiver.method()  |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Step 1: Scope Chain Lookup        |
                  | Find local declaration of `receiver` |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Step 2: Type Registry Resolution  |
                  | Identify class type of `receiver`  |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Step 3: Class Hierarchy / MRO     |
                  | Traverse base classes for method  |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Step 4: Qualified Target Resolved |
                  | Edge: FileA -> TargetPkg.Class.method |
                  +-----------------------------------+
```

### Lexical Scope and Variable Binding

To trace variable definitions to their declared types, the analysis engine maintains a hierarchical scope structure during AST traversal. The `Scope` frame tracks variable bindings introduced by parameter lists, assignments, class bindings, and imported aliases:

1. **Identifier Scope Lookup:** When encountering a variable, search upward from local function scopes to class scopes, module scopes, and global built-ins.
2. **`self` and `cls` Qualifier Resolution:** Method definitions automatically introduce a parameter (`self` or `cls`). The type resolver maps `self` inside an instance method directly to the enclosing `ClassDef`.

### Bottom-Up Receiver Type Inference Pipeline

When evaluating a call expression (`ast.Call`), the target expression (`node.func`) is resolved using a four-step bottom-up process:

1. **Identifier and Attribute Parsing:** Distinguish direct function calls (`process()`) from attribute access method calls (`receiver.process()`). Extract the full receiver qualifier chain (`a.b.c`).
2. **Type Propagation via Assignments and Annotations:** Use explicit Python type annotations (`service: PaymentService`) or assignment statements (`service = PaymentService()`) to infer the receiver's type from the cross-file symbol table (`TypeRegistry`).
3. **Inheritance and Method Resolution Order (MRO) Traversal:** If the method is not defined directly on the target class, traverse its parent classes (`ClassDef.bases`) in accordance with Python's C3 Linearization rules to locate inherited method definitions.
4. **Builtin Noise Filtering:** Exclude built-in Python functions (`len`, `print`, `isinstance`) to focus call graph retrieval on user code and application dependencies.

### Graph Taxonomy: Nodes and Edges

The output cross-file analysis database represents software systems as a property graph containing heterogeneous nodes and directed relationship edges.

```
[Module Node: app.services.payment]
       |
       |--- (CONTAINS) ---> [Class Node: PaymentProcessor]
                                   |
                                   |--- (CONTAINS) ---> [Function Node: PaymentProcessor.process]
                                                                |
                                                                |--- (CALLS: inferred) ---> [Function Node: StripeClient.charge]
```

| Graph Element Category | Element Type | Description | Key Attributes |
| :--- | :--- | :--- | :--- |
| **Node** | `File` | A physical `.py` source file on disk. | `path`, `checksum`, `lines_of_code` |
| **Node** | `Module` | Logical Python module derived from file or package path. | `qualified_name`, `is_package` |
| **Node** | `Declaration` | Code entities (classes, functions, async functions, methods). | `qualified_name`, `signature`, `line_start`, `line_end` |
| **Node** | `ExternalTarget` | Unresolved external library dependencies (e.g., standard library, `pip` packages). | `name`, `module_origin` |
| **Edge** | `CONTAINS` | Parent-child structural containment hierarchy. | `parent_id`, `child_id` |
| **Edge** | `IMPORTS` | Inter-module dependency relationship. | `source_module`, `target_module`, `imported_symbol`, `alias` |
| **Edge** | `CALLS` | Functional call invocation relationship between call site and target declaration. | `caller_qualified_name`, `target_qualified_name`, `confidence` (`extracted` \| `inferred`), `line_number` |

---

## 5. End-to-End Implementation: AST Symbol Extractor and Static Call Resolver

The following self-contained Python program demonstrates AST parsing, symbol extraction, import mapping, receiver type inference, and static call graph extraction across multiple inline module representations.

```python
import ast

# Module Source Code Samples representing a multi-file Python system
MODULE_AUTH = """
class User:
    def __init__(self, username: str):
        self.username = username

class Authenticator:
    def authenticate(self, user: User) -> bool:
        return self._validate_credentials(user.username)

    def _validate_credentials(self, username: str) -> bool:
        return len(username) > 3
"""

MODULE_SERVICE = """
from auth import Authenticator, User

class UserService:
    def __init__(self):
        self.auth = Authenticator()

    def register_user(self, name: str):
        user = User(name)
        if self.auth.authenticate(user):
            self.send_welcome_email(user)

    def send_welcome_email(self, user: User):
        print("Welcome email sent to " + user.username)
"""

class CodebaseAnalyzer:
    def __init__(self):
        self.modules = {}
        self.symbol_table = {}  # qualified_name -> info
        self.type_registry = {} #