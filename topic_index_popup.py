import customtkinter as ctk
from themed_popup import ThemedPopup
from topic_manager import TopicManager
import json
import os

class TopicIndexPopup(ThemedPopup):
    def __init__(self, parent, theme_manager, settings_manager):
        super().__init__(parent, theme_manager)
        self.title("Topic Index Manager")
        self.geometry("900x700")

        self.tm = TopicManager()
        self.settings_manager = settings_manager
        self.topic_checkboxes = {}
        self.current_topic_slug = None

        # --- Main Layout ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Frame (Topic List & Controls) ---
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ns")
        self.left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.left_frame, text="Available Topics", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5))

        self.scrollable_frame = ctk.CTkScrollableFrame(self.left_frame, label_text="")
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ns")

        self.left_controls_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.left_controls_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.add_to_active_btn = ctk.CTkButton(self.left_controls_frame, text="Add to Active", command=self.add_selected_to_active)
        self.add_to_active_btn.pack(pady=(0, 5), fill="x")

        self.refresh_btn = ctk.CTkButton(self.left_controls_frame, text="Refresh List", command=self.populate_topic_list)
        self.refresh_btn.pack(fill="x")

        # --- Right Frame (Topic Details) ---
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.grid(row=0, column=1, pady=0, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # --- Bottom Frame (Settings) ---
        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=(10, 0), sticky="ew")
        self.create_settings_controls()

        self.populate_topic_list()
        self.create_detail_view_placeholder()

        self.apply_theme()

    def populate_topic_list(self):
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.topic_checkboxes.clear()

        all_topics = self.tm.get_all_topic_names()
        search_data = self.tm.get_topic_search_data()

        for i, slug in enumerate(sorted(all_topics)):
            display_name = search_data.get(slug, {}).get('display_name', slug)

            # Use a frame to group button and checkbox
            item_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            item_frame.pack(fill="x", expand=True)

            var = ctk.StringVar()
            cb = ctk.CTkCheckBox(item_frame, text="", variable=var, width=20)
            cb.pack(side="left", padx=(0, 5))
            self.topic_checkboxes[slug] = var

            button = ctk.CTkButton(item_frame, text=display_name, fg_color="transparent", anchor="w", command=lambda s=slug: self.show_topic_details(s))
            button.pack(side="left", fill="x", expand=True)

    def add_selected_to_active(self):
        selected_slugs = [slug for slug, var in self.topic_checkboxes.items() if var.get() == '1']
        if not selected_slugs:
            return

        self.tm.clear_active_topics() # As per user story, bulk-add implies replacing
        self.tm.add_topics_to_active(selected_slugs)
        print(f"Added {len(selected_slugs)} topics to active: {selected_slugs}")


    def create_detail_view_placeholder(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        placeholder_label = ctk.CTkLabel(self.right_frame, text="Select a topic to view or edit its details.", font=ctk.CTkFont(size=14))
        placeholder_label.pack(expand=True, padx=20, pady=20)

    def show_topic_details(self, topic_slug):
        self.current_topic_slug = topic_slug
        content = self.tm.get_topic_content(topic_slug)
        if content is None:
            self.create_detail_view_placeholder()
            return

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # --- Header ---
        header_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        search_data = self.tm.get_topic_search_data()
        display_name = search_data.get(topic_slug, {}).get('display_name', topic_slug)

        ctk.CTkLabel(header_frame, text=display_name, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        save_button = ctk.CTkButton(header_frame, text="Save Changes", command=self.save_topic_details)
        save_button.pack(side="right")

        # --- Tab View ---
        tab_view = ctk.CTkTabview(self.right_frame)
        tab_view.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.detail_textboxes = {}
        sections = ["Summary", "Personal Insights", "Linked Topics", "Chat Entries", "Notes", "Metadata"]

        parsed_content = self._parse_topic_content(content)

        for sec in sections:
            tab = tab_view.add(sec)
            textbox = ctk.CTkTextbox(tab, wrap="word", height=400, width=550)
            textbox.pack(expand=True, fill="both", padx=5, pady=5)
            textbox.insert("1.0", parsed_content.get(sec, ""))
            self.detail_textboxes[sec] = textbox

    def _parse_topic_content(self, content):
        parsed = {}
        # A simple parser based on the template structure
        # This is not robust to format changes, but matches the spec
        # It assumes headers like 'Summary:' are on their own line or followed by a newline

        # Regex to find a section header and capture all content until the next section header or EOF
        pattern = re.compile(r"^(Topic|Alt Names|Summary|Personal Insights|Linked Topics|Optional: Tags|Chat Entries|Notes):\s*$(.*?)", re.MULTILINE | re.DOTALL)

        # This is tricky. A simpler line-by-line parser is more reliable here.
        lines = content.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            if line.startswith("Summary:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Summary"
                current_content = [line.split(":",1)[1].strip()]
            elif line.startswith("Personal Insights:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Personal Insights"
                current_content = []
            elif line.startswith("Linked Topics:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Linked Topics"
                current_content = []
            elif line.startswith("Chat Entries:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Chat Entries"
                current_content = []
            elif line.startswith("Notes:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Notes"
                current_content = []
            elif line.startswith("Optional: Tags:"):
                if current_section: parsed[current_section] = "\n".join(current_content).strip()
                current_section = "Metadata"
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section: # Save the last section
            parsed[current_section] = "\n".join(current_content).strip()

        # Add the unparsed parts for Metadata
        if 'Metadata' not in parsed:
            meta_content = []
            in_meta = False
            for line in lines:
                if line.startswith("Optional: Tags:"): in_meta = True
                if line.startswith("Chat Entries:"): in_meta = False
                if in_meta: meta_content.append(line)
            parsed['Metadata'] = "\n".join(meta_content)


        return parsed


    def save_topic_details(self):
        if not self.current_topic_slug:
            return

        # Reconstruct the file content from the textboxes
        # This is a bit brittle and depends on the template structure.

        # Get the original Topic and Alt Names to preserve them
        original_content = self.tm.get_topic_content(self.current_topic_slug)
        header_lines = []
        for line in original_content.split('\n'):
            if line.startswith("Topic:") or line.startswith("Alt Names:"):
                header_lines.append(line)
            else:
                break

        new_content = "\n".join(header_lines) + "\n\n"
        new_content += "Summary:\n" + self.detail_textboxes["Summary"].get("1.0", "end-1c") + "\n\n"
        new_content += "Personal Insights:\n" + self.detail_textboxes["Personal Insights"].get("1.0", "end-1c") + "\n\n"
        new_content += "Linked Topics:\n" + self.detail_textboxes["Linked Topics"].get("1.0", "end-1c") + "\n\n"
        new_content += self.detail_textboxes["Metadata"].get("1.0", "end-1c") + "\n\n" # Metadata includes the "Optional: Tags:" header
        new_content += "Chat Entries:\n" + self.detail_textboxes["Chat Entries"].get("1.0", "end-1c") + "\n\n"
        new_content += "Notes:\n" + self.detail_textboxes["Notes"].get("1.0", "end-1c")

        self.tm.save_topic_content(self.current_topic_slug, new_content.strip())
        print(f"Saved changes to {self.current_topic_slug}")

    def create_settings_controls(self):
        """Creates the checkboxes for default topic loader settings."""
        ctk.CTkLabel(self.bottom_frame, text="Default Context Injection:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=5)

        self.setting_vars = {}
        defaults = self.settings_manager.get_setting("topic_defaults", {
            "summary": True, "insights": True, "timeline": True
        })

        for setting_name in ["summary", "insights", "timeline"]:
            var = ctk.BooleanVar(value=defaults.get(setting_name, False))
            cb = ctk.CTkCheckBox(self.bottom_frame, text=setting_name.title(), variable=var, command=self.save_settings)
            cb.pack(side="left", padx=5, pady=5)
            self.setting_vars[setting_name] = var

    def save_settings(self):
        """Saves the default loader settings."""
        new_settings = {name: var.get() for name, var in self.setting_vars.items()}
        self.settings_manager.set_setting("topic_defaults", new_settings)
        print(f"Saved topic default settings: {new_settings}")
