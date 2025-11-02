"""Textual TUI application for SageMTL workflows."""

from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
    TabPane,
    TabbedContent,
    TextArea,
    TextLog,
)

from sagemtl.clean import normalize_text
from sagemtl.crawl import extract_main_text


class SageMTLApp(App[None]):
    """Main Textual application for SageMTL."""

    CSS: ClassVar[
        str
    ] = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    # Body contains the navigation rail and the tabbed workspace.
    # It occupies the space between the header and footer.
    #
    # ┌─────────┬────────────────────────────┐
    # │ nav     │      tabbed content        │
    # └─────────┴────────────────────────────┘
    #
    # The textual CSS ensures the left-hand ListView keeps a fixed
    # width and the tabbed content expands to fill the remaining area.
    # The log and status area is stacked below the tabs.
    #
    # Screen layout is vertical:
    #  Header
    #  Horizontal body (nav + tabs)
    #  Footer
    #
    # Within the body, "workspace" splits tabs and log/status sections.

    # Body container with navigation + workspace
    # Equivalent to flex row
    # -- Navigation rail styling --
    # Tabbed content takes the remaining space.

    # Navigation styles
    #   * fixed width so text fits cleanly

    # Workspace contains the main tab panes and the status/log area.

    Screen > Horizontal#body {
        height: 1fr;
        min-height: 0;
    }

    Horizontal#body {
        layout: horizontal;
    }

    ListView#nav {
        width: 24;
        min-width: 24;
        border-right: solid $secondary 20%;
    }

    Container#workspace {
        layout: vertical;
        height: 1fr;
        min-height: 0;
    }

    TabbedContent {
        height: 1fr;
        min-height: 0;
    }

    TabPane {
        padding: 1 2;
        overflow-y: auto;
    }

    Vertical.tool-section {
        padding: 1;
        border: solid $primary 10%;
        border-radius: 1;
        background: $boost;
        height: auto;
        min-height: 0;
    }

    TextArea {
        height: 8;
        min-height: 5;
    }

    TextArea.readonly {
        background: $surface 5%;
    }

    Container#status-log {
        height: 12;
        min-height: 8;
        border-top: solid $surface 10%;
        padding: 1 2;
        layout: vertical;
    }

    Static#status-bar {
        padding: 0 1;
        color: $accent;
    }

    TextLog#event-log {
        height: 1fr;
        border: solid $surface 15%;
        background: $surface 3%;
    }

    .dimmed {
        color: $text 60%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+n", "normalize", "Normalize Text"),
        Binding("ctrl+e", "extract", "Extract Main Text"),
        Binding("ctrl+b", "focus_batch", "Go to Batch"),
        Binding("ctrl+t", "focus_translate", "Go to Translate"),
        Binding("ctrl+s", "focus_settings", "Go to Settings"),
    ]

    status_message: reactive[str] = reactive("Ready.")

    def __init__(self) -> None:
        super().__init__()
        self._nav_map: dict[str, str] = {
            "nav-clean": "tab-clean",
            "nav-crawl": "tab-crawl",
            "nav-batch": "tab-batch",
            "nav-translate": "tab-translate",
            "nav-settings": "tab-settings",
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield ListView(
                ListItem(Label("Clean"), id="nav-clean"),
                ListItem(Label("Crawl"), id="nav-crawl"),
                ListItem(Label("Batch"), id="nav-batch"),
                ListItem(Label("Translate"), id="nav-translate"),
                ListItem(Label("Settings"), id="nav-settings"),
                id="nav",
            )
            with Container(id="workspace"):
                with TabbedContent(id="tabs"):
                    with TabPane("Clean", id="tab-clean"):
                        with Vertical(classes="tool-section"):
                            yield Label("Source text", id="label-clean-src")
                            yield TextArea(
                                id="clean-input",
                                placeholder="Paste or type text to normalize…",
                            )
                            yield Button(
                                "Normalize text (Ctrl+N)",
                                id="btn-normalize",
                                variant="success",
                            )
                            yield Label("Normalized output")
                            yield TextArea(
                                id="clean-output",
                                placeholder="Normalized text will appear here.",
                                read_only=True,
                                classes="readonly",
                            )
                    with TabPane("Crawl", id="tab-crawl"):
                        with Vertical(classes="tool-section"):
                            yield Label("HTML input")
                            yield TextArea(
                                id="crawl-input",
                                placeholder="Paste HTML markup to extract…",
                            )
                            yield Button(
                                "Extract main text (Ctrl+E)",
                                id="btn-extract",
                                variant="primary",
                            )
                            yield Label("Extracted text")
                            yield TextArea(
                                id="crawl-output",
                                placeholder="Extracted article text will appear here.",
                                read_only=True,
                                classes="readonly",
                            )
                    with TabPane("Batch", id="tab-batch"):
                        with Vertical(classes="tool-section"):
                            yield Label(
                                "Batch processing tools will orchestrate directory-based crawls."
                            )
                            yield Label(
                                "Use the CLI for now: sagemtl crawl-batch --help",
                                classes="dimmed",
                            )
                    with TabPane("Translate", id="tab-translate"):
                        with Vertical(classes="tool-section"):
                            yield Label("Translation workflows are under construction.")
                            yield Label(
                                "Check the roadmap for upcoming models.",
                                classes="dimmed",
                            )
                    with TabPane("Settings", id="tab-settings"):
                        with Vertical(classes="tool-section"):
                            yield Label(
                                "Configure API keys, storage paths, and preferences."
                            )
                            yield Label(
                                "Configuration storage is not yet implemented in this build.",
                                classes="dimmed",
                            )
                with Container(id="status-log"):
                    yield Static(self.status_message, id="status-bar")
                    yield TextLog(id="event-log", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        nav = self.query_one("#nav", ListView)
        tabs = self.query_one(TabbedContent)
        nav.index = 0
        tabs.active = "tab-clean"
        nav.focus()
        self.log_event("SageMTL TUI ready.")
        self.update_status("Ready.")

    def log_event(self, message: str) -> None:
        log = self.query_one("#event-log", TextLog)
        log.write(message)

    def update_status(self, message: str) -> None:
        self.status_message = message

    def watch_status_message(self, message: str) -> None:
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(message)

    def action_focus_batch(self) -> None:
        self._activate_tab("tab-batch")

    def action_focus_translate(self) -> None:
        self._activate_tab("tab-translate")

    def action_focus_settings(self) -> None:
        self._activate_tab("tab-settings")

    def action_normalize(self) -> None:
        input_area = self.query_one("#clean-input", TextArea)
        output_area = self.query_one("#clean-output", TextArea)
        source = input_area.value
        if not source.strip():
            self.update_status("No text provided for normalization.")
            self.log_event("Normalize requested but input was empty.")
            return
        try:
            normalized = normalize_text(source)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.update_status("Normalization failed. See log for details.")
            self.log_event(f"[red]Normalization error:[/] {exc}")
            return
        output_area.value = normalized
        self.update_status("Text normalized successfully.")
        self.log_event("Normalized text with clean.text_normalize.normalize_text().")

    def action_extract(self) -> None:
        input_area = self.query_one("#crawl-input", TextArea)
        output_area = self.query_one("#crawl-output", TextArea)
        html = input_area.value
        if not html.strip():
            self.update_status("No HTML provided for extraction.")
            self.log_event("Extract requested but HTML input was empty.")
            return
        try:
            extracted = extract_main_text(html)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.update_status("Extraction failed. See log for details.")
            self.log_event(f"[red]Extraction error:[/] {exc}")
            return
        output_area.value = extracted
        self.update_status("Main text extracted successfully.")
        self.log_event("Extracted text with crawl.extract.extract_main_text().")

    def _activate_tab(self, tab_id: str) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = tab_id
        nav = self.query_one("#nav", ListView)
        for index, item in enumerate(nav.children):
            if (
                isinstance(item, ListItem)
                and self._nav_map.get(item.id or "") == tab_id
            ):
                nav.index = index
                break
        self.update_status(f"Switched to {tab_id.removeprefix('tab-').title()} tab.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-normalize":
            self.action_normalize()
        elif event.button.id == "btn-extract":
            self.action_extract()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if item.id and item.id in self._nav_map:
            self._activate_tab(self._nav_map[item.id])

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        tab_id = event.tab.id
        nav = self.query_one("#nav", ListView)
        for index, item in enumerate(nav.children):
            if (
                isinstance(item, ListItem)
                and self._nav_map.get(item.id or "") == tab_id
            ):
                nav.index = index
                break

    async def on_key(self, event: events.Key) -> None:  # pragma: no cover - runtime UX
        if event.key == "f1":
            self.log_event(
                "Visit https://github.com/blood-dawn/sagemtl for documentation."
            )
