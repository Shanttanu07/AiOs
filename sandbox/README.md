# AI-OS Sandbox

This sandbox directory provides an isolated filesystem where the AI-OS writes and reads all data. Nothing touches your real home directory outside of this sandbox.

## Directory Structure

- **`in/`** - Drop input files here (CSV, screenshots, plans, etc.). The AI-OS reads from this folder.
- **`out/`** - Generated artifacts appear here (reports, ZIP files, models, etc.). The AI-OS writes outputs here.
- **`tmp/`** - Scratch space for temporary files during execution. Contents may be cleaned up between runs.
- **`logs/`** - Audit and transaction logs. Track all syscalls, capability checks, and execution history.
- **`packages/`** - Packaged apps (.aiox files) and cached dependencies. Portable execution units.

## Usage

1. Place input files in `in/`
2. Run `aiox run <plan>` to execute
3. Find results in `out/`
4. Check `logs/` for execution details