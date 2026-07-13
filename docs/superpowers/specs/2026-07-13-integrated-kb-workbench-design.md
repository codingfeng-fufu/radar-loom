# Integrated Knowledge Base Workbench Design

## Goal

Turn `http://127.0.0.1:18080/` into the daily technical-radar workspace: browse the knowledge base, render a selected document, and interact with Claude Code without switching browser tabs. Claude sessions continue to start in `/home/u2023312337/知识库`.

## Constraints

- Keep both services bound to `127.0.0.1`.
- Preserve the installed `claude-code-webui` chat behavior and the four permission modes, including `bypassPermissions`.
- Reuse the existing Viewer at port 18081 for Markdown, KaTeX, Mermaid and graph rendering.
- Do not automatically send file contents to Claude when browsing.
- Make all vendor-package modifications reproducible after npm reinstall.

## Architecture

The integration uses a thin workbench shell rather than modifying the minified React component tree.

- `18080/index.html` becomes the workbench shell.
- The original Claude WebUI document is preserved as `18080/claude.html` and loaded in the right pane.
- The knowledge pane loads the existing Viewer from `18081` and retains its own directory/sidebar and document rendering.
- A reproducible patch script owns creation and validation of the shell and the preserved chat entry.
- The existing dangerous-mode patch remains responsible only for Claude permission behavior.

This boundary keeps the upstream chat application replaceable and avoids coupling file browsing to its minified bundle internals.

## Desktop Layout

The first screen is a full-height, three-region operational workspace:

1. Knowledge navigation: the Viewer's collapsible index, approximately 240-300 px.
2. Document preview: the remaining knowledge-pane width, with Markdown, formulas, Mermaid and graph links.
3. Claude Code: approximately 40-45% of the viewport, with the complete existing chat UI.

The knowledge and Claude regions are separated by a draggable divider. Either region can be collapsed from an icon control and restored without reloading its iframe. No explanatory landing page is introduced.

## Mobile Layout

At narrow widths, the workspace switches to three tabs: `文件`, `预览`, and `Claude`. Only one region is visible at a time, and switching tabs does not reload the current document or chat session. Controls use stable dimensions so labels and icons do not move the layout.

## File And Claude Interaction

Selecting a file only changes the preview. It does not modify the Claude conversation or spend context.

The Viewer exposes the active relative file path to its parent with `postMessage`. The workbench displays that path as the current document. An `询问 Claude` command opens a compact question input; submitting it inserts a prompt into the Claude chat input that identifies the relative path and includes the user's question. The user still confirms by sending the message in Claude WebUI.

Messages are accepted only from the expected localhost Viewer origin. Paths remain subject to the Viewer's existing validation rules.

## Knowledge Refresh

The top toolbar includes a familiar refresh icon with the accessible name and tooltip `刷新知识库`. Activating it reloads only the knowledge Viewer iframe at its current URL, so the file tree and rendered document are refreshed while the Claude iframe, conversation, permission mode and unsent input remain intact. The control is disabled briefly during reload and reports completion through the existing status region.

## Graph Access

The Viewer navigation keeps the `交互图谱` entry. Opening it replaces the knowledge preview with `graph-view.html` while the Claude pane remains available. Returning to a Markdown page restores normal preview behavior.

## Failure Handling

- If port 18081 is unavailable, the knowledge pane shows a concise unavailable state while Claude remains usable.
- If the Claude iframe fails, knowledge browsing remains usable and the shell offers a reload command.
- The patcher's `--check` mode fails startup when required workbench or dangerous-mode markers are absent.
- The existing standalone addresses remain available for diagnosis: `18080/claude.html`, `18081/viewer.html`, and `18081/graph-view.html`.

## Testing

Automated contract tests cover shell structure, localhost URLs, responsive tabs, safe message-origin checks, current-file propagation, prompt insertion hooks, and reproducible patch/check behavior.

Browser verification covers:

- desktop three-region rendering and draggable/collapsible panes;
- file selection and Markdown/KaTeX/Mermaid preview;
- `询问 Claude` prompt insertion without automatic send;
- preservation of all four Claude permission modes;
- mobile tab switching at 390 x 844;
- listener binding and restart recovery.

## Deployment And Recovery

The new patch script lives under `/home/u2023312337/webui/`, outside the knowledge-base repository. `webui-control start` runs both patch checks before launching the service. Reinstall recovery is: apply the dangerous-mode patch, apply the workbench patch, run both checks, then restart the service.
