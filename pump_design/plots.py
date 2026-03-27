"""
Visualization helpers for centrifugal pump design.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


# ── Color palette ───────────────────────────────────────────────────────────────
C_HEAD  = "#1f77b4"
C_EFF   = "#2ca02c"
C_POWER = "#d62728"
C_NPSH  = "#9467bd"
C_ARROW = "#e08000"


def plot_performance_curves(curves, title="Pump Performance Curves", ax_extra=None):
    """
    Plot H-Q, η-Q, P-Q on a 3-axis figure.
    Returns the figure.
    """
    Q  = curves["Q"]  * 1000        # m³/s → L/s
    H  = curves["H"]
    eta = curves["eta"] * 100       # fraction → %
    P  = curves["P_kW"]
    Qd = curves["Q_design"] * 1000
    Hd = curves["H_design"]

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.13))

    # H-Q
    l1, = ax1.plot(Q, H,  color=C_HEAD,  lw=2.2, label="Head  H  [m]")
    ax1.axvline(Qd, color="grey", ls="--", lw=1, alpha=0.7)
    ax1.axhline(Hd, color="grey", ls="--", lw=1, alpha=0.7)
    ax1.scatter([Qd], [Hd], color=C_HEAD, zorder=5, s=70)

    # η-Q
    l2, = ax2.plot(Q, eta, color=C_EFF,  lw=2.2, label="Efficiency η [%]")

    # P-Q
    l3, = ax3.plot(Q, P,   color=C_POWER, lw=2.2, label="Power P [kW]")

    ax1.set_xlabel("Flow rate  Q  [L/s]", fontsize=11)
    ax1.set_ylabel("Head  H  [m]",        fontsize=11, color=C_HEAD)
    ax2.set_ylabel("Efficiency η [%]",    fontsize=11, color=C_EFF)
    ax3.set_ylabel("Shaft power P [kW]",  fontsize=11, color=C_POWER)

    ax1.tick_params(axis="y", colors=C_HEAD)
    ax2.tick_params(axis="y", colors=C_EFF)
    ax3.tick_params(axis="y", colors=C_POWER)

    ax1.set_ylim(bottom=0)
    ax2.set_ylim(0, 110)
    ax3.set_ylim(bottom=0)

    lines = [l1, l2, l3]
    ax1.legend(lines, [l.get_label() for l in lines],
               loc="upper right", fontsize=9)
    ax1.set_title(title, fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_velocity_triangles(ds):
    """
    Draw inlet and outlet velocity triangles from design_summary dict.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle("Velocity Triangles", fontsize=13, fontweight="bold")

    def draw_triangle(ax, u, Cm, Cu, W, title, color_u="#1f77b4",
                      color_C="#2ca02c", color_W="#d62728"):
        # Vector: u (tangential), Cm (meridional), C (absolute), W (relative)
        C = np.sqrt(Cm**2 + Cu**2)
        origin = np.array([0, 0])
        U_vec  = np.array([u,   0])
        C_vec  = np.array([Cu, Cm])
        W_vec  = C_vec - U_vec          # W = C - u

        kw = dict(head_width=0.03 * max(u, C, W),
                  head_length=0.04 * max(u, C, W),
                  length_includes_head=True)

        ax.arrow(*origin, *U_vec, fc=color_u, ec=color_u, **kw)
        ax.arrow(*origin, *C_vec, fc=color_C, ec=color_C, **kw)
        ax.arrow(*U_vec,  *W_vec, fc=color_W, ec=color_W, **kw)

        # Labels
        ax.text(u / 2, -0.08 * max(u, 1), f"u={u:.1f} m/s",
                ha="center", color=color_u, fontsize=8)
        ax.text(Cu / 2, Cm / 2 + 0.05 * max(Cm, 1), f"C={C:.1f} m/s",
                ha="center", color=color_C, fontsize=8)
        ax.text(u + W_vec[0] / 2, W_vec[1] / 2 + 0.05 * max(abs(W_vec[1]), 1),
                f"W={W:.1f} m/s", ha="center", color=color_W, fontsize=8)

        patches = [
            mpatches.Patch(color=color_u, label=f"u  (blade speed)"),
            mpatches.Patch(color=color_C, label=f"C  (absolute)"),
            mpatches.Patch(color=color_W, label=f"W  (relative)"),
        ]
        ax.legend(handles=patches, fontsize=7, loc="upper left")
        ax.set_title(title, fontsize=11)
        ax.set_aspect("equal")
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
        ax.grid(True, alpha=0.25)
        ax.set_xlabel("Tangential [m/s]")
        ax.set_ylabel("Meridional [m/s]")

    draw_triangle(axes[0],
                  u  = ds["u1_ms"],
                  Cm = ds["Cm1_ms"],
                  Cu = 0.0,
                  W  = ds["W1_ms"],
                  title=f"Inlet  (β₁ = {ds['beta1_deg']:.1f}°)")

    draw_triangle(axes[1],
                  u  = ds["u2_ms"],
                  Cm = ds["Cm2_ms"],
                  Cu = ds["Cu2_ms"],
                  W  = np.sqrt(ds["Cm2_ms"]**2 + (ds["u2_ms"] - ds["Cu2_ms"])**2),
                  title=f"Outlet  (β₂ = {ds['beta2_deg']:.1f}°, α₂ = {ds['alpha2_deg']:.1f}°)")

    fig.tight_layout()
    return fig


def plot_impeller_schematic(ds):
    """
    Simple 2-D cross-section schematic of the impeller.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    D2 = ds["D2_m"]
    D1 = ds["D1_m"]
    r2 = D2 / 2
    r1 = D1 / 2

    # Outer shroud circle
    outer = plt.Circle((0, 0), r2, fill=False, color="#1f77b4", lw=2,
                        label=f"Outlet  D₂={D2*1000:.0f} mm")
    inner = plt.Circle((0, 0), r1, fill=False, color="#d62728", lw=2, ls="--",
                        label=f"Inlet   D₁={D1*1000:.0f} mm")
    hub   = plt.Circle((0, 0), r1 * 0.35, color="#aaaaaa", alpha=0.5,
                        label="Hub")

    ax.add_patch(outer)
    ax.add_patch(inner)
    ax.add_patch(hub)

    # Blades (6 backward-curved)
    num_blades = 6
    beta2 = ds["beta2_deg"]
    for i in range(num_blades):
        theta_start = i * 2 * np.pi / num_blades
        # Blade trace: spiral from r1 to r2
        t = np.linspace(0, 1, 60)
        r = r1 + (r2 - r1) * t
        angle_sweep = np.radians(70)    # total angular sweep of blade
        theta = theta_start + angle_sweep * t
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        ax.plot(x, y, color="#e08000", lw=1.6)

    ax.set_aspect("equal")
    margin = r2 * 1.15
    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Impeller Cross-Section Schematic", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.2)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    fig.tight_layout()
    return fig


def plot_affinity_comparison(ds, speeds):
    """
    Plot H-Q curves at multiple speeds using affinity laws.
    speeds: list of RPM values.
    """
    Q0 = ds["curves"]["Q"]
    H0 = ds["curves"]["H"]
    N0 = ds["N_rpm"]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(speeds)))

    for speed, col in zip(speeds, colors):
        r = speed / N0
        Q_s = Q0 * r * 1000      # L/s
        H_s = H0 * r**2
        ax.plot(Q_s, H_s, color=col, lw=2,
                label=f"{speed:.0f} rpm")

    ax.set_xlabel("Flow rate  Q  [L/s]", fontsize=11)
    ax.set_ylabel("Head  H  [m]",        fontsize=11)
    ax.set_title("Affinity Laws – H-Q at Different Speeds", fontsize=13,
                 fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax.legend(title="Speed", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
