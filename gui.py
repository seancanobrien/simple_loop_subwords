"""
computing_project_gui.py

A tkinter GUI for computing_project_module.py.
Place this file in the same directory as computing_project_module.py and run it directly.

    python computing_project_gui.py

Two tabs:
  - Count / Collect  : wraps count_realisable / collect_realisable
  - Check Subword    : wraps check_subword

Requires: Python 3.12+ (for the `type` alias syntax used in the module), tkinter (stdlib).
"""

import csv
import os
import sys
import threading
import time
from math import log10
from tkinter import (
    BooleanVar, Label, StringVar, Tk, Toplevel,
    filedialog, messagebox, scrolledtext,
)
from tkinter import ttk

# ── locate the module ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import computing_project_module as cpm


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_ints(raw: str, name: str = "input") -> list[int]:
    """
    Parse a comma-separated string of integers, e.g. '-1, 2, 3' -> [-1, 2, 3].
    Raises ValueError with a clear message on bad input.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError(f"{name} must contain at least one integer.")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            raise ValueError(f"Cannot parse {name} entry: {p!r}")
    return result


# ── main application ──────────────────────────────────────────────────────────

class App(Tk):
    """Two-tab GUI: Count/Collect and Check Subword."""

    # ── construction ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__()
        self.title("Realisability Checker")
        self.resizable(False, False)
        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        BG    = "#0f0f12"
        PANEL = "#1a1a22"
        ACC   = "#7c6af7"
        FG    = "#e8e6f0"
        FGDIM = "#888"

        self.configure(bg=BG)

        style.configure("TFrame",      background=BG)
        style.configure("TLabel",      background=BG,    foreground=FG,    font=("Georgia", 10))
        style.configure("Dim.TLabel",  background=BG,    foreground=FGDIM, font=("Georgia", 9, "italic"))
        style.configure("Head.TLabel", background=BG,    foreground=FG,    font=("Georgia", 15, "bold"))

        style.configure(
            "TLabelframe",
            background=BG, foreground=ACC,
            bordercolor="#2e2e40", relief="flat",
        )
        style.configure("TLabelframe.Label", background=BG, foreground=ACC, font=("Georgia", 10, "bold"))

        style.configure(
            "TCheckbutton",
            background=BG, foreground=FG, font=("Georgia", 10), indicatorcolor=PANEL,
        )
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", FG)])

        style.configure(
            "TEntry",
            fieldbackground=PANEL, foreground=FG,
            insertcolor=FG, font=("Courier New", 10),
            borderwidth=1, relief="flat",
        )

        style.configure(
            "Accent.TButton",
            background=ACC, foreground="#fff",
            font=("Georgia", 11, "bold"), relief="flat", padding=(18, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#9a8cff"), ("disabled", "#333344")],
            foreground=[("disabled", "#666")],
        )

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=PANEL, foreground=FGDIM,
            font=("Georgia", 10), padding=(14, 6),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", FG)],
        )

        self._bg    = BG
        self._panel = PANEL
        self._acc   = ACC
        self._fg    = FG
        self._fgdim = FGDIM

    # ── top-level layout ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.grid(row=0, column=0, sticky="nsew")

        ttk.Label(root, text="Realisability Checker", style="Head.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 14)
        )

        nb = ttk.Notebook(root)
        nb.grid(row=1, column=0, sticky="nsew")

        tab1 = ttk.Frame(nb, padding=(0, 12, 0, 0))
        tab2 = ttk.Frame(nb, padding=(0, 12, 0, 0))
        tab3 = ttk.Frame(nb, padding=(0, 12, 0, 0))
        nb.add(tab1, text="  Count / Collect  ")
        nb.add(tab2, text="  Check Subword  ")
        nb.add(tab3, text="  Minimal Invalid  ")

        self._build_tab_count(tab1)
        self._build_tab_check(tab2)
        self._build_tab_minimal(tab3)

    # ── Tab 1: Count / Collect ────────────────────────────────────────────────

    def _build_tab_count(self, root: ttk.Frame) -> None:

        # Options
        opt = ttk.LabelFrame(root, text="Options", padding=(14, 10))
        opt.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self._var_mp = BooleanVar(value=cpm.USE_MULTIPROCESSING)
        self._var_ip = BooleanVar(value=cpm.IGNORE_POWERS)
        self._var_po = BooleanVar(value=cpm.PRODUCE_OUTPUT)

        ttk.Checkbutton(opt, text="Use Multiprocessing",  variable=self._var_mp).grid(
            row=0, column=0, sticky="w", padx=(0, 24), pady=2)
        ttk.Checkbutton(opt, text="Ignore Powers",        variable=self._var_ip).grid(
            row=0, column=1, sticky="w", padx=(0, 24), pady=2)
        ttk.Checkbutton(opt, text="Produce Output (CSV)", variable=self._var_po,
                        command=self._toggle_filename).grid(
            row=0, column=2, sticky="w", pady=2)

        self._fn_row = ttk.Frame(opt)
        self._fn_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(self._fn_row, text="Output file:").pack(side="left")
        self._fn_var = StringVar(value="out.csv")
        ttk.Entry(self._fn_row, textvariable=self._fn_var, width=32).pack(side="left", padx=8)
        ttk.Button(self._fn_row, text="Browse…", command=self._browse).pack(side="left")
        if not self._var_po.get():
            self._fn_row.grid_remove()

        # Parameters
        prm = ttk.LabelFrame(root, text="Parameters", padding=(14, 10))
        prm.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        labels   = ["Rank:", "Length:", "Prefix:"]
        defaults = ["5", "6", "1"]
        widths   = [8, 8, 32]
        hints    = [
            "Positive integer  —  number of punctures",
            "Positive integer  —  total word length  (>= len(prefix))",
            "Comma-separated signed integers  —  e.g.  1   or   -1, 2   or   1, -3, 2",
        ]
        self._vars = []
        for i, (lbl, dflt, w, hint) in enumerate(zip(labels, defaults, widths, hints)):
            ttk.Label(prm, text=lbl).grid(row=i*2,   column=0, sticky="e", padx=(0, 10), pady=(6, 0))
            v = StringVar(value=dflt)
            self._vars.append(v)
            ttk.Entry(prm, textvariable=v, width=w).grid(row=i*2, column=1, sticky="w", pady=(6, 0))
            ttk.Label(prm, text=hint, style="Dim.TLabel").grid(
                row=i*2+1, column=1, sticky="w", pady=(0, 2))

        self._rank_var, self._length_var, self._prefix_var = self._vars

        # Run button
        self._run_btn = ttk.Button(root, text="Run", style="Accent.TButton", command=self._run)
        self._run_btn.grid(row=2, column=0, columnspan=2, pady=(0, 16))

        # Output log
        out = ttk.LabelFrame(root, text="Output", padding=(14, 10))
        out.grid(row=3, column=0, columnspan=2, sticky="nsew")

        self._log_box = scrolledtext.ScrolledText(
            out, width=62, height=12, font=("Courier New", 10),
            state="disabled", background="#0a0a10", foreground="#c8e6c9",
            insertbackground="white", borderwidth=0, highlightthickness=0,
        )
        self._log_box.pack(fill="both", expand=True)

    # ── Tab 2: Check Subword ──────────────────────────────────────────────────

    def _build_tab_check(self, root: ttk.Frame) -> None:

        # Options
        opt = ttk.LabelFrame(root, text="Options", padding=(14, 10))
        opt.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self._chk_var_ip = BooleanVar(value=cpm.IGNORE_POWERS)
        ttk.Checkbutton(opt, text="Ignore Powers", variable=self._chk_var_ip).grid(
            row=0, column=0, sticky="w", padx=(0, 24), pady=2)

        self._chk_var_is = BooleanVar(value=cpm.IGNORE_SIGNS)
        ttk.Checkbutton(opt, text="Ignore Signs", variable=self._chk_var_is).grid(
            row=0, column=1, sticky="w", pady=2)

        # Parameters
        prm = ttk.LabelFrame(root, text="Parameters", padding=(14, 10))
        prm.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        ttk.Label(prm, text="Rank:").grid(row=0, column=0, sticky="e", padx=(0, 10), pady=(6, 0))
        self._chk_rank_var = StringVar(value="5")
        ttk.Entry(prm, textvariable=self._chk_rank_var, width=8).grid(row=0, column=1, sticky="w", pady=(6, 0))
        ttk.Label(prm, text="Positive integer  —  number of punctures", style="Dim.TLabel").grid(
            row=1, column=1, sticky="w", pady=(0, 2))

        ttk.Label(prm, text="Subword:").grid(row=2, column=0, sticky="e", padx=(0, 10), pady=(6, 0))
        self._chk_subword_var = StringVar(value="1, 2, -1")
        ttk.Entry(prm, textvariable=self._chk_subword_var, width=40).grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(prm, text="Comma-separated signed integers  —  e.g.  1, 2, -3", style="Dim.TLabel").grid(
            row=3, column=1, sticky="w", pady=(0, 2))

        # Check button
        self._chk_btn = ttk.Button(root, text="Check", style="Accent.TButton", command=self._run_check)
        self._chk_btn.grid(row=2, column=0, columnspan=2, pady=(0, 16))

        # Result panel
        res = ttk.LabelFrame(root, text="Result", padding=(14, 14))
        res.grid(row=3, column=0, columnspan=2, sticky="ew")
        res.columnconfigure(0, weight=1)

        # Large verdict label, updated green/red after each run
        self._chk_verdict = Label(
            res, text="—",
            font=("Georgia", 22, "bold"),
            background=self._bg, foreground=self._fgdim,
            anchor="center",
        )
        self._chk_verdict.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # Detail line: echoed subword + timing
        self._chk_detail = Label(
            res, text="",
            font=("Courier New", 10),
            background=self._bg, foreground=self._fgdim,
            anchor="center",
        )
        self._chk_detail.grid(row=1, column=0, sticky="ew")

    # ── Tab 1 callbacks ───────────────────────────────────────────────────────

    def _toggle_filename(self) -> None:
        if self._var_po.get():
            self._fn_row.grid()
        else:
            self._fn_row.grid_remove()

    def _browse(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._fn_var.set(path)

    def _run(self) -> None:
        try:
            rank   = int(self._rank_var.get().strip())
            length = int(self._length_var.get().strip())
            prefix = _parse_ints(self._prefix_var.get(), "prefix")
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        cpm.USE_MULTIPROCESSING = self._var_mp.get()
        cpm.IGNORE_POWERS       = self._var_ip.get()
        cpm.PRODUCE_OUTPUT      = self._var_po.get()

        produce_output = self._var_po.get()
        filename = self._fn_var.get().strip() if produce_output else None

        self._clear_log()
        sep = "─" * 54
        self._log(f"  Rank    = {rank}")
        self._log(f"  Length  = {length}")
        self._log(f"  Prefix  = {prefix}")
        self._log(f"  MP      = {'ON' if cpm.USE_MULTIPROCESSING else 'OFF'}")
        self._log(f"  Powers  = {'ignored' if cpm.IGNORE_POWERS else 'allowed'}")
        self._log(f"  Output  = {'-> ' + filename if produce_output else 'count only'}")
        self._log(sep)
        self._log("  Running...")
        self._run_btn.configure(state="disabled")

        def _worker() -> None:
            try:
                t0 = time.perf_counter()
                if produce_output:
                    true_count  = cpm.collect_realisable(rank, length, filename, prefix)
                    elapsed     = time.perf_counter() - t0
                    bf          = (rank * 2 - 2) if cpm.IGNORE_POWERS else (rank * 2 - 1)
                    total_count = bf ** (length - len(prefix))
                else:
                    true_count, total_count = cpm.count_realisable(rank, length, prefix)
                    elapsed = time.perf_counter() - t0
                self.after(0, _show, true_count, total_count, elapsed)
            except Exception as exc:
                self.after(0, _err, exc)

        def _show(true_count: int, total_count: int, elapsed: float) -> None:
            prop = (
                f"10^{log10(true_count / total_count):.4f}"
                if true_count > 0 else "0"
            )
            self._log(f"  Total words     : {total_count:,}")
            self._log(f"  True count      : {true_count:,}")
            self._log(f"  False count     : {total_count - true_count:,}")
            self._log(f"  Proportion True : {prop}")
            self._log(f"  Time            : {elapsed:.3f}s")
            if filename:
                self._log(f"  Written to      : {filename}")
            self._log(sep)
            self._run_btn.configure(state="normal")
            if filename:
                self._open_results_window(filename, rank, length, prefix)

        def _err(exc: Exception) -> None:
            self._log(f"  ERROR: {exc}")
            self._log(sep)
            self._run_btn.configure(state="normal")
            messagebox.showerror("Runtime Error", str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Tab 2 callback ────────────────────────────────────────────────────────

    def _run_check(self) -> None:
        try:
            rank    = int(self._chk_rank_var.get().strip())
            subword = _parse_ints(self._chk_subword_var.get(), "subword")
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        cpm.IGNORE_POWERS = self._chk_var_ip.get()
        cpm.IGNORE_SIGNS  = self._chk_var_is.get()

        self._chk_verdict.configure(text="...", foreground=self._fgdim)
        self._chk_detail.configure(text="")
        self._chk_btn.configure(state="disabled")

        def _worker() -> None:
            try:
                t0             = time.perf_counter()
                result, max_sub = cpm.check_subword(rank, subword)
                elapsed        = time.perf_counter() - t0
                self.after(0, _show, result, max_sub, elapsed)
            except Exception as exc:
                self.after(0, _err, exc)

        def _show(result: bool, max_sub: list[int], elapsed: float) -> None:
            word_str = ", ".join(str(x) for x in max_sub)
            if result:
                self._chk_verdict.configure(text="✓  Realisable",     foreground="#66bb6a")
                self._chk_detail.configure(
                    text=f"rank={rank}    [{word_str}]    {elapsed*1000:.2f} ms"
                )
            else:
                self._chk_verdict.configure(text="✗  Not realisable", foreground="#ef5350")
                prefix_str = ", ".join(str(x) for x in max_sub)
                self._chk_detail.configure(
                    text=f"rank={rank}    [{word_str}]    {elapsed*1000:.2f} ms\n"
                         f"longest valid prefix ({len(max_sub)}):  [{prefix_str}]"
                )
            self._chk_btn.configure(state="normal")

        def _err(exc: Exception) -> None:
            self._chk_verdict.configure(text="Error", foreground="#ef5350")
            self._chk_detail.configure(text=str(exc))
            self._chk_btn.configure(state="normal")
            messagebox.showerror("Runtime Error", str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Tab 3: Minimal Invalid ───────────────────────────────────────────────

    def _build_tab_minimal(self, root: ttk.Frame) -> None:

        # Parameters
        prm = ttk.LabelFrame(root, text="Parameters", padding=(14, 10))
        prm.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        ttk.Label(prm, text="Rank:").grid(row=0, column=0, sticky="e", padx=(0, 10), pady=(6, 0))
        self._min_rank_var = StringVar(value="5")
        ttk.Entry(prm, textvariable=self._min_rank_var, width=8).grid(row=0, column=1, sticky="w", pady=(6, 0))
        ttk.Label(prm, text="Positive integer  —  number of punctures", style="Dim.TLabel").grid(
            row=1, column=1, sticky="w", pady=(0, 2))

        ttk.Label(prm, text="Length:").grid(row=2, column=0, sticky="e", padx=(0, 10), pady=(6, 0))
        self._min_length_var = StringVar(value="4")
        ttk.Entry(prm, textvariable=self._min_length_var, width=8).grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(prm, text="Positive integer  —  length of words to search", style="Dim.TLabel").grid(
            row=3, column=1, sticky="w", pady=(0, 2))

        # Run button
        self._min_btn = ttk.Button(root, text="Find", style="Accent.TButton", command=self._run_minimal)
        self._min_btn.grid(row=1, column=0, columnspan=2, pady=(0, 16))

        # Output log
        out = ttk.LabelFrame(root, text="Output", padding=(14, 10))
        out.grid(row=2, column=0, columnspan=2, sticky="nsew")

        self._min_log_box = scrolledtext.ScrolledText(
            out, width=62, height=12, font=("Courier New", 10),
            state="disabled", background="#0a0a10", foreground="#c8e6c9",
            insertbackground="white", borderwidth=0, highlightthickness=0,
        )
        self._min_log_box.pack(fill="both", expand=True)

    def _run_minimal(self) -> None:
        try:
            rank   = int(self._min_rank_var.get().strip())
            length = int(self._min_length_var.get().strip())
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        self._min_log_clear()
        sep = "─" * 54
        self._min_log(f"  Rank    = {rank}")
        self._min_log(f"  Length  = {length}")
        self._min_log(sep)
        self._min_log("  Running...")
        self._min_btn.configure(state="disabled")

        def _worker() -> None:
            try:
                t0    = time.perf_counter()
                words = cpm.find_minimal_invalid(rank, length)
                elapsed = time.perf_counter() - t0
                self.after(0, _show, words, elapsed)
            except Exception as exc:
                self.after(0, _err, exc)

        def _show(words: list, elapsed: float) -> None:
            self._min_log(f"  Found           : {len(words):,} minimal invalid words")
            self._min_log(f"  Time            : {elapsed:.3f}s")
            self._min_log(sep)
            self._min_btn.configure(state="normal")
            if words:
                self._open_words_window(
                    words=[[str(x) for x in w] for w in words],
                    title=f"Minimal invalid  —  rank={rank}, length={length}",
                    header=f"Minimal invalid words   (rank={rank}, length={length})",
                    status=f"{len(words):,} minimal invalid words  ·  rank={rank}, length={length}",
                )

        def _err(exc: Exception) -> None:
            self._min_log(f"  ERROR: {exc}")
            self._min_log(sep)
            self._min_btn.configure(state="normal")
            messagebox.showerror("Runtime Error", str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _min_log(self, text: str) -> None:
        self._min_log_box.configure(state="normal")
        self._min_log_box.insert("end", text + "\n")
        self._min_log_box.see("end")
        self._min_log_box.configure(state="disabled")

    def _min_log_clear(self) -> None:
        self._min_log_box.configure(state="normal")
        self._min_log_box.delete("1.0", "end")
        self._min_log_box.configure(state="disabled")

    # ── results window ────────────────────────────────────────────────────────

    _MAX_DISPLAY_ROWS = 50_000

    def _open_results_window(
        self, filename: str, rank: int, length: int, prefix: list[int]
    ) -> None:
        """Read a CSV of realisable words and open a display window."""
        try:
            with open(filename, newline="") as f:
                rows = [row for row in csv.reader(f) if row]
        except OSError as exc:
            messagebox.showerror("Cannot open file", str(exc))
            return

        total_rows = len(rows)
        truncated  = total_rows > self._MAX_DISPLAY_ROWS
        status_parts = [f"{total_rows:,} realisable words"]
        if truncated:
            status_parts.append(
                f"  ·  showing first {self._MAX_DISPLAY_ROWS:,}"
                f"  ({total_rows - self._MAX_DISPLAY_ROWS:,} not displayed)"
            )
        status_parts.append(f"  ·  {filename}")

        self._open_words_window(
            words=rows[:self._MAX_DISPLAY_ROWS],
            title=f"Results  —  rank={rank}, length={length}, prefix={prefix}",
            header=f"Realisable words   (rank={rank}, length={length}, prefix={prefix})",
            status="".join(status_parts),
        )

    def _open_words_window(
        self, words: list[list[str]], title: str, header: str, status: str
    ) -> None:
        """
        Open a Toplevel displaying *words* as a scrollable two-column list.
        Each row shows a right-aligned index and a comma-separated word.
        *words* is a list of rows, where each row is a list of strings.
        """
        from tkinter import Text, Scrollbar, VERTICAL

        total_rows = len(words)

        win = Toplevel(self)
        win.title(title)
        win.configure(bg=self._bg)
        win.geometry("560x500")
        win.minsize(360, 200)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)

        # Header
        hdr = ttk.Frame(win, padding=(14, 10, 14, 6))
        hdr.grid(row=0, column=0, sticky="ew")
        ttk.Label(hdr, text=header, style="Head.TLabel", font=("Georgia", 12, "bold")).pack(side="left")

        # Text area + scrollbar
        txt_frame = ttk.Frame(win, padding=(14, 0, 14, 0))
        txt_frame.grid(row=1, column=0, sticky="nsew")
        txt_frame.columnconfigure(0, weight=1)
        txt_frame.rowconfigure(0, weight=1)

        vsb = Scrollbar(txt_frame, orient=VERTICAL)
        txt = Text(
            txt_frame,
            font=("Courier New", 10),
            background="#0a0a10", foreground="#c8e6c9",
            insertbackground="white",
            selectbackground=self._acc, selectforeground="#ffffff",
            borderwidth=0, highlightthickness=0,
            wrap="none", state="normal",
            yscrollcommand=vsb.set,
        )
        vsb.configure(command=txt.yview)
        txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        idx_width = len(str(total_rows))
        lines = [
            f"{idx:>{idx_width}}    {', '.join(row)}"
            for idx, row in enumerate(words, 1)
        ]
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")

        # Status bar
        ttk.Label(
            win, text=status,
            style="Dim.TLabel", padding=(14, 4, 14, 8),
        ).grid(row=2, column=0, sticky="ew")

    # ── log helpers ───────────────────────────────────────────────────────────

    def _log(self, text: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()