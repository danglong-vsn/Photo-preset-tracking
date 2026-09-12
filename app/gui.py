"""
Small desktop GUI: drag a photo in (or click Browse), click Generate,
save the resulting .xmp preset. Runs fully offline.

Uses only tkinter (bundled with Python) plus, optionally, tkinterdnd2 for
drag-and-drop. If tkinterdnd2 isn't installed the app still works fully via
the Browse button -- it just won't accept drag-and-drop.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except Exception:
    _HAS_DND = False

from PIL import Image, ImageTk

from .analyzer import analyze_image
from .xmp_writer import save_xmp

IMAGE_FILETYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
    ("All files", "*.*"),
]


def _open_in_file_manager(path: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path])
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", path])
        else:
            subprocess.run(["xdg-open", str(Path(path).parent)])
    except Exception:
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Look → XMP")
        self.root.geometry("560x520")
        self.root.minsize(480, 460)

        self.image_path: str | None = None
        self.thumb_image = None  # keep a reference so Tk doesn't GC it

        self._build_widgets()

    # ------------------------------------------------------------------ UI
    def _build_widgets(self):
        pad = {"padx": 14, "pady": 8}

        title = tk.Label(self.root, text="Photo Look → Lightroom XMP",
                          font=("Helvetica", 16, "bold"))
        title.pack(**pad)

        subtitle = tk.Label(
            self.root,
            text="Drop a photo below to extract its color look as a Lightroom\n"
                 "(.xmp) preset you can apply to other photos.",
            font=("Helvetica", 10), justify="center", fg="#555555",
        )
        subtitle.pack()

        self.drop_frame = tk.Frame(self.root, bg="#eef0f3", height=200,
                                    highlightthickness=2, highlightbackground="#c7cbd1")
        self.drop_frame.pack(fill="both", expand=True, padx=20, pady=14)
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_frame, bg="#eef0f3", fg="#666666",
            text=self._drop_hint_text(), justify="center", font=("Helvetica", 11),
        )
        self.drop_label.pack(expand=True)

        browse_btn = tk.Button(self.root, text="Browse for a photo…", command=self.browse)
        browse_btn.pack(pady=(0, 6))

        name_frame = tk.Frame(self.root)
        name_frame.pack(fill="x", padx=20, pady=(6, 4))
        tk.Label(name_frame, text="Preset name:").pack(side="left")
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.generate_btn = tk.Button(
            self.root, text="Generate XMP…", state="disabled",
            font=("Helvetica", 11, "bold"), command=self.on_generate,
        )
        self.generate_btn.pack(pady=10, ipadx=10, ipady=4)

        self.status_var = tk.StringVar(value="Waiting for a photo…")
        status = tk.Label(self.root, textvariable=self.status_var, fg="#444444")
        status.pack(pady=(0, 10))

        if _HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)

    def _drop_hint_text(self) -> str:
        if _HAS_DND:
            return "Drag & drop a photo here"
        return "(Drag & drop not available on this install —\nuse the Browse button below)"

    # ------------------------------------------------------------- actions
    def _on_drop(self, event):
        # tkinterdnd2 gives paths possibly wrapped in {}
        raw = event.data
        path = raw.strip("{}")
        self.load_image(path)

    def browse(self):
        path = filedialog.askopenfilename(title="Choose a photo", filetypes=IMAGE_FILETYPES)
        if path:
            self.load_image(path)

    def load_image(self, path: str):
        try:
            img = Image.open(path)
            img.thumbnail((260, 180))
            self.thumb_image = ImageTk.PhotoImage(img)
            self.drop_label.configure(image=self.thumb_image, text="")
        except Exception:
            messagebox.showerror("Couldn't open file", f"That doesn't look like a supported image:\n{path}")
            return

        self.image_path = path
        self.name_var.set(Path(path).stem + " Look")
        self.generate_btn.configure(state="normal")
        self.status_var.set(f"Loaded: {Path(path).name}")

    def on_generate(self):
        if not self.image_path:
            return
        self.generate_btn.configure(state="disabled")
        self.status_var.set("Analyzing colors…")
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        try:
            preset_name = self.name_var.get().strip() or Path(self.image_path).stem + " Look"
            look = analyze_image(self.image_path, preset_name=preset_name)
        except Exception as exc:
            traceback.print_exc()
            self.root.after(0, lambda: self._on_error(exc))
            return
        self.root.after(0, lambda: self._on_analyzed(look))

    def _on_error(self, exc: Exception):
        self.generate_btn.configure(state="normal")
        self.status_var.set("Something went wrong.")
        messagebox.showerror("Analysis failed", str(exc))

    def _on_analyzed(self, look):
        self.generate_btn.configure(state="normal")
        default_name = Path(self.image_path).stem + "_look.xmp"
        out_path = filedialog.asksaveasfilename(
            title="Save Lightroom preset as…",
            defaultextension=".xmp",
            initialfile=default_name,
            filetypes=[("Lightroom preset (.xmp)", "*.xmp")],
        )
        if not out_path:
            self.status_var.set("Canceled.")
            return
        try:
            save_xmp(look, out_path)
        except Exception as exc:
            messagebox.showerror("Couldn't save file", str(exc))
            return
        self.status_var.set(f"Saved: {Path(out_path).name}")
        if messagebox.askyesno("Preset saved", f"Saved to:\n{out_path}\n\nShow it in your file browser?"):
            _open_in_file_manager(out_path)


def main():
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
