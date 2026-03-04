# Shared Quality Gate for Every Step

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

This gate is **mandatory** for each step file in this plan.

## A. Code completeness checks

- No unfinished code.
- No `TODO`, `FIXME`, ellipsis placeholders, or syntax errors.
- No `pass` in production logic (except valid abstract/interface cases).
- No `NotImplemented` / `NotImplementedError` in non-abstract methods.
- No deviations from project rules or this plan.

## B. Static checks and formatting

Run and fix issues after each completed step:

1. `code_mapper -r /home/vasilyvz/projects/ollama`
2. `black /home/vasilyvz/projects/ollama`
3. `flake8 /home/vasilyvz/projects/ollama`
4. `mypy /home/vasilyvz/projects/ollama`

## C. Validation checks

- Run focused tests related to changed files.
- Confirm no regressions in changed behavior.
- For server startup paths: validation errors must be logged and must stop process startup.
- For client startup/init paths: validation errors must be returned and raised as exceptions.

## D. Step closure criteria

A step is complete only when:

- Step-specific success metrics are green.
- A+B+C checks are all completed and green.
- Step evidence is captured (commands run, key outputs, and startup validation behavior for server/client when applicable).
