# Markdown Display

<!-- block-metadata:start -->
[![Block version: 0.1.0](https://img.shields.io/badge/block-0.1.0-blue)](model.json)
[![BloxSmith compatibility: 1.0.9](https://img.shields.io/badge/BloxSmith-1.0.9-brightgreen)](compatibility.json)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Verified BloxSmith versions: **1.0.9** (bundled-block tests; see [test evidence](compatibility.json)).
<!-- block-metadata:end -->


Display Markdown from another block: reports, Codex responses, documentation or other structured text, without transforming the rest of the workflow. The current UI calls this block **Visualiser md**.

## When to use it

Inspect Markdown on the graph or in a readable modal. Use `html_display` for raw HTML instead.

## Ports

Input **`md`** accepts `text/markdown`, `text/plain`, `message/*` and `application/json`. This is a display sink with no outputs.

## Behavior

The block captures received content and keeps the raw Markdown in its runtime result. The canvas shows a short one-line preview, the inspector shows captured source, and the modal provides scrollable rendered Markdown and a copy-raw-Markdown action.

## Security and limits

Raw HTML is escaped. The supported safe Markdown subset includes headings, paragraphs, lists, block quotes, separators, inline/fenced code, bold, italics and HTTP/HTTPS/mailto links.

## Example

Connect an upstream response such as:

```markdown
# Report

- First point
- Second point
```

Open the block modal to read the rendered report.

## Compatibility policy

[compatibility.json](compatibility.json) records HackInvent's verified BloxSmith versions and test evidence. Only the versions listed above have been verified, using the block-owned suites in a **bundled-block test installation**. This is not a certification of managed-package installation, every browser/OS, or live provider availability. Other framework versions are unverified, not necessarily incompatible.

The block-version badge follows `model.json`, not a published Git tag. `unversioned` means that no block release version is declared; no number is inferred from the framework version. The framework still uses `model.json` for its runtime/install contract; the tester-owned JSON does not replace it. Official integration tests run in the private `bloxmith-blocs` workspace. Test helpers and the proprietary framework are not bundled in this public block repository.

## Properties ergonomics

Modal and inspector styles are owned by this package and scoped to its exact
release. Forms adapt to narrow panels, checkboxes stay beside their labels, and
long values do not widen the inspector. Existing labels are associated with
controls; keyboard navigation complements the block’s own tab handlers.
These presentation helpers do not change port bindings, authored settings,
runtime behavior or the block’s original surface cleanup.
