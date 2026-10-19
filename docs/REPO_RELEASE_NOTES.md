# Packaging changes compared with supplied uploads

This release uses your uploaded teaching scripts as the starting point. Their tool workflows and pauses are retained.

1. Renamed duplicate-suffixed uploads (such as `(8).py`) to the canonical import and run names used in the code.
2. Renamed `inventory(1).csv` to `inventory.csv`; retained original invalid price `P003=X` for the lab exercise.
3. Packaged the editable PowerPoint provided earlier in the conversation.
4. Excluded uploaded `.env` and added `.env.example`, `.gitignore`, and secret-handling instructions.
5. Removed duplicate-ID skipping from `common.load_inventory()` to align the shared loader with the `read_product` row-number workflow (duplicate IDs are allowed).
6. Updated the normal-LLM inventory script to describe and expect the *actual* count of valid records, rather than exactly 15, since the supplied CSV includes an intentional invalid row.
7. Added optional `--trace YES/NO` to the rule-based math script to permit noninteractive testing; interactive pauses still default to YES.
8. Added offline smoke tests and a GitHub README/guide. No API prompts, function registries, or Graph/Harness retry policies were redesigned.

**Test scope:** Python syntax compilation; offline smoke tests and no-key rule-based demos. Remote Groq behavior requires valid participant keys and is not verified in the packaging environment.
