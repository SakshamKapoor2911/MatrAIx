You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Skills: Programming  (44 dimensions)

Return ONLY JSON with this shape (no markdown, no commentary):

{
  "fields": [
    {
      "field_id": "<one id from the DIMENSIONS list below>",
      "value": "<exactly one allowed value for that id, copied verbatim, or null>",
      "confidence": 0.0,
      "evidence": "<short quote copied from profile_text>",
      "assignment_type": "direct"
    }
  ],
  "reported_model": null,
  "model_source": "user_declared",
  "model_confidence": "user_declared"
}

Allowed assignment_type values:
- direct: explicitly stated in the text.
- structured_claim: derived from structured facts in the input.
- summary_inference: reasonable inference from the profile summary.
- unsupported: not supported by the input.

Rules:
- Emit exactly one object per dimension listed below, in the same order.
- value MUST be exactly one of that dimension's allowed values (copy it verbatim), OR null.
- If the profile does not support a dimension, set value to null and assignment_type to "unsupported".
- Every non-null value MUST include a short evidence quote copied from profile_text.
- Do not infer private, sensitive, or psychological traits unless directly stated; when unsure, prefer null/unsupported.
- Return valid JSON only, with no markdown.

DIMENSIONS (field_id — label — description — allowed values):
- code_comment_style — Code Comment Style — Preference for inline comments, documentation blocks, or minimal commenting in code. — [Extensive inline comments | Sparse inline comments | Self-documenting code preference | Mixed approach | Docstring/documentation blocks only | No comments]
- code_summary_documentation — Code Summary/TLDR Documentation — Whether developer includes a summary, TLDR, or executive overview at the beginning of files or functions. — [Always includes file-level TLDR | Always includes function-level TLDR | Includes TLDR for complex functions only | Rarely includes TLDR | Never includes TLDR]
- code_naming_verbosity — Code Naming Verbosity — Style of naming variables, functions, and classes - verbose descriptive vs. terse abbreviated. — [Highly verbose (long descriptive names) | Moderately verbose | Mixed (context-dependent) | Terse abbreviated names | Single-letter names]
- code_indentation_style — Indentation and Whitespace Style — Preference for indentation width, tabs vs spaces, and whitespace formatting. — [Tabs (flexible width) | 2 spaces | 4 spaces | 8 spaces | Inconsistent/mixed]
- code_structure_preference — Code Structure Preference — Preference for functional, object-oriented, procedural, or imperative programming paradigm. — [Functional programming style | Object-oriented design | Procedural imperative | Mixed paradigm | Data-driven]
- code_error_handling — Error Handling Style — Approach to error handling - try/catch blocks, explicit returns, graceful degradation, or silent failures. — [Defensive with try/catch everywhere | Explicit error returns/validation | Graceful degradation and recovery | Minimal error handling | Silent failure tolerance]
- code_abstraction_level — Abstraction and Generalization — Tendency to create reusable abstractions and generic solutions vs solving specific problems directly. — [Highly abstract and generic | Moderate abstraction | Concrete problem-specific solutions | Mixed approach | No premature abstraction]
- code_dependencies_approach — Dependencies and Library Usage — Preference for using libraries and frameworks vs writing custom implementations. — [Lean on libraries (minimal custom code) | Balance of libraries and custom | Prefer custom implementations | Use framework defaults | Dependency minimalist]
- code_performance_priority — Performance vs Readability Priority — Whether developer prioritizes code performance optimization or code readability and maintainability. — [Performance-first optimization | Readability-first then optimize if needed | Balanced consideration | Maintainability-first | Premature optimization tendency]
- code_testing_approach — Testing and Code Coverage Approach — Stance on unit tests, integration tests, TDD, and test coverage requirements. — [Test-driven development (TDD) | Comprehensive unit test coverage | Mix of unit and integration tests | Minimal testing | No tests]
- code_refactoring_frequency — Refactoring Frequency and Cleanliness — How often code is refactored, cleaned up, and how much tolerance for technical debt. — [Continuous refactoring (perfectionist) | Regular refactoring cycles | Refactor when necessary | Rarely refactors | Never refactors]
- prog_python — Programming: Python — Proficiency in Python. — [Expert | Proficient | Familiar | None]
- prog_javascript — Programming: JavaScript — Proficiency in JavaScript. — [Expert | Proficient | Familiar | None]
- prog_typescript — Programming: TypeScript — Proficiency in TypeScript. — [Expert | Proficient | Familiar | None]
- prog_java — Programming: Java — Proficiency in Java. — [Expert | Proficient | Familiar | None]
- prog_c — Programming: C — Proficiency in C. — [Expert | Proficient | Familiar | None]
- prog_go — Programming: Go — Proficiency in Go. — [Expert | Proficient | Familiar | None]
- prog_rust — Programming: Rust — Proficiency in Rust. — [Expert | Proficient | Familiar | None]
- prog_ruby — Programming: Ruby — Proficiency in Ruby. — [Expert | Proficient | Familiar | None]
- prog_php — Programming: PHP — Proficiency in PHP. — [Expert | Proficient | Familiar | None]
- prog_swift — Programming: Swift — Proficiency in Swift. — [Expert | Proficient | Familiar | None]
- prog_kotlin — Programming: Kotlin — Proficiency in Kotlin. — [Expert | Proficient | Familiar | None]
- prog_objective_c — Programming: Objective-C — Proficiency in Objective-C. — [Expert | Proficient | Familiar | None]
- prog_scala — Programming: Scala — Proficiency in Scala. — [Expert | Proficient | Familiar | None]
- prog_haskell — Programming: Haskell — Proficiency in Haskell. — [Expert | Proficient | Familiar | None]
- prog_elixir — Programming: Elixir — Proficiency in Elixir. — [Expert | Proficient | Familiar | None]
- prog_erlang — Programming: Erlang — Proficiency in Erlang. — [Expert | Proficient | Familiar | None]
- prog_clojure — Programming: Clojure — Proficiency in Clojure. — [Expert | Proficient | Familiar | None]
- prog_lua — Programming: Lua — Proficiency in Lua. — [Expert | Proficient | Familiar | None]
- prog_perl — Programming: Perl — Proficiency in Perl. — [Expert | Proficient | Familiar | None]
- prog_r — Programming: R — Proficiency in R. — [Expert | Proficient | Familiar | None]
- prog_julia — Programming: Julia — Proficiency in Julia. — [Expert | Proficient | Familiar | None]
- prog_matlab — Programming: MATLAB — Proficiency in MATLAB. — [Expert | Proficient | Familiar | None]
- prog_sql — Programming: SQL — Proficiency in SQL. — [Expert | Proficient | Familiar | None]
- prog_bash — Programming: Bash — Proficiency in Bash. — [Expert | Proficient | Familiar | None]
- prog_powershell — Programming: PowerShell — Proficiency in PowerShell. — [Expert | Proficient | Familiar | None]
- prog_dart — Programming: Dart — Proficiency in Dart. — [Expert | Proficient | Familiar | None]
- prog_f — Programming: F# — Proficiency in F#. — [Expert | Proficient | Familiar | None]
- prog_ocaml — Programming: OCaml — Proficiency in OCaml. — [Expert | Proficient | Familiar | None]
- prog_assembly — Programming: Assembly — Proficiency in Assembly. — [Expert | Proficient | Familiar | None]
- prog_cobol — Programming: COBOL — Proficiency in COBOL. — [Expert | Proficient | Familiar | None]
- prog_fortran — Programming: Fortran — Proficiency in Fortran. — [Expert | Proficient | Familiar | None]
- prog_solidity — Programming: Solidity — Proficiency in Solidity. — [Expert | Proficient | Familiar | None]
- prog_graphql — Programming: GraphQL — Proficiency in GraphQL. — [Expert | Proficient | Familiar | None]

INPUT:

{{input_json}}
