"""
Centrifugal Pump Design App
============================
Interactive Tkinter GUI for designing single-stage centrifugal pumps.

Run:
    python pump_design/app.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt

from calculations import design_summary, affinity_laws, m3s_to_gpm, m_to_ft, kw_to_hp
from plots import (plot_performance_curves, plot_velocity_triangles,
                   plot_impeller_schematic, plot_affinity_comparison)


# ─────────────────────────────────────────────────────────────────────────────
FONT_LABEL  = ("Segoe UI", 10)
FONT_ENTRY  = ("Segoe UI", 10)
FONT_HEAD   = ("Segoe UI", 12, "bold")
FONT_RESULT = ("Consolas", 10)
PAD = {"padx": 6, "pady": 4}

BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
BG_HEADER = "#1a73e8"
FG_HEADER = "#ffffff"
FG_ACCENT = "#1a73e8"
# ─────────────────────────────────────────────────────────────────────────────


class PumpDesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Centrifugal Pump Design Tool")
        self.geometry("1280x820")
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)

        self._ds = None          # last design summary
        self._fig_perf = None
        self._fig_tri  = None
        self._fig_imp  = None
        self._fig_aff  = None

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header bar ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_HEADER, height=48)
        header.pack(fill="x")
        tk.Label(header, text="⚙  Centrifugal Pump Design Tool",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_HEADER, fg=FG_HEADER).pack(side="left", padx=16, pady=8)

        # ── Main paned layout ─────────────────────────────────────────────────
        pane = tk.PanedWindow(self, orient="horizontal", bg=BG_MAIN,
                              sashwidth=6, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=6, pady=6)

        left  = self._build_left_panel(pane)
        right = self._build_right_panel(pane)
        pane.add(left,  minsize=340)
        pane.add(right, minsize=700)

    def _build_left_panel(self, parent):
        frame = tk.Frame(parent, bg=BG_MAIN)

        # ── Input section ─────────────────────────────────────────────────────
        inp_frame = self._section(frame, "Design Inputs")
        self._inputs = {}
        fields = [
            ("Flow rate Q [m³/s]",    "Q_m3s",    "0.05"),
            ("Total head H [m]",      "H_m",      "30.0"),
            ("Speed N [rpm]",         "N_rpm",    "1450"),
            ("Blade outlet angle β₂ [°]", "beta2_deg", "25.0"),
        ]
        for label, key, default in fields:
            row = tk.Frame(inp_frame, bg=BG_PANEL)
            row.pack(fill="x", **PAD)
            tk.Label(row, text=label, font=FONT_LABEL, bg=BG_PANEL,
                     width=26, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var, width=12, font=FONT_ENTRY)
            entry.pack(side="left", padx=4)
            self._inputs[key] = var

        # ── Affinity laws section ─────────────────────────────────────────────
        aff_frame = self._section(frame, "Affinity Laws – Speed Comparison")
        self._aff_speeds = tk.StringVar(value="800, 1000, 1200, 1450, 1750")
        row = tk.Frame(aff_frame, bg=BG_PANEL)
        row.pack(fill="x", **PAD)
        tk.Label(row, text="Speeds [rpm] (comma-sep):", font=FONT_LABEL,
                 bg=BG_PANEL, anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=self._aff_speeds, width=24,
                  font=FONT_ENTRY).pack(side="left", padx=4)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.pack(fill="x", padx=8, pady=6)
        ttk.Button(btn_frame, text="▶  Calculate & Plot",
                   command=self._on_calculate).pack(fill="x", pady=3)
        ttk.Button(btn_frame, text="⟳  Reset to Defaults",
                   command=self._on_reset).pack(fill="x", pady=3)
        ttk.Button(btn_frame, text="✕  Clear Results",
                   command=self._on_clear).pack(fill="x", pady=3)

        # ── Results text ──────────────────────────────────────────────────────
        res_frame = self._section(frame, "Design Summary")
        self._results_text = tk.Text(res_frame, height=28, font=FONT_RESULT,
                                     bg="#1e1e2e", fg="#cdd6f4",
                                     insertbackground="white",
                                     relief="flat", wrap="none")
        sb = ttk.Scrollbar(res_frame, command=self._results_text.yview)
        self._results_text.configure(yscrollcommand=sb.set)
        self._results_text.pack(side="left", fill="both", expand=True, padx=(6, 0))
        sb.pack(side="right", fill="y", padx=(0, 6))

        return frame

    def _build_right_panel(self, parent):
        frame = tk.Frame(parent, bg=BG_MAIN)

        self._nb = ttk.Notebook(frame)
        self._nb.pack(fill="both", expand=True)

        self._tab_perf = ttk.Frame(self._nb)
        self._tab_tri  = ttk.Frame(self._nb)
        self._tab_imp  = ttk.Frame(self._nb)
        self._tab_aff  = ttk.Frame(self._nb)

        self._nb.add(self._tab_perf, text=" Performance Curves ")
        self._nb.add(self._tab_tri,  text=" Velocity Triangles  ")
        self._nb.add(self._tab_imp,  text=" Impeller Schematic  ")
        self._nb.add(self._tab_aff,  text=" Affinity Laws       ")

        # placeholder labels
        for tab, text in [
            (self._tab_perf, "H-Q  |  η-Q  |  P-Q curves appear here after calculation."),
            (self._tab_tri,  "Velocity triangle diagrams appear here after calculation."),
            (self._tab_imp,  "Impeller cross-section schematic appears here."),
            (self._tab_aff,  "Affinity law comparison appears here."),
        ]:
            tk.Label(tab, text=text, font=FONT_LABEL, bg=BG_MAIN,
                     fg="#888").pack(expand=True)

        return frame

    # ── Helper: section card ───────────────────────────────────────────────────
    def _section(self, parent, title):
        outer = tk.Frame(parent, bg=BG_MAIN)
        outer.pack(fill="x", padx=8, pady=4)
        tk.Label(outer, text=title, font=FONT_HEAD,
                 bg=BG_MAIN, fg=FG_ACCENT).pack(anchor="w", pady=(4, 2))
        inner = tk.Frame(outer, bg=BG_PANEL, relief="flat",
                         highlightbackground="#d0d7de", highlightthickness=1)
        inner.pack(fill="x")
        return inner

    # ── Embed matplotlib figure in a notebook tab ──────────────────────────────
    def _embed_figure(self, fig, tab):
        for widget in tab.winfo_children():
            widget.destroy()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, tab, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── Button callbacks ───────────────────────────────────────────────────────
    def _on_calculate(self):
        try:
            Q     = float(self._inputs["Q_m3s"].get())
            H     = float(self._inputs["H_m"].get())
            N     = float(self._inputs["N_rpm"].get())
            beta2 = float(self._inputs["beta2_deg"].get())
        except ValueError:
            messagebox.showerror("Input Error", "All inputs must be numeric.")
            return

        if Q <= 0 or H <= 0 or N <= 0:
            messagebox.showerror("Input Error",
                                 "Q, H, and N must be positive values.")
            return
        if not (10 <= beta2 <= 60):
            messagebox.showwarning("Warning",
                                   "Blade angle β₂ outside typical range 10°–60°.")

        try:
            ds = design_summary(N_rpm=N, Q_m3s=Q, H_m=H, beta2_deg=beta2)
        except Exception as exc:
            messagebox.showerror("Calculation Error", str(exc))
            return

        self._ds = ds
        self._update_results_text(ds)
        self._update_plots(ds)

    def _on_reset(self):
        defaults = {"Q_m3s": "0.05", "H_m": "30.0",
                    "N_rpm": "1450", "beta2_deg": "25.0"}
        for k, v in defaults.items():
            self._inputs[k].set(v)

    def _on_clear(self):
        self._results_text.config(state="normal")
        self._results_text.delete("1.0", "end")
        self._results_text.config(state="disabled")
        for tab, text in [
            (self._tab_perf, "H-Q  |  η-Q  |  P-Q curves appear here after calculation."),
            (self._tab_tri,  "Velocity triangle diagrams appear here after calculation."),
            (self._tab_imp,  "Impeller cross-section schematic appears here."),
            (self._tab_aff,  "Affinity law comparison appears here."),
        ]:
            for w in tab.winfo_children():
                w.destroy()
            tk.Label(tab, text=text, font=FONT_LABEL, bg=BG_MAIN,
                     fg="#888").pack(expand=True)
        plt.close("all")
        self._ds = None

    # ── Results text panel ─────────────────────────────────────────────────────
    def _update_results_text(self, ds):
        lines = [
            "══════════════════════════════════════════",
            "  CENTRIFUGAL PUMP DESIGN SUMMARY",
            "══════════════════════════════════════════",
            "",
            "  ── Operating Point ──────────────────",
            f"  Flow rate Q  : {ds['Q_m3s']*1000:.2f} L/s  ({ds['Q_gpm']:.1f} gpm)",
            f"  Head    H    : {ds['H_m']:.2f} m  ({ds['H_ft']:.1f} ft)",
            f"  Speed   N    : {ds['N_rpm']:.0f} rpm",
            "",
            "  ── Specific Speed ────────────────────",
            f"  Ω_s (dim.)   : {ds['Ns_dim']:.3f}  rad",
            f"  Ns  (US)     : {ds['Ns_us']:.0f}",
            f"  Pump type    : {_pump_type(ds['Ns_dim'])}",
            "",
            "  ── Impeller Geometry ─────────────────",
            f"  Outer dia D₂ : {ds['D2_mm']:.1f} mm",
            f"  Inlet dia D₁ : {ds['D1_mm']:.1f} mm",
            f"  Outlet width b₂: {ds['b2_mm']:.1f} mm",
            f"  Inlet  width b₁: {ds['b1_mm']:.1f} mm",
            f"  Blade angle β₂: {ds['beta2_deg']:.1f}°",
            "",
            "  ── Velocity Triangles ────────────────",
            f"  u₂ (tip speed): {ds['u2_ms']:.2f} m/s",
            f"  Cm₂ (meridional): {ds['Cm2_ms']:.2f} m/s",
            f"  Cu₂ (whirl)  : {ds['Cu2_ms']:.2f} m/s",
            f"  C₂ (absolute): {ds['C2_ms']:.2f} m/s",
            f"  α₂ (abs. angle): {ds['alpha2_deg']:.1f}°",
            f"  u₁ (inlet)   : {ds['u1_ms']:.2f} m/s",
            f"  Cm₁           : {ds['Cm1_ms']:.2f} m/s",
            f"  β₁ (inlet angle): {ds['beta1_deg']:.1f}°",
            "",
            "  ── Head & Efficiency ─────────────────",
            f"  Euler head H_th: {ds['H_euler_m']:.2f} m",
            f"  η_hydraulic   : {ds['eta_hydraulic']*100:.1f}%",
            f"  η_volumetric  : {ds['eta_volumetric']*100:.1f}%",
            f"  η_mechanical  : {ds['eta_mechanical']*100:.1f}%",
            f"  η_overall     : {ds['eta_overall']*100:.1f}%",
            "",
            "  ── Power ─────────────────────────────",
            f"  Shaft power   : {ds['P_shaft_kW']:.2f} kW  ({ds['P_shaft_hp']:.2f} hp)",
            "",
            "  ── NPSH ──────────────────────────────",
            f"  NPSHr         : {ds['NPSHr_m']:.2f} m",
            "",
            "══════════════════════════════════════════",
        ]
        self._results_text.config(state="normal")
        self._results_text.delete("1.0", "end")
        self._results_text.insert("end", "\n".join(lines))
        self._results_text.config(state="disabled")

    # ── Plot updates ───────────────────────────────────────────────────────────
    def _update_plots(self, ds):
        plt.close("all")

        # Performance curves
        fig_perf = plot_performance_curves(
            ds["curves"],
            title=f"Performance Curves  (N = {ds['N_rpm']:.0f} rpm, "
                  f"D₂ = {ds['D2_mm']:.0f} mm)")
        self._embed_figure(fig_perf, self._tab_perf)

        # Velocity triangles
        fig_tri = plot_velocity_triangles(ds)
        self._embed_figure(fig_tri, self._tab_tri)

        # Impeller schematic
        fig_imp = plot_impeller_schematic(ds)
        self._embed_figure(fig_imp, self._tab_imp)

        # Affinity laws
        try:
            speeds = [float(s.strip())
                      for s in self._aff_speeds.get().split(",") if s.strip()]
        except ValueError:
            speeds = [800, 1000, 1200, 1450, 1750]
        fig_aff = plot_affinity_comparison(ds, speeds)
        self._embed_figure(fig_aff, self._tab_aff)


# ── Helper ─────────────────────────────────────────────────────────────────────
def _pump_type(Ns_dim):
    if Ns_dim < 0.5:
        return "Radial flow (low Ns)"
    elif Ns_dim < 1.5:
        return "Mixed radial-flow"
    elif Ns_dim < 3.5:
        return "Mixed flow"
    else:
        return "Axial / propeller flow"


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PumpDesignApp()
    app.mainloop()
