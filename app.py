r"""
================================================================================
  AUTOMAÇÃO WABBAJACK — Interface Gráfica
  Wizard para configurar, capturar imagens dos botões e iniciar o download.

  USO:
    python app.py

  DEPENDÊNCIAS (já no requirements.txt):
    pip install pyautogui opencv-python Pillow pygetwindow
================================================================================
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instal


# ─────────────────────────────────────────────────────────────────────────────
#  Redireciona o log de instal.py para uma fila → widget de texto
# ─────────────────────────────────────────────────────────────────────────────

class _QueueHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def emit(self, record):
        tag = {'WARNING': 'warn', 'ERROR': 'error', 'CRITICAL': 'error'}.get(
            record.levelname, 'info'
        )
        self.q.put((self.format(record), tag))


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo de instrução antes da captura
# ─────────────────────────────────────────────────────────────────────────────

class _CaptureInstructionDialog(tk.Toplevel):
    def __init__(self, parent, filename: str):
        super().__init__(parent)
        self.title("Capturar imagem")
        self.resizable(False, False)
        self.grab_set()
        self.confirmed = False
        self._center(460, 220)

        msg = (
            f"Capturando:  {filename}\n\n"
            "1. Clique em 'Pronto'\n"
            "2. Navegue até a janela com o botão desejado\n"
            "3. Clique e arraste para selecionar a região exata do botão\n"
            "   (ESC cancela)"
        )
        ttk.Label(self, text=msg, justify='left', wraplength=420,
                  padding=(24, 20, 24, 10)).pack(fill='x')

        row = ttk.Frame(self, padding=(24, 0, 24, 20))
        row.pack(fill='x')
        ttk.Button(row, text="Cancelar", command=self.destroy).pack(side='right', padx=(6, 0))
        ttk.Button(row, text="Pronto →", command=self._ok).pack(side='right')

    def _ok(self):
        self.confirmed = True
        self.destroy()

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


# ─────────────────────────────────────────────────────────────────────────────
#  Seletor de região: tela cheia com screenshot de fundo
# ─────────────────────────────────────────────────────────────────────────────

class _RegionSelector(tk.Toplevel):
    """Exibe o screenshot da tela cheia e deixa o usuário arrastar para selecionar."""

    def __init__(self, parent, screenshot: Image.Image):
        super().__init__(parent)
        self.region = None

        sw, sh = screenshot.width, screenshot.height
        self.geometry(f"{sw}x{sh}+0+0")
        self.overrideredirect(True)
        self.attributes('-topmost', True)

        self._photo = ImageTk.PhotoImage(screenshot)
        c = tk.Canvas(self, width=sw, height=sh, cursor='cross', bd=0, highlightthickness=0)
        c.pack()
        c.create_image(0, 0, anchor='nw', image=self._photo)
        # Escurece levemente para destacar a seleção
        c.create_rectangle(0, 0, sw, sh, fill='black', stipple='gray25', outline='')
        c.create_text(
            sw // 2, 38,
            text="Arraste para selecionar o botão   •   ESC cancela",
            fill='white', font=('Segoe UI', 13, 'bold'),
        )

        self._c = c
        self._rect = None
        self._x0 = self._y0 = 0

        c.bind('<ButtonPress-1>',   self._press)
        c.bind('<B1-Motion>',       self._drag)
        c.bind('<ButtonRelease-1>', self._release)
        self.bind('<Escape>', lambda _: self.destroy())

    def _press(self, e):
        self._x0, self._y0 = e.x, e.y
        if self._rect:
            self._c.delete(self._rect)

    def _drag(self, e):
        if self._rect:
            self._c.delete(self._rect)
        self._rect = self._c.create_rectangle(
            self._x0, self._y0, e.x, e.y,
            outline='#ff4444', width=2, dash=(6, 3),
        )

    def _release(self, e):
        x1, y1 = min(self._x0, e.x), min(self._y0, e.y)
        x2, y2 = max(self._x0, e.x), max(self._y0, e.y)
        self.region = (x1, y1, x2, y2)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  Configuração dos botões mostrados na aba de captura
# ─────────────────────────────────────────────────────────────────────────────

_BUTTONS = [
    ("btn_slow_download.png",     "Slow Download  (Nexus Mods)",          True),
    ("btn_standard_download.png", "Standard Download  (Nexus Mods)",      False),
    ("btn_manual_download.png",   "Manual Download  (fallback)",           False),
    ("btn_install_from_disk.png", "Install from disk  (Wabbajack)",       False),
    ("btn_open.png",              "Abrir / Open  (diálogo de arquivo)",   False),
    ("btn_install.png",           "Install  (Wabbajack)",                 False),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Aplicativo principal
# ─────────────────────────────────────────────────────────────────────────────

class WabbajackApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automação Wabbajack")
        self.geometry("780x600")
        self.resizable(False, False)

        ttk.Style(self).theme_use('clam')

        self._log_q: queue.Queue = queue.Queue()
        self._inject_log_handler()

        self._build_ui()
        self._refresh_status()
        self._poll_log()

    # ── Log ──────────────────────────────────────────────────────────────────

    def _inject_log_handler(self):
        h = _QueueHandler(self._log_q)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        instal.log.addHandler(h)

    def _poll_log(self):
        try:
            while True:
                msg, tag = self._log_q.get_nowait()
                self._log.configure(state='normal')
                self._log.insert('end', msg + '\n', tag)
                self._log.see('end')
                self._log.configure(state='disabled')
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=10)
        self._nb = nb
        self._build_tab_setup(nb)
        self._build_tab_settings(nb)
        self._build_tab_run(nb)

    # ─── Aba 1: Configuração ─────────────────────────────────────────────────

    def _build_tab_setup(self, nb):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="  1. Configuração  ")
        f.columnconfigure(0, weight=1)

        # Modlist path
        ttk.Label(f, text="Arquivo do Modlist (.wabbajack):",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w')

        path_row = ttk.Frame(f)
        path_row.grid(row=1, column=0, sticky='ew', pady=(4, 20))
        path_row.columnconfigure(0, weight=1)

        self._modlist = tk.StringVar(value=instal.MODLIST_PATH)
        ttk.Entry(path_row, textvariable=self._modlist).grid(row=0, column=0, sticky='ew')
        ttk.Button(path_row, text="Procurar...",
                   command=self._browse).grid(row=0, column=1, padx=(6, 0))

        # Images
        ttk.Label(f, text="Imagens dos Botões:",
                  font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w')
        ttk.Label(
            f,
            text="★ = obrigatória    Clique em 'Capturar', vá até a janela correta e arraste para selecionar o botão",
            foreground='gray',
        ).grid(row=3, column=0, sticky='w', pady=(2, 8))

        card = ttk.LabelFrame(f, text="", padding=12)
        card.grid(row=4, column=0, sticky='nsew')
        card.columnconfigure(1, weight=1)
        f.rowconfigure(4, weight=1)

        self._sv: dict[str, tk.StringVar] = {}
        self._slabels: dict[str, ttk.Label] = {}

        for i, (fname, label, req) in enumerate(_BUTTONS):
            prefix = "★ " if req else "    "
            ttk.Label(card, text=f"{prefix}{label}").grid(
                row=i, column=0, sticky='w', padx=(0, 14), pady=4)

            sv = tk.StringVar()
            lbl = ttk.Label(card, textvariable=sv, width=14, anchor='w')
            lbl.grid(row=i, column=1, sticky='w', pady=4)
            self._sv[fname] = sv
            self._slabels[fname] = lbl

            ttk.Button(card, text="Capturar", width=10,
                       command=lambda fn=fname: self._capture(fn)
                       ).grid(row=i, column=2, padx=(14, 0), pady=4)

    # ─── Aba 2: Configurações avançadas ──────────────────────────────────────

    def _build_tab_settings(self, nb):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="  2. Configurações  ")
        f.columnconfigure(1, weight=1)

        # Confidence slider
        self._conf   = tk.DoubleVar(value=instal.CONFIANCA)
        self._conf_s = tk.StringVar(value=f"{instal.CONFIANCA:.2f}")

        ttk.Label(f, text="Confiança de reconhecimento  (0.50 – 1.00):").grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))

        row_c = ttk.Frame(f)
        row_c.grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 20))
        ttk.Scale(row_c, from_=0.50, to=1.00, variable=self._conf, orient='horizontal',
                  length=320,
                  command=lambda v: self._conf_s.set(f"{float(v):.2f}")).pack(side='left')
        ttk.Label(row_c, textvariable=self._conf_s, width=5).pack(side='left', padx=6)
        ttk.Label(row_c, text="← reduza se os botões não forem encontrados",
                  foreground='gray').pack(side='left')

        def spin_row(row, label, var, lo, hi, inc=1):
            ttk.Label(f, text=label).grid(row=row, column=0, sticky='w', pady=6, padx=(0, 14))
            ttk.Spinbox(f, from_=lo, to=hi, increment=inc, textvariable=var,
                        width=9).grid(row=row, column=1, sticky='w')

        self._timeout  = tk.IntVar(value=instal.TIMEOUT_BOTAO)
        self._interval = tk.DoubleVar(value=instal.INTERVALO_LOOP)
        self._wait     = tk.DoubleVar(value=instal.ESPERA_APOS_DOWNLOAD)
        self._maxatt   = tk.IntVar(value=instal.MAX_TENTATIVAS_SEM_BOTAO)

        spin_row(2, "Timeout por botão (segundos):",            self._timeout,  10, 300)
        spin_row(3, "Intervalo entre verificações (segundos):", self._interval, 0.5, 10.0, 0.5)
        spin_row(4, "Espera após clicar no Slow Download (s):", self._wait,     1.0, 30.0, 0.5)
        spin_row(5, "Tentativas máximas sem botão:",            self._maxatt,   10, 1000)

        ttk.Separator(f, orient='horizontal').grid(
            row=6, column=0, columnspan=3, sticky='ew', pady=16)

        self._all_steps = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            f,
            text=(
                "Automatizar etapas 1–3  (abrir Wabbajack, selecionar modlist, iniciar instalação)\n"
                "Requer imagens:  btn_install_from_disk   btn_open   btn_install"
            ),
            variable=self._all_steps,
        ).grid(row=7, column=0, columnspan=3, sticky='w')

    # ─── Aba 3: Executar ─────────────────────────────────────────────────────

    def _build_tab_run(self, nb):
        f = ttk.Frame(nb, padding=16)
        nb.add(f, text="  3. Executar  ")

        # Barra de ação
        top = ttk.Frame(f)
        top.pack(fill='x', pady=(0, 10))

        self._status = tk.StringVar(value="Pronto para iniciar")
        ttk.Label(top, textvariable=self._status, font=('Segoe UI', 10)).pack(side='left')

        self._btn_stop  = ttk.Button(top, text="⏹  Parar",   command=self._stop,
                                     state='disabled', width=14)
        self._btn_start = ttk.Button(top, text="▶  Iniciar", command=self._start, width=14)
        self._btn_stop.pack(side='right', padx=(6, 0))
        self._btn_start.pack(side='right')

        ttk.Separator(f, orient='horizontal').pack(fill='x', pady=(0, 8))

        # Log
        log_wrap = ttk.Frame(f)
        log_wrap.pack(fill='both', expand=True)

        self._log = tk.Text(
            log_wrap,
            state='disabled',
            font=('Consolas', 9),
            bg='#1e1e1e', fg='#d4d4d4',
            wrap='word', bd=0,
        )
        vsb = ttk.Scrollbar(log_wrap, orient='vertical', command=self._log.yview)
        self._log.configure(yscrollcommand=vsb.set)
        self._log.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self._log.tag_configure('info',  foreground='#9cdcfe')
        self._log.tag_configure('warn',  foreground='#ce9178')
        self._log.tag_configure('error', foreground='#f48771')

    # ── Browse ───────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Selecione o arquivo .wabbajack",
            filetypes=[("Wabbajack", "*.wabbajack"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self._modlist.set(path.replace('/', os.sep))

    # ── Captura interativa de imagem ─────────────────────────────────────────

    def _capture(self, filename: str):
        dialog = _CaptureInstructionDialog(self, filename)
        self.wait_window(dialog)
        if not dialog.confirmed:
            return

        # Esconde a janela principal para ela não aparecer no screenshot
        self.withdraw()
        self.update()
        time.sleep(0.45)

        try:
            screenshot = ImageGrab.grab()
        except Exception as e:
            self.deiconify()
            messagebox.showerror("Erro ao capturar tela", str(e))
            return

        sel = _RegionSelector(self, screenshot)
        self.wait_window(sel)

        self.deiconify()
        self.lift()
        self.focus_force()

        if sel.region is None:
            return  # ESC pressionado

        x1, y1, x2, y2 = sel.region
        if (x2 - x1) < 5 or (y2 - y1) < 5:
            messagebox.showwarning("Seleção muito pequena",
                                   "Selecione uma área maior e tente novamente.")
            return

        cropped = screenshot.crop((x1, y1, x2, y2))
        os.makedirs(instal.IMGS_DIR, exist_ok=True)
        dest = os.path.join(instal.IMGS_DIR, filename)
        cropped.save(dest)

        self._refresh_status()
        messagebox.showinfo("Imagem salva!", f"✔  {filename}\nLocal: {dest}")

    def _refresh_status(self):
        for fname, sv in self._sv.items():
            exists = os.path.exists(os.path.join(instal.IMGS_DIR, fname))
            sv.set("✔ Capturado" if exists else "✗ Faltando")
            self._slabels[fname].configure(foreground='#2d8a4e' if exists else '#c04040')

    # ── Automação ────────────────────────────────────────────────────────────

    def _apply_settings(self):
        instal.MODLIST_PATH             = self._modlist.get()
        instal.CONFIANCA                = self._conf.get()
        instal.TIMEOUT_BOTAO            = self._timeout.get()
        instal.INTERVALO_LOOP           = self._interval.get()
        instal.ESPERA_APOS_DOWNLOAD     = self._wait.get()
        instal.MAX_TENTATIVAS_SEM_BOTAO = self._maxatt.get()

    def _start(self):
        if not self._modlist.get():
            messagebox.showerror("Erro", "Informe o caminho do modlist.")
            self._nb.select(0)
            return

        if not os.path.exists(os.path.join(instal.IMGS_DIR, "btn_slow_download.png")):
            messagebox.showerror(
                "Imagem obrigatória faltando",
                "Capture a imagem 'btn_slow_download.png' primeiro.\n"
                "(Aba Configuração → linha Slow Download → Capturar)",
            )
            self._nb.select(0)
            return

        self._apply_settings()
        instal.STOP_REQUESTED = False

        # Limpa o log
        self._log.configure(state='normal')
        self._log.delete('1.0', 'end')
        self._log.configure(state='disabled')

        self._btn_start.configure(state='disabled')
        self._btn_stop.configure(state='normal')
        self._status.set("Rodando...")

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            if self._all_steps.get():
                instal.etapa1_install_from_disk()
                instal.etapa2_selecionar_modlist()
                instal.etapa3_iniciar_instalacao()
            instal.etapa4_loop_slow_download()
        except Exception as e:
            instal.log.error(f"Erro inesperado: {e}", exc_info=True)
        finally:
            self.after(0, self._on_done)

    def _stop(self):
        instal.STOP_REQUESTED = True
        self._status.set("Parando...")

    def _on_done(self):
        self._btn_start.configure(state='normal')
        self._btn_stop.configure(state='disabled')
        self._status.set("Finalizado")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = WabbajackApp()
    app.mainloop()
