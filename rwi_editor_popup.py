import customtkinter as ctk
from themed_popup import ThemedPopup, ThemeManager

class RWIInstructionEditorPopup(ThemedPopup):
    """A popup for editing a specific RWI component's instruction."""
    def __init__(self, parent, theme_manager: ThemeManager, component_name: str, instruction: str, save_callback):
        super().__init__(parent=parent, theme_manager=theme_manager)
        self.title(f"Edit Instruction: {component_name}")
        self.geometry("450x300")
        self.grab_set()

        self.component_name = component_name
        self.save_callback = save_callback

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=10)

        self.instruction_textbox = ctk.CTkTextbox(main_frame, wrap="word")
        self.instruction_textbox.pack(expand=True, fill="both", pady=(0, 10))
        self.instruction_textbox.insert("1.0", instruction)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 10))

        save_button = ctk.CTkButton(button_frame, text="Save", command=self.save_and_close)
        save_button.pack(side="right", padx=5)

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side="right", padx=5)

        self.apply_theme()

    def save_and_close(self):
        """Saves the content and closes the popup."""
        new_instruction = self.instruction_textbox.get("1.0", "end-1c")
        self.save_callback(self.component_name, new_instruction)
        self.destroy()
