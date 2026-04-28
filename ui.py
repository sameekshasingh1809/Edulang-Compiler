"""
ui.py — EduLang Compiler IDE  v3
====================================
Editor improvements:
  • Live error squiggles as you type (red wavy underline on bad lines)
  • Inline error panel below editor — shows plain-English hint instantly
  • Bracket / quote matching highlight
  • Autocomplete popup for keywords and declared variables  (Tab / Enter)
  • Smart auto-close for  (  and  "
  • Current-line highlight (soft glow)
  • Error gutter icons  ❌  next to line numbers
  • Debounced live analysis (runs 400 ms after you stop typing)
  • Theme toggle  Dark / Light  in toolbar
  • All v2 features retained
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import time
import threading

from lexer        import Lexer, LexerError
from parser       import Parser, ParseError
from semantic     import SemanticAnalyzer, SemanticError
from intermediate import TACGenerator
from optimizer    import optimize
from codegen      import CodeGenerator
from main         import format_ast, format_tokens
from errors       import friendly


# ══════════════════════════════════════════════════════════════
#  Themes
# ══════════════════════════════════════════════════════════════

THEMES = {
    "dark": {
        "BG":        "#1e1e2e",
        "BG2":       "#181825",
        "PANEL":     "#313244",
        "ACCENT":    "#cba6f7",
        "ACCENT2":   "#89b4fa",
        "GREEN":     "#a6e3a1",
        "RED":       "#f38ba8",
        "YELLOW":    "#f9e2af",
        "TEAL":      "#94e2d5",
        "PINK":      "#f5c2e7",
        "ORANGE":    "#fab387",
        "TEXT":      "#cdd6f4",
        "DIM":       "#585b70",
        "BORDER":    "#45475a",
        "ERR_BG":    "#3d1a1a",
        "CUR_LINE":  "#25253a",
        "MATCH_BG":  "#3d3d5c",
        "SQUIGGLE":  "#f38ba8",
        "AC_BG":     "#2a2a3d",
        "AC_SEL":    "#45475a",
        "GUTTER_ERR":"#f38ba8",
        "WARN_BG":   "#f9e2af",
    },
    "light": {
        "BG":        "#eff1f5",
        "BG2":       "#e6e9ef",
        "PANEL":     "#ccd0da",
        "ACCENT":    "#7287fd",
        "ACCENT2":   "#1e66f5",
        "GREEN":     "#40a02b",
        "RED":       "#d20f39",
        "YELLOW":    "#df8e1d",
        "TEAL":      "#179299",
        "PINK":      "#ea76cb",
        "ORANGE":    "#fe640b",
        "TEXT":      "#4c4f69",
        "DIM":       "#9ca0b0",
        "BORDER":    "#bcc0cc",
        "ERR_BG":    "#fde8e8",
        "CUR_LINE":  "#dce0ea",
        "MATCH_BG":  "#c8d0e7",
        "SQUIGGLE":  "#d20f39",
        "AC_BG":     "#e6e9ef",
        "AC_SEL":    "#ccd0da",
        "GUTTER_ERR":"#d20f39",
        "WARN_BG":   "#fef3c7",
    },
}

_theme_name = "dark"
_theme      = THEMES[_theme_name]

def C(key):       return _theme[key]
def MONO(sz=11):  return ("Courier New", sz)
def UI(sz=10):    return ("Segoe UI", sz)
def BOLD(sz=11):  return ("Segoe UI", sz, "bold")

# All EduLang keywords for autocomplete
KEYWORDS = [
    "int", "float", "str", "bool",
    "true", "false",
    "input", "print",
    "if", "else",
    "loop", "till",
    "and", "or", "not",
]


# ══════════════════════════════════════════════════════════════
#  Sample programs
# ══════════════════════════════════════════════════════════════

SAMPLES = {
    "Hello World": """\
# My first EduLang program
str greeting
greeting = "Hello, World!"
print greeting
""",
    "Int loop & sum": """\
# Sum of integers 0..4 using a loop
int i
int sum
sum = 0
loop i = 0 till i < 5:
    sum = sum + i
    i = i + 1
print "Sum =", sum
""",
    "Float arithmetic": """\
# Float variables and all arithmetic operators
float a
float b
a = 7.5
b = 2.0
print "a + b =", a + b
print "a - b =", a - b
print "a * b =", a * b
print "a / b  =", a / b
print "a ** b =", a ** b
print "a // b =", a // b
print "a % b  =", a % b
""",
    "String concat": """\
# String declaration, assignment, and concatenation
str first
str last
str full
first = "Ada"
last  = " Lovelace"
full  = first + last
print "Full name:", full
""",
    "Bool & logical ops": """\
# Boolean variables and and / or / not
bool hot
bool raining
hot     = true
raining = false

if hot and not raining:
    print "Great weather!"
else:
    print "Stay inside."

int x
x = 42
if x > 0 and x < 100:
    print "x is in range"
""",
    "If / Else": """\
# Grade checker using if-else
int score
score = 78

if score >= 90:
    print "Grade: A"
if score >= 80:
    if score < 90:
        print "Grade: B"
if score >= 70:
    if score < 80:
        print "Grade: C"
""",
    "Fibonacci": """\
# First 10 Fibonacci numbers
int a
int b
int tmp
int i
a = 0
b = 1
loop i = 0 till i < 10:
    print a
    tmp = a + b
    a   = b
    b   = tmp
    i   = i + 1
""",
    "Power & Modulo": """\
# Demonstrate ** % // !=
int a
int b
a = 17
b = 5
print "17 % 5  =", a % b
print "2 ** 10 =", 2 ** 10
print "17 // 5 =", a // b
if a != b:
    print "a and b are different"
""",
    "User input": """\
# Read two numbers and print their sum
int x
int y
input x
input y
int result
result = x + y
print "Sum =", result
""",
    "Factorial": """\
# Factorial of 6 using a loop
int n
int fact
int i
n    = 6
fact = 1
loop i = 1 till i < 7:
    fact = fact * i
    i    = i + 1
print "6! =", fact
""",
}

WELCOME_TEXT = """\
# ╔══════════════════════════════════════════════╗
# ║         Welcome to  EduLang IDE  v3          ║
# ╚══════════════════════════════════════════════╝
#
#  Errors are shown as you type — no need to Run first!
#  Red squiggles = problem line.  Panel below = what's wrong.
#
#  Quick start:
#    • Pick a sample from the  Samples  menu
#    • Or delete this text and write your own code
#    • Press  ▶ Run  (or F5)  to compile and run
#
#  Keyboard shortcuts:
#    F5          Run
#    Tab         Accept autocomplete
#    Ctrl+S      Save      Ctrl+O  Open
#    Ctrl+N      New       Ctrl+H  Find / Replace
#    Ctrl++/-    Zoom in / out
"""

# ── Regex for syntax highlighting ────────────────────────────
_PAT_TYPE = re.compile(r'\b(int|float|str|bool)\b')
_PAT_KW   = re.compile(r'\b(true|false|input|print|if|else|loop|till|and|or|not)\b')
_PAT_NUM  = re.compile(r'\b\d+\.?\d*\b')
_PAT_STR  = re.compile(r'"[^"\n]*"')
_PAT_CMT  = re.compile(r'#[^\n]*')
_PAT_IDENT= re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')


# ══════════════════════════════════════════════════════════════
#  Input popup
# ══════════════════════════════════════════════════════════════

class AskValue(tk.Toplevel):
    def __init__(self, parent, var_name: str):
        super().__init__(parent)
        self.value = "0"
        self.title("Program Input")
        self.configure(bg=C("BG2"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Frame(self, bg=C("ACCENT"), height=3).pack(fill="x")
        tk.Label(self, text="📥  Program Input",
                 bg=C("BG2"), fg=C("ACCENT"), font=BOLD(12),
                 padx=28, pady=14).pack()
        tk.Label(self, text=f"Enter a value for  '{var_name}'",
                 bg=C("BG2"), fg=C("TEXT"), font=UI(10), padx=28).pack()
        tk.Label(self, text="Accepts integer, float, or text",
                 bg=C("BG2"), fg=C("DIM"), font=UI(9), padx=28, pady=4).pack()

        ef = tk.Frame(self, bg=C("PANEL"), padx=2, pady=2)
        ef.pack(padx=28, pady=8, fill="x")
        self._e = tk.Entry(ef, font=MONO(13), bg=C("BG"), fg=C("TEXT"),
                           insertbackground=C("ACCENT"), relief="flat",
                           bd=6, justify="center")
        self._e.pack(fill="x")
        self._e.insert(0, "0")
        self._e.select_range(0, "end")
        self._e.focus_set()
        self._e.bind("<Return>", lambda _: self._ok())
        self._e.bind("<Escape>", lambda _: self.destroy())

        tk.Button(self, text="  Confirm  ", command=self._ok,
                  bg=C("ACCENT"), fg=C("BG2"), font=BOLD(10),
                  relief="flat", bd=0, padx=20, pady=8,
                  cursor="hand2").pack(pady=12)

        self.update_idletasks()
        x = parent.winfo_rootx() + parent.winfo_width()  // 2 - self.winfo_width()  // 2
        y = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")
        parent.wait_window(self)

    def _ok(self):
        self.value = self._e.get().strip()
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  Find / Replace dialog
# ══════════════════════════════════════════════════════════════

class FindReplace(tk.Toplevel):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self._ed = editor
        self.title("Find / Replace")
        self.configure(bg=C("BG2"))
        self.resizable(False, False)
        self.transient(parent)

        def lbl_entry(text, row):
            tk.Label(self, text=text, bg=C("BG2"), fg=C("DIM"),
                     font=UI(9), width=10, anchor="e").grid(row=row, column=0, padx=8, pady=6)
            e = tk.Entry(self, font=MONO(10), bg=C("PANEL"), fg=C("TEXT"),
                         insertbackground=C("ACCENT"), relief="flat", bd=4, width=30)
            e.grid(row=row, column=1, columnspan=3, padx=8, pady=6)
            return e

        self._find_e    = lbl_entry("Find:",    0)
        self._replace_e = lbl_entry("Replace:", 1)

        for col, (text, cmd) in enumerate([
            ("Find Next",   self._find_next),
            ("Replace",     self._replace_one),
            ("Replace All", self._replace_all),
        ]):
            tk.Button(self, text=text, command=cmd,
                      bg=C("PANEL"), fg=C("TEXT"), font=UI(9),
                      relief="flat", padx=12, pady=4,
                      cursor="hand2").grid(row=2, column=col+1, padx=4, pady=10)

        self.bind("<Escape>", lambda _: self.destroy())

    def _find_next(self):
        needle = self._find_e.get()
        if not needle: return
        pos = self._ed.search(needle, self._ed.index("insert") + "+1c", stopindex="end")
        if not pos:
            pos = self._ed.search(needle, "1.0", stopindex="end")
        if pos:
            end = f"{pos}+{len(needle)}c"
            self._ed.tag_remove("sel", "1.0", "end")
            self._ed.tag_add("sel", pos, end)
            self._ed.mark_set("insert", end)
            self._ed.see(pos)

    def _replace_one(self):
        needle = self._find_e.get()
        repl   = self._replace_e.get()
        try:
            s = self._ed.index("sel.first")
            e = self._ed.index("sel.last")
            if self._ed.get(s, e) == needle:
                self._ed.delete(s, e); self._ed.insert(s, repl)
        except tk.TclError:
            pass
        self._find_next()

    def _replace_all(self):
        needle = self._find_e.get()
        repl   = self._replace_e.get()
        if not needle: return
        count = 0; start = "1.0"
        while True:
            pos = self._ed.search(needle, start, stopindex="end")
            if not pos: break
            end = f"{pos}+{len(needle)}c"
            self._ed.delete(pos, end); self._ed.insert(pos, repl)
            start = f"{pos}+{len(repl)}c"; count += 1
        messagebox.showinfo("Replace All", f"Replaced {count} occurrence(s).", parent=self)


# ══════════════════════════════════════════════════════════════
#  Autocomplete popup
# ══════════════════════════════════════════════════════════════

class Autocomplete(tk.Toplevel):
    """
    Floating listbox that appears just below the cursor with completions.
    Dismissed by Escape, accepted by Tab or Enter or click.
    """
    def __init__(self, parent, editor, items: list, prefix: str):
        super().__init__(parent)
        self.overrideredirect(True)          # no window decorations
        self.configure(bg=C("BORDER"))
        self._ed     = editor
        self._items  = items
        self._prefix = prefix
        self._selected = 0

        # Position just below the cursor
        try:
            bbox = editor.bbox("insert")
            if bbox:
                x = editor.winfo_rootx() + bbox[0]
                y = editor.winfo_rooty() + bbox[1] + bbox[3] + 2
                self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._lb = tk.Listbox(self, font=MONO(10),
                              bg=C("AC_BG"), fg=C("TEXT"),
                              selectbackground=C("AC_SEL"),
                              selectforeground=C("ACCENT"),
                              relief="flat", bd=1,
                              highlightthickness=1,
                              highlightcolor=C("ACCENT"),
                              height=min(len(items), 8),
                              width=max(len(s) for s in items) + 4)
        self._lb.pack()
        for it in items:
            self._lb.insert("end", "  " + it)
        self._lb.selection_set(0)
        self._lb.bind("<ButtonRelease-1>", lambda _: self._accept())

        # Let the editor keep focus but intercept Tab/Enter/Escape/arrows
        editor.bind("<Tab>",    self._on_tab,    add=True)
        editor.bind("<Return>", self._on_return, add=True)
        editor.bind("<Escape>", self._on_escape, add=True)
        editor.bind("<Down>",   self._on_down,   add=True)
        editor.bind("<Up>",     self._on_up,     add=True)

    def _on_tab(self, _):
        self._accept(); return "break"

    def _on_return(self, _):
        # Only intercept Enter for autocomplete if list is showing
        self._accept(); return "break"

    def _on_escape(self, _):
        self.dismiss()

    def _on_down(self, _):
        n = len(self._items)
        self._selected = min(self._selected + 1, n - 1)
        self._lb.selection_clear(0, "end")
        self._lb.selection_set(self._selected)
        self._lb.see(self._selected)
        return "break"

    def _on_up(self, _):
        self._selected = max(self._selected - 1, 0)
        self._lb.selection_clear(0, "end")
        self._lb.selection_set(self._selected)
        self._lb.see(self._selected)
        return "break"

    def _accept(self):
        word = self._items[self._selected]
        # Delete the prefix the user already typed
        pos  = self._ed.index("insert")
        self._ed.delete(f"{pos}-{len(self._prefix)}c", pos)
        self._ed.insert("insert", word)
        self.dismiss()

    def dismiss(self):
        for seq in ("<Tab>", "<Return>", "<Escape>", "<Down>", "<Up>"):
            try: self._ed.unbind(seq)
            except Exception: pass
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  Main IDE
# ══════════════════════════════════════════════════════════════

class IDE(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("EduLang Compiler IDE")
        self.configure(bg=C("BG"))
        self.geometry("1440x900")
        self.minsize(960, 660)
        self._font_size    = 11
        self._ac_popup     = None       # current autocomplete popup
        self._lint_after   = None       # pending after() handle for debounce
        self._lint_errors  = []         # list of (line_no, message) from live lint
        self._build()
        self._shortcuts()
        # Bind editor Re-indent on Return separately so autocomplete Return works
        self._ed.bind("<Return>", self._auto_indent)

    # ─── Build ────────────────────────────────────────────────

    def _build(self):
        self._menu()
        self._header()
        self._body()
        self._statusbar()

    # ── Menu ──────────────────────────────────────────────────

    def _menu(self):
        mb = tk.Menu(self, bg=C("BG2"), fg=C("TEXT"), relief="flat",
                     activebackground=C("ACCENT"), activeforeground=C("BG2"))
        self.config(menu=mb)

        def cascade(parent, label, items):
            m = tk.Menu(parent, tearoff=0, bg=C("BG2"), fg=C("TEXT"),
                        activebackground=C("ACCENT"), activeforeground=C("BG2"))
            parent.add_cascade(label=label, menu=m)
            for it in items:
                if it == "---": m.add_separator()
                else:           m.add_command(label=it[0], command=it[1])
            return m

        cascade(mb, "File", [
            ("New              Ctrl+N", self._new),
            ("Open…            Ctrl+O", self._open),
            ("Save…            Ctrl+S", self._save),
            "---",
            ("Exit",                    self.quit),
        ])
        cascade(mb, "Edit", [
            ("Undo             Ctrl+Z", lambda: self._ed.edit_undo()),
            ("Redo             Ctrl+Y", lambda: self._ed.edit_redo()),
            "---",
            ("Find / Replace   Ctrl+H", self._find_replace),
            "---",
            ("Zoom In          Ctrl++", self._zoom_in),
            ("Zoom Out         Ctrl+-", self._zoom_out),
        ])
        cascade(mb, "Run", [
            ("▶  Run     F5",  self._run),
            ("Clear output",   self._clear_output),
        ])
        sm = tk.Menu(mb, tearoff=0, bg=C("BG2"), fg=C("TEXT"),
                     activebackground=C("ACCENT"), activeforeground=C("BG2"))
        mb.add_cascade(label="Samples", menu=sm)
        for k in SAMPLES:
            sm.add_command(label=k, command=lambda k=k: self._load_sample(k))
        cascade(mb, "View", [
            ("Toggle Dark/Light Theme", self._toggle_theme),
        ])
        cascade(mb, "Help", [
            ("EduLang Reference", self._show_ref),
            ("About",             self._show_about),
        ])

    # ── Header / toolbar ──────────────────────────────────────

    def _header(self):
        bar = tk.Frame(self, bg=C("BG2"), height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)

        # Logo
        tk.Label(bar, text="◆ EduLang IDE", bg=C("BG2"),
                 fg=C("ACCENT"), font=BOLD(13), padx=16).pack(side="left")
        tk.Frame(bar, bg=C("BORDER"), width=1).pack(side="left", fill="y", pady=10)

        def btn(text, cmd, accent=False):
            b = tk.Button(bar, text=text, command=cmd,
                          bg=C("ACCENT") if accent else C("PANEL"),
                          fg=C("BG2")    if accent else C("TEXT"),
                          font=UI(10), relief="flat", bd=0,
                          padx=14, pady=6, cursor="hand2",
                          activebackground=C("ACCENT2"),
                          activeforeground=C("BG2"))
            b.pack(side="left", padx=3, pady=10)
            return b

        self._run_btn = btn("▶  Run  F5", self._run, accent=True)
        btn("New",          self._new)
        btn("Open",         self._open)
        btn("Save",         self._save)
        btn("Find/Replace", self._find_replace)
        btn("Zoom +",       self._zoom_in)
        btn("Zoom -",       self._zoom_out)
        btn("🌓 Theme",     self._toggle_theme)

        tk.Frame(bar, bg=C("BORDER"), width=1).pack(side="right", fill="y", pady=10)
        self._svar = tk.StringVar(value="")
        om = tk.OptionMenu(bar, self._svar, *SAMPLES.keys(),
                           command=self._load_sample)
        om.config(bg=C("PANEL"), fg=C("TEXT"), font=UI(10),
                  relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
                  highlightthickness=0,
                  activebackground=C("ACCENT"), activeforeground=C("BG2"),
                  indicatoron=0)
        om["menu"].config(bg=C("PANEL"), fg=C("TEXT"), font=UI(10),
                          activebackground=C("ACCENT"), activeforeground=C("BG2"))
        om.pack(side="right", padx=4)
        tk.Label(bar, text="📂 Samples:", bg=C("BG2"), fg=C("DIM"),
                 font=UI(9)).pack(side="right", padx=2)

    # ── Body (paned: editor | output) ─────────────────────────

    def _body(self):
        pw = tk.PanedWindow(self, orient="horizontal",
                            bg=C("BORDER"), sashwidth=4, sashpad=0)
        pw.pack(fill="both", expand=True)
        pw.add(self._editor_pane(pw), minsize=340, width=560)
        pw.add(self._output_pane(pw), minsize=380)

    # ── Editor pane ───────────────────────────────────────────

    def _editor_pane(self, parent):
        outer = tk.Frame(parent, bg=C("BG"))

        # ── Header strip
        hdr = tk.Frame(outer, bg=C("BG2"), height=34)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="  📝  Source Editor", bg=C("BG2"),
                 fg=C("ACCENT2"), font=BOLD(10), pady=7).pack(side="left")
        self._cur_lbl = tk.Label(hdr, text="Ln 1, Col 1",
                                 bg=C("BG2"), fg=C("DIM"), font=UI(9))
        self._cur_lbl.pack(side="right", padx=12)
        # Live lint indicator
        self._lint_lbl = tk.Label(hdr, text="", bg=C("BG2"),
                                  fg=C("RED"), font=UI(9))
        self._lint_lbl.pack(side="right", padx=4)

        # ── Editor + gutter
        body = tk.Frame(outer, bg=C("BG2"))
        body.pack(fill="both", expand=True)

        # Gutter (line numbers + error icons)
        self._ln = tk.Text(body, width=5, state="disabled",
                           bg=C("BG"), fg=C("DIM"), font=MONO(self._font_size),
                           relief="flat", bd=0, padx=4, pady=8, cursor="arrow")
        self._ln.pack(side="left", fill="y")
        tk.Frame(body, bg=C("BORDER"), width=1).pack(side="left", fill="y")

        # Scrollbars
        ys = tk.Scrollbar(body,  orient="vertical",
                          bg=C("PANEL"), troughcolor=C("BG2"), width=8)
        xs = tk.Scrollbar(outer, orient="horizontal",
                          bg=C("PANEL"), troughcolor=C("BG2"), width=8)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")

        # The editor text widget
        self._ed = tk.Text(body, bg=C("BG2"), fg=C("TEXT"),
                           insertbackground=C("ACCENT"),
                           selectbackground=C("PANEL"),
                           font=MONO(self._font_size),
                           relief="flat", bd=0, padx=12, pady=8,
                           undo=True, wrap="none",
                           yscrollcommand=self._sync_scroll,
                           xscrollcommand=xs.set,
                           tabs="28")
        ys.configure(command=self._scroll_both)
        xs.configure(command=self._ed.xview)
        self._ed.pack(side="left", fill="both", expand=True)

        # ── Tags
        self._ed.tag_configure("typ",        foreground=C("PINK"))
        self._ed.tag_configure("kw",         foreground=C("ACCENT"))
        self._ed.tag_configure("num",        foreground=C("YELLOW"))
        self._ed.tag_configure("str_lit",    foreground=C("GREEN"))
        self._ed.tag_configure("cmt",        foreground=C("DIM"),
                               font=MONO(self._font_size) + ("italic",))
        self._ed.tag_configure("error_line", background=C("ERR_BG"),
                               underline=True)
        self._ed.tag_configure("squiggle",   underline=True,
                               foreground=C("SQUIGGLE"))
        self._ed.tag_configure("cur_line",   background=C("CUR_LINE"))
        self._ed.tag_configure("match_bracket", background=C("MATCH_BG"))
        # Gutter tags
        self._ln.tag_configure("err_icon",   foreground=C("GUTTER_ERR"))

        # ── Bindings
        self._ed.bind("<KeyRelease>",     self._on_key)
        self._ed.bind("<ButtonRelease>",  self._update_cur)
        self._ed.bind("<KeyPress>",       self._on_keypress)

        # ── Inline error panel (collapsible strip below editor)
        self._err_panel = tk.Frame(outer, bg=C("ERR_BG"), height=0)
        self._err_panel.pack(fill="x")
        self._err_panel.pack_propagate(False)
        self._err_icon  = tk.Label(self._err_panel, text="",
                                   bg=C("ERR_BG"), fg=C("RED"),
                                   font=UI(9), anchor="nw",
                                   padx=10, pady=6, justify="left",
                                   wraplength=500)
        self._err_icon.pack(fill="both", expand=True)

        # Welcome
        self._ed.insert("1.0", WELCOME_TEXT)
        self._rehighlight()
        return outer

    def _sync_scroll(self, *a):  self._ln.yview_moveto(a[0])
    def _scroll_both(self, *a):  self._ed.yview(*a); self._ln.yview(*a)

    # ── Keypress (before char inserted) ───────────────────────

    def _on_keypress(self, event):
        """Auto-close brackets and quotes."""
        pairs = {"(": ")", '"': '"'}
        if event.char in pairs and event.keysym not in ("BackSpace",):
            close = pairs[event.char]
            self._ed.insert("insert", event.char + close)
            # move cursor back one char to sit between pair
            pos = self._ed.index("insert")
            r, c = pos.split(".")
            self._ed.mark_set("insert", f"{r}.{int(c)-1}")
            return "break"

    # ── Key release (after char inserted) ─────────────────────

    def _on_key(self, event=None):
        self._rehighlight()
        self._update_cur()
        self._highlight_matching_bracket()
        self._schedule_lint()
        self._maybe_autocomplete(event)

    def _update_cur(self, _=None):
        r, c = self._ed.index("insert").split(".")
        self._cur_lbl.configure(text=f"Ln {r}, Col {int(c)+1}")
        self._highlight_cur_line()

    def _highlight_cur_line(self):
        self._ed.tag_remove("cur_line", "1.0", "end")
        self._ed.tag_add("cur_line", "insert linestart", "insert lineend+1c")

    # ── Bracket matching ──────────────────────────────────────

    def _highlight_matching_bracket(self):
        self._ed.tag_remove("match_bracket", "1.0", "end")
        pos  = self._ed.index("insert")
        # check char before cursor
        try:
            ch = self._ed.get(f"{pos}-1c", pos)
        except Exception:
            return
        OPEN  = "("
        CLOSE = ")"
        if ch == CLOSE:
            # search backward for matching open
            depth = 0
            idx   = self._ed.index(f"{pos}-1c")
            while True:
                c = self._ed.get(idx, f"{idx}+1c")
                if c == CLOSE: depth += 1
                elif c == OPEN:
                    depth -= 1
                    if depth == 0:
                        self._ed.tag_add("match_bracket", idx, f"{idx}+1c")
                        self._ed.tag_add("match_bracket", f"{pos}-1c", pos)
                        return
                if idx == "1.0": break
                idx = self._ed.index(f"{idx}-1c")
        elif ch == OPEN:
            depth = 0
            idx   = self._ed.index(f"{pos}-1c")
            end   = self._ed.index("end")
            while True:
                c = self._ed.get(idx, f"{idx}+1c")
                if c == OPEN: depth += 1
                elif c == CLOSE:
                    depth -= 1
                    if depth == 0:
                        self._ed.tag_add("match_bracket", f"{pos}-1c", pos)
                        self._ed.tag_add("match_bracket", idx, f"{idx}+1c")
                        return
                if idx == end: break
                idx = self._ed.index(f"{idx}+1c")

    # ── Autocomplete ──────────────────────────────────────────

    def _maybe_autocomplete(self, event):
        """Show autocomplete if user typed 2+ chars matching a keyword or declared var."""
        if event and event.keysym in ("BackSpace", "Delete", "Escape",
                                       "Tab", "Return", "space",
                                       "Left", "Right", "Up", "Down"):
            self._dismiss_ac()
            return

        # Get the word fragment before cursor
        pos    = self._ed.index("insert")
        line   = self._ed.get("insert linestart", "insert")
        # strip everything before the last non-word char
        m = re.search(r'[a-zA-Z_][a-zA-Z0-9_]*$', line)
        if not m or len(m.group()) < 2:
            self._dismiss_ac(); return

        prefix = m.group()

        # Collect candidates: keywords + declared variable names
        src     = self._ed.get("1.0", "end")
        declared= re.findall(r'\b(?:int|float|str|bool)\s+([a-zA-Z_]\w*)', src)
        pool    = KEYWORDS + [d for d in declared if d not in KEYWORDS]

        matches = [w for w in pool if w.startswith(prefix) and w != prefix]
        if not matches:
            self._dismiss_ac(); return

        # Dismiss old popup then show new one
        self._dismiss_ac()
        self._ac_popup = Autocomplete(self, self._ed, matches, prefix)

    def _dismiss_ac(self):
        if self._ac_popup:
            try: self._ac_popup.dismiss()
            except Exception: pass
            self._ac_popup = None

    # ── Auto-indent ───────────────────────────────────────────

    def _auto_indent(self, _=None):
        # If autocomplete is open, let it handle Return
        if self._ac_popup:
            try:
                self._ac_popup._accept()
            except Exception:
                pass
            return "break"
        line   = self._ed.get("insert linestart", "insert")
        spaces = len(line) - len(line.lstrip())
        extra  = 4 if line.rstrip().endswith(":") else 0
        self._ed.insert("insert", "\n" + " " * (spaces + extra))
        return "break"

    # ── Live lint (debounced) ─────────────────────────────────

    def _schedule_lint(self):
        """Cancel any pending lint and schedule a new one 400 ms later."""
        if self._lint_after:
            self.after_cancel(self._lint_after)
        self._lint_after = self.after(400, self._run_lint)

    def _run_lint(self):
        """Run lexer + parser + semantic on current source; annotate errors."""
        self._lint_after = None
        src = self._ed.get("1.0", "end-1c")

        # Clear previous squiggles
        self._ed.tag_remove("squiggle", "1.0", "end")
        self._lint_errors = []

        if not src.strip():
            self._show_err_panel("")
            self._lint_lbl.configure(text="")
            self._update_gutter()
            return

        error_line = 0
        msg        = ""
        try:
            tokens = Lexer(src).tokenize()
            tree   = Parser(tokens).parse()
            SemanticAnalyzer().analyze(tree)
            # All good
            self._show_err_panel("")
            self._lint_lbl.configure(text="✅ No errors", fg=C("GREEN"))
            self._update_gutter()
            return
        except Exception as e:
            raw = str(e)
            m   = re.search(r'line\s+(\d+)', raw, re.I)
            if m: error_line = int(m.group(1))
            msg = friendly(raw, src) or raw

        self._lint_errors = [(error_line, msg)]

        # Draw squiggle on the bad line
        if error_line:
            self._ed.tag_add("squiggle",
                             f"{error_line}.0",
                             f"{error_line}.end")

        # Show inline panel with a short hint
        short = self._short_hint(msg)
        self._show_err_panel(short)
        count = len(self._lint_errors)
        self._lint_lbl.configure(
            text=f"⚠ {count} error{'s' if count>1 else ''}",
            fg=C("RED"))
        self._update_gutter()

    def _short_hint(self, friendly_msg: str) -> str:
        """Extract just the headline + first fix line from a friendly error box."""
        lines = friendly_msg.splitlines()
        headline = ""
        fix_line = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("❌"):
                headline = stripped[1:].strip()
            if stripped and not stripped.startswith("━") and \
               not stripped.startswith("📍") and \
               not stripped.startswith("ℹ") and \
               not stripped.startswith("🔧") and \
               not stripped.startswith("❌") and \
               fix_line == "" and headline:
                fix_line = stripped
        if headline and fix_line and fix_line != headline:
            return f"❌  {headline}  —  {fix_line}"
        return f"❌  {headline}" if headline else ""

    def _show_err_panel(self, text: str):
        """Show or hide the inline error strip below the editor."""
        if text:
            self._err_panel.configure(height=36)
            self._err_icon.configure(text="  " + text)
        else:
            self._err_panel.configure(height=0)
            self._err_icon.configure(text="")

    def _update_gutter(self):
        """Redraw line numbers with ❌ icons on error lines."""
        src  = self._ed.get("1.0", "end")
        n    = src.count("\n") + 1
        err_lines = {ln for ln, _ in self._lint_errors}

        self._ln.configure(state="normal")
        self._ln.delete("1.0", "end")
        self._ln.tag_configure("err_icon", foreground=C("GUTTER_ERR"))
        for i in range(1, n + 1):
            if i in err_lines:
                self._ln.insert("end", f"❌\n", "err_icon")
            else:
                self._ln.insert("end", f"{i:>3}\n")
        self._ln.configure(state="disabled")

    # ── Syntax highlighting ───────────────────────────────────

    def _rehighlight(self):
        src = self._ed.get("1.0", "end")
        # Line numbers (delegated to _update_gutter when linting,
        # but also update immediately here so they don't lag)
        if not self._lint_errors:
            n = src.count("\n") + 1
            self._ln.configure(state="normal")
            self._ln.delete("1.0", "end")
            self._ln.insert("1.0", "\n".join(f"{i:>3}" for i in range(1, n + 1)))
            self._ln.configure(state="disabled")

        for tag in ("typ", "kw", "num", "str_lit", "cmt"):
            self._ed.tag_remove(tag, "1.0", "end")

        for m in _PAT_CMT.finditer(src):
            self._ed.tag_add("cmt",      f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in _PAT_STR.finditer(src):
            self._ed.tag_add("str_lit",  f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in _PAT_TYPE.finditer(src):
            self._ed.tag_add("typ",      f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in _PAT_KW.finditer(src):
            self._ed.tag_add("kw",       f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in _PAT_NUM.finditer(src):
            self._ed.tag_add("num",      f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    # ── Output pane ───────────────────────────────────────────

    def _output_pane(self, parent):
        frame = tk.Frame(parent, bg=C("BG"))
        hdr   = tk.Frame(frame, bg=C("BG2"), height=34)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="  📊  Compiler Output", bg=C("BG2"),
                 fg=C("ACCENT2"), font=BOLD(10), pady=7).pack(side="left")
        tk.Button(hdr, text="Copy", command=self._copy_tab,
                  bg=C("PANEL"), fg=C("TEXT"), font=UI(9),
                  relief="flat", bd=0, padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=8)

        self._nb = ttk.Notebook(frame)
        st = ttk.Style(); st.theme_use("default")
        st.configure("TNotebook",     background=C("BG"),    borderwidth=0)
        st.configure("TNotebook.Tab", background=C("PANEL"), foreground=C("DIM"),
                     padding=[12, 6], font=UI(10))
        st.map("TNotebook.Tab",
               background=[("selected", C("BG2"))],
               foreground=[("selected", C("ACCENT"))])
        self._nb.pack(fill="both", expand=True)

        self._t_tok = self._tab("🔤 Tokens")
        self._t_ast = self._tab("🌳 AST")
        self._t_tac = self._tab("📋 TAC")
        self._t_opt = self._tab("⚡ Optimised")
        self._t_tgt = self._tab("🖥 Target")
        self._t_out = self._tab("▶ Output")
        self._tabs  = [self._t_tok, self._t_ast, self._t_tac,
                       self._t_opt, self._t_tgt, self._t_out]

        self._put(self._t_out,
                  "Press  ▶ Run  (or F5)  to compile and run your program.\n\n"
                  "Use the  Samples  menu to try example programs.", C("DIM"))
        return frame

    def _tab(self, label):
        f  = tk.Frame(self._nb, bg=C("BG2"))
        self._nb.add(f, text=f"  {label}  ")
        t  = tk.Text(f, bg=C("BG2"), fg=C("TEXT"), font=MONO(10),
                     relief="flat", bd=0, padx=12, pady=8,
                     wrap="none", state="disabled",
                     selectbackground=C("PANEL"))
        ys = tk.Scrollbar(f, orient="vertical",   command=t.yview,
                          bg=C("PANEL"), troughcolor=C("BG2"), width=8)
        xs = tk.Scrollbar(f, orient="horizontal", command=t.xview,
                          bg=C("PANEL"), troughcolor=C("BG2"), width=8)
        t.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right",  fill="y")
        xs.pack(side="bottom", fill="x")
        t.pack(fill="both", expand=True)
        return t

    # ── Status bar ────────────────────────────────────────────

    def _statusbar(self):
        bar = tk.Frame(self, bg=C("BG2"), height=26)
        bar.pack(fill="x", side="bottom"); bar.pack_propagate(False)
        self._status = tk.Label(bar,
                                text="  Ready  —  open a file or pick a sample",
                                bg=C("BG2"), fg=C("DIM"), font=UI(9), padx=4)
        self._status.pack(side="left")
        self._stats = tk.Label(bar, text="", bg=C("BG2"), fg=C("DIM"), font=UI(9))
        self._stats.pack(side="right", padx=12)

    # ─── Keyboard shortcuts ───────────────────────────────────

    def _shortcuts(self):
        self.bind("<F5>",            lambda _: self._run())
        self.bind("<Control-s>",     lambda _: self._save())
        self.bind("<Control-o>",     lambda _: self._open())
        self.bind("<Control-n>",     lambda _: self._new())
        self.bind("<Control-h>",     lambda _: self._find_replace())
        self.bind("<Control-plus>",  lambda _: self._zoom_in())
        self.bind("<Control-equal>", lambda _: self._zoom_in())
        self.bind("<Control-minus>", lambda _: self._zoom_out())

    # ─── Toolbar / menu actions ───────────────────────────────

    def _new(self):
        if messagebox.askyesno("New File", "Discard current code?", parent=self):
            self._ed.delete("1.0", "end")
            for t in self._tabs: self._put(t, "")
            self._ed.tag_remove("error_line", "1.0", "end")
            self._ed.tag_remove("squiggle",   "1.0", "end")
            self._show_err_panel("")
            self._lint_errors = []
            self._lint_lbl.configure(text="")
            self._rehighlight()
            self._update_gutter()
            self._status_set("New file")

    def _open(self):
        p = filedialog.askopenfilename(
            filetypes=[("EduLang", "*.edu"), ("Text", "*.txt"), ("All", "*.*")])
        if p:
            with open(p) as f: src = f.read()
            self._ed.delete("1.0", "end")
            self._ed.insert("1.0", src)
            self._rehighlight()
            self._schedule_lint()
            self._status_set(f"Opened  {p}")

    def _save(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".edu",
            filetypes=[("EduLang", "*.edu"), ("Text", "*.txt")])
        if p:
            with open(p, "w") as f:
                f.write(self._ed.get("1.0", "end-1c"))
            self._status_set(f"Saved  {p}")

    def _load_sample(self, name):
        code = SAMPLES.get(name, "")
        self._ed.delete("1.0", "end")
        self._ed.insert("1.0", code)
        self._svar.set("")
        self._ed.tag_remove("error_line", "1.0", "end")
        self._ed.tag_remove("squiggle",   "1.0", "end")
        self._lint_errors = []
        self._show_err_panel("")
        self._lint_lbl.configure(text="")
        self._rehighlight()
        self._schedule_lint()
        self._status_set(f"Loaded sample: {name}")

    def _clear_output(self):
        for t in self._tabs: self._put(t, "")
        self._stats.configure(text="")
        self._status_set("Output cleared")

    def _copy_tab(self):
        idx = self._nb.index("current")
        txt = self._tabs[idx].get("1.0", "end-1c")
        self.clipboard_clear(); self.clipboard_append(txt)
        self._status_set("Copied to clipboard ✓")

    def _find_replace(self): FindReplace(self, self._ed)

    def _zoom_in(self):
        if self._font_size < 22:
            self._font_size += 1; self._apply_zoom()

    def _zoom_out(self):
        if self._font_size > 8:
            self._font_size -= 1; self._apply_zoom()

    def _apply_zoom(self):
        f = MONO(self._font_size)
        self._ed.configure(font=f)
        self._ln.configure(font=f)
        self._ed.tag_configure("cmt", font=f + ("italic",))
        self._status_set(f"Font size: {self._font_size}")

    def _toggle_theme(self):
        global _theme_name, _theme
        _theme_name = "light" if _theme_name == "dark" else "dark"
        _theme      = THEMES[_theme_name]
        messagebox.showinfo(
            "Theme Changed",
            f"Switched to {_theme_name} theme.\n"
            "Please restart the IDE for the full effect.",
            parent=self)

    # ─── RUN ──────────────────────────────────────────────────

    def _run(self):
        self._dismiss_ac()
        source = self._ed.get("1.0", "end-1c").strip()
        real_lines = [l for l in source.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
        if not real_lines:
            messagebox.showwarning("No Code",
                "Please write some EduLang code first,\n"
                "or choose a sample from the Samples menu.",
                parent=self)
            return

        self._ed.tag_remove("error_line", "1.0", "end")
        self._status_set("Compiling…", C("YELLOW"))
        self._run_btn.configure(text="⏳ Running…", state="disabled")
        self.update_idletasks()
        t0 = time.perf_counter()

        def ask(var_name):
            return AskValue(self, var_name).value

        try:
            tokens  = Lexer(source).tokenize()
            tree    = Parser(tokens).parse()
            sym     = SemanticAnalyzer().analyze(tree)
            tac     = TACGenerator().generate(tree)
            tac_opt = optimize(tac)
            cg      = CodeGenerator()
            target  = cg.generate(tac_opt)
            output  = cg.run(input_fn=ask)
            elapsed = time.perf_counter() - t0

        except Exception as err:
            self._run_btn.configure(text="▶  Run  F5", state="normal")
            err_str = str(err)
            lm = re.search(r'line\s+(\d+)', err_str, re.I)
            if lm:
                ln = int(lm.group(1))
                self._ed.tag_remove("error_line", "1.0", "end")
                self._ed.tag_add("error_line", f"{ln}.0", f"{ln}.end+1c")
                self._ed.see(f"{ln}.0")
            for t in self._tabs[:-1]: self._put(t, "")
            self._put(self._t_out, friendly(err_str, source) or err_str, C("RED"))
            self._nb.select(5)
            self._status_set("❌  Compilation failed — see Output tab", C("RED"))
            self._stats.configure(text="")
            return

        self._run_btn.configure(text="▶  Run  F5", state="normal")

        # Tokens
        hdr  = f"{'TYPE':<16} {'VALUE':<24} {'LINE':>5}  {'COL':>5}\n{'─'*58}"
        rows = "\n".join(f"{t.type:<16} {t.value!r:<24} {t.line:>5}  {t.column:>5}"
                         for t in tokens)
        self._put(self._t_tok, hdr + "\n" + rows)

        # AST
        self._put(self._t_ast, format_ast(tree))

        # TAC
        sym_txt  = "── Symbol Table ─────────────────────────────\n\n"
        sym_txt += "\n".join(f"  {n:<16} :  {tp}"
                             for n, tp in sym.all_symbols().items())
        sym_txt += "\n\n── Three Address Code ───────────────────────\n\n"
        sym_txt += "\n".join(f"  {i:>3}.  {ins}" for i, ins in enumerate(tac, 1))
        self._put(self._t_tac, sym_txt)

        # Optimised TAC
        saved    = len(tac) - len(tac_opt)
        opt_txt  = f"── Optimiser removed {saved} instruction(s) ────────\n\n"
        opt_txt += "\n".join(f"  {i:>3}.  {ins}" for i, ins in enumerate(tac_opt, 1))
        self._put(self._t_opt, opt_txt)

        # Target
        tgt_txt  = "── Stack-Based Target Code ──────────────────\n\n"
        tgt_txt += "\n".join(f"  {i:>3}.  {ins}" for i, ins in enumerate(target, 1))
        self._put(self._t_tgt, tgt_txt)

        # Output
        if output:
            prog  = "\n".join(output)
            prog += f"\n\n── Program finished in {elapsed*1000:.2f} ms ──"
            self._put(self._t_out, prog, C("GREEN"))
        else:
            self._put(self._t_out,
                      f"(program ran successfully — no output)\n\n"
                      f"── Finished in {elapsed*1000:.2f} ms ──", C("DIM"))

        self._nb.select(5)
        self._status_set("✅  Compiled and ran successfully", C("GREEN"))
        self._stats.configure(
            text=f"Tokens: {len(tokens)}   TAC: {len(tac_opt)}   "
                 f"Vars: {len(sym.all_symbols())}   {elapsed*1000:.1f} ms")

    # ─── Help dialogs ─────────────────────────────────────────

    def _show_ref(self):
        ref = """\
EduLang Quick Reference
═══════════════════════

TYPES
  int   x          — integer variable
  float y          — floating-point variable
  str   s          — string variable
  bool  b          — boolean variable

ASSIGNMENT
  x = <expression>

INPUT / OUTPUT
  input x              — read a value into x
  print x, "text"      — print one or more items

CONTROL FLOW
  if <condition>:
      <body>
  else:
      <body>

  loop i = <start> till <condition>:
      <body>

OPERATORS
  Arithmetic : + - * / % ** //
  Comparison : > < >= <= == !=
  Logical    : and  or  not

LITERALS
  42     3.14     "hello"     true     false

COMMENTS
  # This line is a comment
"""
        w = tk.Toplevel(self)
        w.title("EduLang Reference")
        w.configure(bg=C("BG2"))
        w.geometry("500x560")
        t = tk.Text(w, bg=C("BG2"), fg=C("TEXT"), font=MONO(10),
                    relief="flat", bd=0, padx=20, pady=16, wrap="word")
        t.pack(fill="both", expand=True)
        t.insert("1.0", ref)
        t.configure(state="disabled")

    def _show_about(self):
        messagebox.showinfo(
            "About EduLang IDE",
            "EduLang Compiler IDE  v3\n\n"
            "A complete compiler pipeline for an\n"
            "educational programming language.\n\n"
            "New in v3:\n"
            "  • Live error squiggles as you type\n"
            "  • Inline error hint panel\n"
            "  • Autocomplete for keywords & variables\n"
            "  • Bracket / quote matching\n"
            "  • Current line highlight\n"
            "  • Error icons in gutter\n",
            parent=self)

    # ─── Utilities ────────────────────────────────────────────

    def _put(self, widget, text, color=None):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.tag_remove("col", "1.0", "end")
        if color:
            widget.tag_add("col", "1.0", "end")
            widget.tag_configure("col", foreground=color)
        widget.configure(state="disabled")

    def _status_set(self, msg, color=None):
        self._status.configure(text=f"  {msg}", fg=color or C("DIM"))


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    IDE().mainloop()