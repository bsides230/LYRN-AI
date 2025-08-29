import customtkinter as ctk
from themed_popup import ThemedPopup, ThemeManager

import tkinter.messagebox
from themed_popup import ThemedPopup, ThemeManager
import customtkinter as ctk

class RWIInstructionEditorPopup(ThemedPopup):
    """A popup for editing a specific RWI component's instruction, start bracket, and end bracket."""
    def __init__(self, parent, theme_manager: ThemeManager, component_name: str, instruction: str, start_bracket: str, end_bracket: str, save_callback, is_locked: bool = False):
        super().__init__(parent=parent, theme_manager=theme_manager)
        self.title(f"Edit Instruction: {component_name}")
        self.geometry("500x400")
        self.grab_set()

        self.component_name = component_name
        self.save_callback = save_callback
        self.is_locked = is_locked

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=10)

        # Bracket editors
        bracket_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bracket_frame.pack(fill="x", pady=(0, 10))
        bracket_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bracket_frame, text="Start Bracket:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.start_bracket_entry = ctk.CTkEntry(bracket_frame)
        self.start_bracket_entry.grid(row=0, column=1, sticky="ew")
        self.start_bracket_entry.insert(0, start_bracket)

        ctk.CTkLabel(bracket_frame, text="End Bracket:").grid(row=1, column=0, padx=(0, 5), pady=(5,0), sticky="w")
        self.end_bracket_entry = ctk.CTkEntry(bracket_frame)
        self.end_bracket_entry.grid(row=1, column=1, sticky="ew", pady=(5,0))
        self.end_bracket_entry.insert(0, end_bracket)

        # Instruction editor
        ctk.CTkLabel(main_frame, text="Instruction:").pack(anchor="w", pady=(10, 5))
        self.instruction_textbox = ctk.CTkTextbox(main_frame, wrap="word")
        self.instruction_textbox.pack(expand=True, fill="both", pady=(0, 10))
        self.instruction_textbox.insert("1.0", instruction)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.save_button = ctk.CTkButton(button_frame, text="Save", command=self.save_and_close)
        self.save_button.pack(side="right", padx=5)

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side="right", padx=5)

        if self.is_locked:
            self.save_button.configure(state="disabled")
            ctk.CTkLabel(main_frame, text="RWI file is locked by the Full RWI Viewer. Unlock to save changes.", text_color="orange", wraplength=460).pack(pady=(5,0))


        self.apply_theme()

    def save_and_close(self):
        """Saves the brackets and instruction content and closes the popup."""
        if self.is_locked:
            tkinter.messagebox.showwarning(
                "File Locked",
                "The RWI file is currently locked by the Full RWI Viewer/Editor. Please close that window or unlock the file to save changes."
            )
            return

        new_instruction = self.instruction_textbox.get("1.0", "end-1c")
        new_start_bracket = self.start_bracket_entry.get()
        new_end_bracket = self.end_bracket_entry.get()
        self.save_callback(self.component_name, new_instruction, new_start_bracket, new_end_bracket)
        self.destroy()
