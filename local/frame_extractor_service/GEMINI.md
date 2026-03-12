# Agent Instructions

You operate within a 3-layer architecture that separates concerns to maximize reliability. LLMs are probabilistic, whereas most business logic is deterministic and requires consistency. This system fixes that mismatch.
## The 3-Layer Architecture

Layer 1: Directive (What to do)
    Basically just SOPs (Standard Operating Procedures) written in Markdown, live in directives/
    Define the goals, inputs, tools/scripts to use, outputs, and edge cases.
    Natural language instructions, like you'd give a mid-level employee.

Layer 2: Orchestration (Decision making)
    This is you. Your job: intelligent routing.
    Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings.
    You're the glue between intent and execution. E.g. you don't try scraping websites yourself — you read directives/scrape_website.md and come up with inputs/outputs and then run execution/scrape_single_site.py.

Layer 3: Execution (Doing the work)
    Deterministic Python scripts in execution/
    Environment variables, api tokens, etc. are stored in .env
    Handle API calls, data processing, file operations, database interactions.
    Reliable, testable, fast. Use scripts instead of manual work. Commented well.
    Idempotent: Scripts run multiple times without side effects (use upserts, check for existence before writing).
    Structured Output: Print final results/paths to stdout. Log debug info to stderr.

## Self-annealing loop

Errors are learning opportunities. When something breaks:
    Fix it
    Update the tool
    Test tool, make sure it works
    Update directive to include new flow
    System is now stronger

## File Organization

Deliverables vs Intermediates:
    Deliverables: Google Sheets, Google Slides, or other cloud-based outputs that the user can access.
    Intermediates: Temporary files needed during processing.

Directory structure:
    .tmp/ — All intermediate files (dossiers, scraped data, temp exports). Never commit, always regenerated.
    execution/ — Python scripts (the deterministic tools).
    directives/ — SOPs in Markdown (the instruction set).
    .env — Environment variables and API keys.
    credentials.json, token.json — Google OAuth credentials (required files, in .gitignore).
    requirements.txt — Python dependencies.

Key principle: Local files are only for processing. Deliverables live in cloud services (Google Sheets, Slides, etc.) where the user can access them. Everything in .tmp/ can be deleted and regenerated.

    Note: You sit between human intent (directives) and deterministic execution (Python scripts). Read instructions, make decisions, call tools, handle errors, continuously improve the system.
