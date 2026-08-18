#!/usr/bin/env python3
"""Restore permissions omitted by Upptime's generated workflows.

The repository's enterprise policy gives GITHUB_TOKEN read-only permissions by
default. Upptime regenerates its workflow files without explicit permissions,
so its checks cannot commit results or manage incident issues unless these
blocks are restored after each template update.
"""

from pathlib import Path

WORKFLOW_PERMISSIONS = {
    "graphs.yml": ("contents",),
    "response-time.yml": ("contents",),
    "setup.yml": ("actions", "contents", "issues"),
    "site.yml": ("contents",),
    "summary.yml": ("contents",),
    "update-template.yml": ("contents", "issues"),
    "updates.yml": ("contents",),
    "uptime.yml": ("contents", "issues"),
}

workflows_dir = Path(__file__).resolve().parents[1] / ".github" / "workflows"
restore_step = """      - name: Restore required workflow permissions
        run: |
          python3 scripts/patch-upptime-workflow-permissions.py
          if ! git diff --quiet -- .github/workflows; then
            git config user.name \"Upptime Bot\"
            git config user.email \"73812536+upptime-bot@users.noreply.github.com\"
            git add .github/workflows
            git commit -m \":wrench: Preserve workflow permissions [skip ci]\"
            git push
          fi
"""

for filename, permissions in WORKFLOW_PERMISSIONS.items():
    path = workflows_dir / filename
    original_text = path.read_text()
    text = original_text
    on_marker = "\non:\n"
    on_index = text.find(on_marker)

    if on_index == -1:
        raise RuntimeError(f"Could not find top-level 'on' key in {path}")

    # Respect an upstream permission block if Upptime adds one in the future.
    permissions_index = text.find("\npermissions:\n", 0, on_index)
    if permissions_index == -1:
        permission_block = "\npermissions:\n" + "".join(
            f"  {permission}: write\n" for permission in permissions
        ).rstrip("\n")
        text = text[:on_index] + permission_block + text[on_index:]

    # These two workflows regenerate Upptime's workflow files. Preserve this
    # repair step so every later template regeneration remains self-healing.
    if (
        filename in {"setup.yml", "update-template.yml"}
        and "      - name: Restore required workflow permissions\n" not in text
    ):
        text = text.rstrip() + "\n" + restore_step

    if text != original_text:
        path.write_text(text)
