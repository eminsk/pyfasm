"""PyFASM Example 07: Native Windows GUI (Tkinter)
Compiles a standard desktop window with event-driven buttons and labels into a lightweight PE64 binary.

Compile with:
    pyfasm64 compile examples/07_tkinter_gui.py --gui -o 07_tkinter_gui.exe
"""

import tkinter as tk

def on_click():
    print("Action button triggered!")

root = tk.Tk()
root.title("PyFASM Native Window")
root.geometry("420x260")

label = tk.Label(root, text="Compiled to Native Machine Code with PyFASM v1.1.0!")
label.pack()

btn = tk.Button(root, text="Click Here", command=on_click)
btn.pack()

root.mainloop()
