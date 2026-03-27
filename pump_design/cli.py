"""
Command-line interface for quick pump design calculations.

Usage:
    python pump_design/cli.py --Q 0.05 --H 30 --N 1450 --beta2 25
    python pump_design/cli.py --Q 0.1 --H 50 --N 2900 --plot
"""
import argparse
import sys
from calculations import design_summary, kw_to_hp, m3s_to_gpm, m_to_ft


def _pump_type(Ns_dim):
    if Ns_dim < 0.5:   return "Radial flow (low Ns)"
    if Ns_dim < 1.5:   return "Mixed radial-flow"
    if Ns_dim < 3.5:   return "Mixed flow"
    return "Axial / propeller flow"


def print_summary(ds):
    lines = [
        "",
        "══════════════════════════════════════════════════════",
        "           CENTRIFUGAL PUMP DESIGN SUMMARY",
        "══════════════════════════════════════════════════════",
        f"  Flow rate Q    : {ds['Q_m3s']*1000:.3f} L/s  "
            f"({ds['Q_gpm']:.1f} gpm)",
        f"  Total head H   : {ds['H_m']:.2f} m  ({ds['H_ft']:.1f} ft)",
        f"  Speed N        : {ds['N_rpm']:.0f} rpm",
        "",
        "  ─── Specific Speed ───────────────────────────────",
        f"  Ω_s (dim.)     : {ds['Ns_dim']:.4f}",
        f"  Ns  (US)       : {ds['Ns_us']:.0f}",
        f"  Pump type      : {_pump_type(ds['Ns_dim'])}",
        "",
        "  ─── Impeller Geometry ────────────────────────────",
        f"  Outer diameter D₂ : {ds['D2_mm']:.1f} mm",
        f"  Inlet diameter D₁ : {ds['D1_mm']:.1f} mm",
        f"  Outlet width   b₂ : {ds['b2_mm']:.2f} mm",
        f"  Inlet  width   b₁ : {ds['b1_mm']:.2f} mm",
        f"  Blade angle    β₂ : {ds['beta2_deg']:.1f}°",
        "",
        "  ─── Velocity Triangles ───────────────────────────",
        f"  u₂ (tip speed)    : {ds['u2_ms']:.2f} m/s",
        f"  Cm₂ (meridional)  : {ds['Cm2_ms']:.2f} m/s",
        f"  Cu₂ (whirl)       : {ds['Cu2_ms']:.2f} m/s",
        f"  C₂ (absolute)     : {ds['C2_ms']:.2f} m/s",
        f"  α₂                : {ds['alpha2_deg']:.1f}°",
        f"  u₁                : {ds['u1_ms']:.2f} m/s",
        f"  Cm₁               : {ds['Cm1_ms']:.2f} m/s",
        f"  β₁                : {ds['beta1_deg']:.1f}°",
        "",
        "  ─── Head & Efficiency ────────────────────────────",
        f"  Euler head H_th   : {ds['H_euler_m']:.2f} m",
        f"  η_hydraulic       : {ds['eta_hydraulic']*100:.1f} %",
        f"  η_volumetric      : {ds['eta_volumetric']*100:.1f} %",
        f"  η_mechanical      : {ds['eta_mechanical']*100:.1f} %",
        f"  η_overall         : {ds['eta_overall']*100:.1f} %",
        "",
        "  ─── Power ────────────────────────────────────────",
        f"  Shaft power       : {ds['P_shaft_kW']:.3f} kW "
            f"  ({ds['P_shaft_hp']:.3f} hp)",
        "",
        "  ─── NPSH ─────────────────────────────────────────",
        f"  NPSHr             : {ds['NPSHr_m']:.2f} m",
        "══════════════════════════════════════════════════════",
        "",
    ]
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Centrifugal Pump Design – quick CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--Q",     type=float, default=0.05,
                        help="Flow rate [m³/s]")
    parser.add_argument("--H",     type=float, default=30.0,
                        help="Total head [m]")
    parser.add_argument("--N",     type=float, default=1450.0,
                        help="Rotational speed [rpm]")
    parser.add_argument("--beta2", type=float, default=25.0,
                        help="Blade outlet angle [°]")
    parser.add_argument("--plot",  action="store_true",
                        help="Show matplotlib plots")
    args = parser.parse_args()

    if args.Q <= 0 or args.H <= 0 or args.N <= 0:
        print("ERROR: Q, H, and N must be positive.", file=sys.stderr)
        sys.exit(1)

    ds = design_summary(N_rpm=args.N, Q_m3s=args.Q,
                        H_m=args.H, beta2_deg=args.beta2)
    print_summary(ds)

    if args.plot:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from plots import (plot_performance_curves, plot_velocity_triangles,
                           plot_impeller_schematic, plot_affinity_comparison)

        plot_performance_curves(ds["curves"])
        plot_velocity_triangles(ds)
        plot_impeller_schematic(ds)
        plot_affinity_comparison(ds, [800, 1000, 1200, 1450, 1750])
        plt.show()


if __name__ == "__main__":
    main()
