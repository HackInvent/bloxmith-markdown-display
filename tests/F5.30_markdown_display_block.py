#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies Markdown display block behavior.
# File Name: F5.30_markdown_display_block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-06-22
# -----------------------------------------------------------------------------

"""F5.30 - Markdown display block.

The test connects a text source containing Markdown to `markdown_display` and
checks that the block preserves raw Markdown while rendering a safe HTML subset
in its block-owned modal.
"""

# Test cases:
# - FB1 - Render inspector with captured Markdown source.
# - FB2 - Render modal with escaped/safe Markdown output and block-owned CSS.
# - FB1/FB3 - Run text -> markdown_display in centralized and zeromq_active modes.

from ui_smoke_common import (
    create_run_api,
    data_edge,
    expect,
    graph_payload,
    http_json,
    isolated_server,
    text_node,
    wait_for_run_terminal,
)
from urllib.parse import quote
from block_test_packages import install_test_package, release_key, surface_payload


def markdown_display_node() -> dict:
    return {
        "id": "markdown-display-1",
        "kind": "markdown_display",
        "title": "Visualiser md",
        "position": {"x": 420, "y": 120},
        "inputs": [
            {
                "id": 1,
                "name": "md",
                "title": "Markdown",
                "accepts": ["text/markdown", "text/plain", "message/*"],
                "multiplicity": "many",
                "execution_requirement": "required_for_execution",
                "required": False,
            }
        ],
        "outputs": [],
        "config": {},
    }


def main() -> None:
    markdown = "# Rapport\n\n- Point **important**\n- `code`\n\n<script>alert('x')</script>\n" + ("\nTexte long." * 80)
    with isolated_server() as server:
        # Surfaces are release assets: a bundled kind serves none of them.
        model = install_test_package(server, "markdown_display")
        key = quote(release_key(model), safe="")
        served = lambda payload, suffix: next(
            asset["path"] for asset in payload["assets"] if asset["path"].endswith(suffix))
        catalog = http_json(server.base_url, "/api/blocks")
        kinds = {block.get("kind") for block in catalog.get("blocks", [])}
        expect("markdown_display" in kinds, "markdown_display must be discovered in the block catalog.")

        rendered = http_json(
            server.base_url,
            "/api/blocks/markdown_display/inspector-panel",
            method="POST",
            payload={
                "node": {"id": "markdown-display-1", "kind": "markdown_display", "title": "Visualiser md"},
                "runtime": {
                    "received_inputs": [
                        {"label": "Text.out", "target_label": "Visualiser md.md", "content": markdown}
                    ],
                    "latest_message": markdown,
                },
            },
        )
        inspector = str(rendered.get("html") or "")
        expect("Text.out" in inspector and "Rapport" in inspector, "Inspector must render source and captured Markdown.")
        expect("<script>" not in inspector and "&lt;script&gt;" in inspector, "Inspector must escape raw HTML.")

        modal = http_json(
            server.base_url,
            "/api/blocks/markdown_display/modal",
            method="POST",
            payload={
                "node": {"id": "markdown-display-1", "kind": "markdown_display", "title": "Visualiser md"},
                "runtime": {
                    "received_inputs": [
                        {"label": "Text.out", "target_label": "Visualiser md.md", "content": markdown}
                    ],
                    "latest_message": markdown,
                },
            },
        )
        modal_html = str(modal.get("html") or "")
        modal_assets = {(asset.get("kind"), asset.get("path")) for asset in modal.get("assets", [])}
        expect('<h1>Rapport</h1>' in modal_html, "Modal must render Markdown headings.")
        expect("<strong>important</strong>" in modal_html, "Modal must render inline emphasis.")
        expect("<script>" not in modal_html and "&lt;script&gt;" in modal_html, "Modal must escape raw HTML.")
        expect('data-block-runtime-refresh="autonomous"' in modal_html, "Modal must opt into autonomous runtime refresh.")
        expect("data-block-apply" in modal_html, "Modal must expose generic Apply for title edits.")

        document = graph_payload(
            "F5 Markdown Display",
            [
                text_node("text-1", "Markdown source", markdown, 80, 120),
                markdown_display_node(),
            ],
            [data_edge("edge-text-markdown-display", "text-1", 1, "markdown-display-1", 1)],
        )
        for runtime_mode in ("centralized", "zeromq_active"):
            created = create_run_api(server, document, runtime_mode=runtime_mode)
            run = wait_for_run_terminal(server, str(created.get("run_id") or ""))

            expect(run.get("status") == "success", f"markdown_display run must succeed in {runtime_mode}.")
            result = run.get("results", {}).get("markdown-display-1", {})
            expect(result.get("content_type") == "text/markdown", f"markdown_display content type mismatch in {runtime_mode}.")
            expect("# Rapport" in str(result.get("last_message") or ""), f"Markdown source missing in {runtime_mode}.")
            worker_received = str(run.get("worker_rows", {}).get("markdown-display-1", {}).get("received") or "")
            expect("Rapport" in worker_received, f"Worker row Markdown missing in {runtime_mode}.")
            expect(len(worker_received) < len(markdown), f"Worker row must stay bounded in {runtime_mode}.")
            expect("_display_received_messages" not in result, f"markdown_display must not duplicate full text lists in {runtime_mode}.")
            expect(result.get("display_received_count") == 1, f"markdown_display should expose received count in {runtime_mode}.")
    print("[ok] F5.30_markdown_display_block")


if __name__ == "__main__":
    main()
