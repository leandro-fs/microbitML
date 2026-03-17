# main.py
import tkinter as tk
import sys
from core.app_controller import AppController

def main():
    root = tk.Tk()
    AppController(root)
    root.mainloop()

if __name__ == '__main__':
    main()