"""PyFASM Example 09: Modern GUI Application (CustomTkinter)
Compiles modern dark/light UI applications with zero external Python installation on target machines.

Compile with:
    pyfasm64 compile examples/09_customtkinter_app.py --gui -o 09_customtkinter_app.exe
"""

import customtkinter as ctk

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PyFASM Modern UI")
        self.geometry("450x300")

        self.label = ctk.CTkLabel(self, text="Native Modern UI compiled by PyFASM")
        self.label.pack(pady=20)

        self.entry = ctk.CTkEntry(self, placeholder_text="Enter text here...")
        self.entry.pack(pady=10)

        self.btn = ctk.CTkButton(self, text="Submit", command=self.on_submit)
        self.btn.pack(pady=10)

    def on_submit(self):
        print("Submit button pressed in native GUI loop!")


if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()
