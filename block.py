# -----------------------------------------------------------------------------
# Role: Implements the Markdown display block runtime and UI contract.
# File Name: block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-06-22
# -----------------------------------------------------------------------------

from __future__ import annotations

from html import escape
import re
from typing import Any

from bloxsmith_app.block_api import (
    BlockDefinition,
    BlockRuntimeResult,
    render_inspector_template,
    render_node_card_template,
)

TEXT_MARKDOWN = "text/markdown"
MARKDOWN_DISPLAY_WORKER_PREVIEW_LIMIT = 300


# Functional behavior:
# FB1 - Capture Markdown runtime data as a block-owned display sink result.
# FB2 - Render Markdown safely in the modal while preserving raw Markdown for copy/debug.
# FB3 - Keep node-card and inspector rendering block-owned and generic-framework compatible.
class MarkdownDisplayBlock(BlockDefinition):
    """Autonomous block implementation for the `markdown_display` sink."""

    kind = "markdown_display"

    def execute_runtime(self, context: Any) -> BlockRuntimeResult:
        """Capture the received Markdown payload as this sink block result.

        Args:
            context: Runtime context populated by centralized or ZeroMQ active execution.

        Returns:
            Successful runtime result with no outputs and the received Markdown preserved.
        """

        message = self._runtime_message(context)
        messages = self._received_messages(context, message)
        accumulated_message = "\n\n".join(messages)
        node_id = str(getattr(context, "node_id", "") or self.kind)
        log = (
            f"[markdown-display] {node_id}: {len(accumulated_message)} caractere(s) Markdown recu(s)."
            if accumulated_message
            else f"[markdown-display] {node_id}: aucune entree Markdown recue."
        )
        return BlockRuntimeResult(
            status="success",
            outputs=[],
            logs=[log],
            last_message=accumulated_message,
            content_type=TEXT_MARKDOWN,
            worker_received=self._worker_preview(accumulated_message),
            metadata={
                "content_type": TEXT_MARKDOWN,
                "display_received_count": len(messages),
            },
        )

    def render_node_card(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the Markdown Display canvas card body.

        Args:
            node: Serialized Markdown Display node being rendered.
            payload: Optional UI payload that may contain the latest Markdown output.

        Returns:
            Block UI payload used by the generic canvas shell.
        """

        payload = payload or {}
        display_output = self._display_output(node=node, payload=payload)
        return render_node_card_template(
            block=self,
            node=node,
            node_classes=["markdown-display-node"],
            replacements={
                "title": node.get("title") or self.default_title(),
                "preview": self._truncate(str(display_output or "Waiting for Markdown"), 60),
            },
        )

    def render_inspector_panel(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the Markdown Display inspector from generic runtime UI payload.

        Args:
            node: Serialized Markdown Display node.
            payload: Optional UI payload containing runtime output previews.

        Returns:
            Block inspector payload with rendered HTML and context metadata.
        """

        payload = payload or {}
        markdown_source = self._display_output(node=node, payload=payload)
        template = (self.directory / "inspector_panel.html").read_text(encoding="utf-8")
        html = render_inspector_template(
            template=(
                template
                .replace("{{ display_source }}", escape(self._display_source(node=node, payload=payload)))
                .replace("{{ markdown_source }}", escape(str(markdown_source or "Aucune sortie disponible pour l'instant.")))
            ),
            node={**node, "type": self.kind, "kind": self.kind},
            payload=payload,
            show_duplicate=False,
        )
        return {"html": html, "context": {"node_id": str(node.get("id") or ""), "full_panel": True}}

    def render_modal(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the full Markdown output modal from block-owned HTML.

        Args:
            node: Serialized Markdown Display node selected by the user.
            payload: Generic UI payload containing runtime input/output previews.

        Returns:
            Block modal payload consumed by the shared modal host.
        """

        payload = payload or {}
        items = self._display_items(node=node, payload=payload)
        template = (self.directory / "block_modal.html").read_text(encoding="utf-8")
        html = (
            template.replace("{{ title }}", escape(str(node.get("title") or self.default_title())))
            .replace("{{ summary }}", escape(self._modal_summary(items)))
            .replace("{{ items_html }}", self._render_modal_items(items))
            .replace("{{ clipboard_text }}", escape(self._modal_clipboard_text(items)))
        )
        return {
            "html": html,
            "context": {
                "node_id": str(node.get("id") or ""),
                "item_count": len(items),
            },
        }

    def _truncate(self, value: str, max_length: int) -> str:
        """Return a compact one-line preview for the canvas card."""

        text = str(value or "").replace("\n", " ").strip()
        return text if len(text) <= max_length else f"{text[: max_length - 1]}..."

    def _runtime_message(self, context: Any) -> str:
        """Return the ordered input payload received by the Markdown sink."""

        if hasattr(context, "input_values"):
            values: list[Any] = []
            try:
                values = list(context.input_values("md"))
            except Exception:
                values = []
            if values:
                return "\n\n".join(str(value or "") for value in values if str(value or ""))
        message = str(getattr(context, "input_message", "") or "")
        return message


    def _received_messages(self, context: Any, message: str) -> list[str]:
        """Append this execution payload to previously captured active Markdown messages."""

        previous = getattr(context, "previous_result", {}) or {}
        raw_previous = previous.get("_display_received_messages") if isinstance(previous, dict) else None
        messages = [str(item) for item in raw_previous if str(item)] if isinstance(raw_previous, list) else []
        if not messages and isinstance(previous, dict) and str(previous.get("last_message") or ""):
            messages = [str(previous.get("last_message") or "")]
        if message:
            messages.append(message)
        return messages

    def _worker_preview(self, value: str) -> str:
        """Return a bounded worker row preview without duplicating full Markdown."""

        text = str(value or "")
        if len(text) <= MARKDOWN_DISPLAY_WORKER_PREVIEW_LIMIT:
            return text
        hidden = len(text) - MARKDOWN_DISPLAY_WORKER_PREVIEW_LIMIT
        return f"{text[:MARKDOWN_DISPLAY_WORKER_PREVIEW_LIMIT]}... ({hidden} caracteres masques)"

    def _runtime_payload(self, payload: dict[str, Any], node: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the generic runtime payload supplied by the editor."""

        runtime = payload.get("runtime")
        if isinstance(runtime, dict):
            return runtime
        node_runtime = node.get("runtimeUi") if isinstance(node, dict) else None
        return node_runtime if isinstance(node_runtime, dict) else {}

    def _display_output(self, *, node: dict[str, Any], payload: dict[str, Any]) -> str:
        """Resolve the latest Markdown output from the runtime payload."""

        runtime = self._runtime_payload(payload, node)
        if runtime.get("latest_message"):
            return str(runtime.get("latest_message") or "")
        return str(node.get("output") or "")

    def _display_source(self, *, node: dict[str, Any], payload: dict[str, Any]) -> str:
        """Resolve a readable source label from generic runtime inputs."""

        runtime = self._runtime_payload(payload, node)
        inputs = runtime.get("received_inputs")
        if isinstance(inputs, list) and inputs:
            first = inputs[0] if isinstance(inputs[0], dict) else {}
            return str(first.get("label") or "")
        return ""

    def _display_items(self, *, node: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
        """Resolve all Markdown values that should be shown in the modal."""

        runtime = self._runtime_payload(payload, node)
        inputs = runtime.get("received_inputs")
        if isinstance(inputs, list) and inputs:
            return [
                {
                    "label": str(item.get("label") or "Entrée reçue"),
                    "target_label": str(item.get("target_label") or item.get("targetLabel") or node.get("title") or ""),
                    "content": str(item.get("content") or ""),
                }
                for item in inputs
                if isinstance(item, dict) and str(item.get("content") or "")
            ]

        latest = str(runtime.get("latest_message") or "")
        if latest:
            return [{"label": "Runtime", "target_label": str(node.get("title") or ""), "content": latest}]

        output = str(node.get("output") or "")
        if output:
            return [{"label": "Output received", "target_label": str(node.get("title") or ""), "content": output}]
        return []

    def _modal_summary(self, items: list[dict[str, str]]) -> str:
        """Return the modal summary sentence for the resolved Markdown items."""

        if not items:
            return "Aucun contenu Markdown reçu pour ce bloc."
        suffix = "s" if len(items) > 1 else ""
        return f"{len(items)} contenu{suffix} Markdown reçu{suffix}."

    def _render_modal_items(self, items: list[dict[str, str]]) -> str:
        """Render Markdown output cards for the modal body."""

        if not items:
            return '<div class="ports-editor-empty">Run the workflow or load a run to see the Markdown rendering.</div>'
        cards: list[str] = []
        for index, item in enumerate(items):
            label = escape(item.get("label") or f"Source {index + 1}")
            target = escape(item.get("target_label") or "")
            rendered = self._render_markdown(item.get("content") or "")
            cards.append(
                '<article class="display-output-card markdown-rendered-card">'
                '<div class="display-output-card-header">'
                f"<span>{label}</span>"
                f"<span>{target}</span>"
                "</div>"
                f'<div class="markdown-rendered-content">{rendered}</div>'
                "</article>"
            )
        return "".join(cards)

    def _modal_clipboard_text(self, items: list[dict[str, str]]) -> str:
        """Build the raw Markdown text copied by the generic modal copy button."""

        return "\n\n---\n\n".join(f"{item.get('label') or 'Source'}\n{item.get('content') or ''}" for item in items)

    def _render_markdown(self, source: str) -> str:
        """Render a safe Markdown subset while escaping raw HTML."""

        lines = str(source or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        html_parts: list[str] = []
        paragraph: list[str] = []
        list_items: list[str] = []
        ordered_list = False
        in_code = False
        code_lines: list[str] = []

        def flush_paragraph() -> None:
            if paragraph:
                html_parts.append(f"<p>{self._render_inline(' '.join(paragraph).strip())}</p>")
                paragraph.clear()

        def flush_list() -> None:
            nonlocal ordered_list
            if list_items:
                tag = "ol" if ordered_list else "ul"
                html_parts.append(f"<{tag}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{tag}>")
                list_items.clear()
                ordered_list = False

        def flush_code() -> None:
            if code_lines:
                html_parts.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    flush_code()
                    in_code = False
                else:
                    flush_paragraph()
                    flush_list()
                    in_code = True
                continue
            if in_code:
                code_lines.append(raw_line)
                continue
            if not stripped:
                flush_paragraph()
                flush_list()
                continue
            if re.fullmatch(r"[-*_]{3,}", stripped):
                flush_paragraph()
                flush_list()
                html_parts.append("<hr>")
                continue
            heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading:
                flush_paragraph()
                flush_list()
                level = len(heading.group(1))
                html_parts.append(f"<h{level}>{self._render_inline(heading.group(2).strip())}</h{level}>")
                continue
            unordered = re.match(r"^[-*+]\s+(.+)$", stripped)
            ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
            if unordered or ordered:
                flush_paragraph()
                next_ordered = bool(ordered)
                if list_items and ordered_list != next_ordered:
                    flush_list()
                ordered_list = next_ordered
                list_items.append(self._render_inline((ordered or unordered).group(1).strip()))
                continue
            if stripped.startswith(">"):
                flush_paragraph()
                flush_list()
                html_parts.append(f"<blockquote>{self._render_inline(stripped.lstrip('>').strip())}</blockquote>")
                continue
            paragraph.append(stripped)

        if in_code:
            flush_code()
        flush_paragraph()
        flush_list()
        return "".join(html_parts) or "<p></p>"

    def _render_inline(self, value: str) -> str:
        """Render safe inline Markdown markers after escaping raw text."""

        text = escape(str(value or ""))
        code_tokens: list[str] = []

        def stash_code(match: re.Match[str]) -> str:
            code_tokens.append(f"<code>{match.group(1)}</code>")
            return f"@@CODE{len(code_tokens) - 1}@@"

        text = re.sub(r"`([^`]+)`", stash_code, text)
        text = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)", r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
        for index, token in enumerate(code_tokens):
            text = text.replace(f"@@CODE{index}@@", token)
        return text
