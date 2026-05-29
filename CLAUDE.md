# Code Style & Design Guide

Match these conventions when writing or modifying code.

## Philosophy

- **Functional core.** Prefer pure functions that take explicit inputs and return new
  objects. Avoid hidden state and side effects. When a function mutates, make that a
  deliberate, opt-in `inplace: bool` choice — never the default.
- **Make illegal states unrepresentable.** Validate types and invariants at construction
  / entry, raise immediately with a clear message, and let the rest of the code trust the
  data.
- **Names tell the story.** Long, descriptive names are preferred over comments. e.g.
  `argument_test_value`, `number_of_columns_with_just_amplitudes_and_phases`,
  `high_resolution_limit`. A reader should not have to guess what a variable holds.
- **Compose small pieces.** Break work into small, single-purpose functions. Use local
  closures when they make a block more readable (e.g. an objective function passed to an
  optimizer).

## Typing (strict)

- `from __future__ import annotations` is the first import in every module.
- Everything is fully type-annotated. mypy runs strict:
  `disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_untyped_calls`. New code
  must type-check with no `# type: ignore` unless a third-party stub genuinely forces it
  (annotate the specific error code, e.g. `# type: ignore[no-untyped-call]`).
- Use `@overload` to give precise signatures to functions whose return type depends on a
  flag or input type (e.g. `inplace: Literal[True] -> None` vs
  `Literal[False] -> Object`; `full_output` variants).
- Use `TypeAlias` for recurring union types (`CellType: TypeAlias = ... | ... | ...`).
- Use `Final` for true module-level constants, `ClassVar` for class-level constants,
  `Literal` for closed string/flag sets.

## Function signatures

- **Keyword-only by default.** Put `*` early so that anything optional — and *all*
  booleans — must be passed by name: `def f(x, *, inplace: bool = False)`. Positional
  bools are banned outside of tests.
- Give sensible defaults; surface tunable defaults as named constants (see Settings).
- Return new objects rather than mutating arguments, unless `inplace=True` is explicitly
  requested.

## Errors

- Define custom exception subclasses with descriptive names ending in `Error`, bodies
  elided: `class ShapeMismatchError(Exception): ...`. Subclass the most specific built-in
  that fits (`ValueError`, `RuntimeError`, `AttributeError`, …).
- Build the message in a local `msg` variable, then raise — never inline the string in
  the `raise` (ruff EM rule):
  ```python
  msg = f"inputs not same shape: {a.shape} vs {b.shape}"
  raise ShapeMismatchError(msg)
  ```
- For multi-line messages, append with `msg += ...` across lines.
- Validate inputs early and raise with context (include the offending value/type).

## Constants & settings

- **No magic values.** Extract numeric/string literals into named, type-annotated
  module-level constants. Centralize tunable runtime parameters in a single `settings.py`
  module, grouped by topic with short comments explaining units and intent.
  ```python
  MAP_SAMPLING: int = 3
  TV_MAX_WEIGHT_EXPECTED = 0.1  # threshold for a warning to the user
  ```
- Reference these constants as defaults in function signatures rather than re-typing the
  literal.

## Data models

- Use **pydantic `BaseModel`** for structured/serializable data (metadata, results,
  config). Keep them small and use inheritance to share fields. Serialize with
  `model_dump_json(...)`.
- Use **`@dataclass`** for lightweight internal bundles of related objects, and attach
  small behavior methods where it reads naturally.
- Use **`Enum`** for things that can be discretely enumerated.
- Use **`StrEnum` with `auto()`** for closed sets of mode/choice strings; pass the enum
  type directly to argparse `type=` and `choices=list(Enum)`.

## Logging

- Logging should occur at leaf-level, not burried deep in the code base.
- Use `log.warning(...)` for suspicious-but-recoverable conditions (e.g. a parameter
  landing outside its expected range), and keep a named constant for the threshold.

## Numerics

- Cast numpy scalars to Python types (`float(...)`) before storing them in models or
  returning them, so downstream types are clean.
- Pass `strict=...` explicitly to `zip`.
- Seed RNGs (`np.random.default_rng(seed=...)`) anywhere determinism matters.

## Docstrings & comments

- numpy docstring convention. Module docstrings are short, lowercase one-liners
  (`"""total variation denoising of maps"""`).
- Public functions/classes get full docstrings: a summary, then `Parameters`, `Returns`,
  `Raises`, and `Notes`/`Example`/`References` where useful. Docstrings on internal
  helpers, dunders, and obvious code are optional (these rules are ignored in lint).
- Comments explain *why*, not *what*. It's fine — encouraged — to leave honest comments
  about known warts, with an author/date tag: `# this feels dangerous ... - @tjlane`.
- Regression tests carry a comment stating the bug they pin.
- Good code is self-documenting. Minimize comments. Either re-write the code so that 
  it is clean and does not require comment, or build the comments into the variable names and code structure whenever possible.

## Tests

- Test functions are fully type-annotated and return `None`.
- Use fixtures (often `scope="session"` for shared inputs) defined in `conftest.py`;
  use `@pytest.mark.parametrize` to cover variants, including edge inputs.
- Write a `_smoke` test that just exercises the happy path and checks types, plus targeted
  tests for behavior, scale/conservation, NaN handling, and regressions.
- Assert numerics with `np.testing.assert_allclose(..., rtol=...)` / `np.isclose`, not
  `==`. In tests, asserts, magic numbers, and positional bools are allowed.

## Linting / formatting

- ruff with `select = ["ALL"]` and a curated `ignore` list; line length 100.
- Prefer fixing the code over adding a `# noqa`. When a `# noqa` is unavoidable, scope it
  to the specific rule and add a short reason (e.g. `# noqa: N802, caps from <library>`).
- Keep imports grouped stdlib / third-party / local; use explicit relative imports
  (`from .settings import ...`) within a package.

## Paths and IO

- **Use `pathlib.Path`** for paths, not strings.
- Minimize reading and writing to disk and file I/O, it is brittle and slow.
