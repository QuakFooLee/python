"""
Centrifugal Pump Design Calculations
Covers: impeller sizing, velocity triangles, specific speed,
        NPSH, affinity laws, and performance curve estimation.
"""
import numpy as np


# ── Constants ──────────────────────────────────────────────────────────────────
RHO_WATER = 998.2   # kg/m³  at 20 °C
G = 9.81            # m/s²


# ── Specific speed ─────────────────────────────────────────────────────────────
def specific_speed_dimensionless(N_rpm, Q_m3s, H_m):
    """Dimensionless specific speed  Ω_s = ω·Q^0.5 / (g·H)^0.75"""
    omega = N_rpm * np.pi / 30          # rad/s
    return omega * Q_m3s**0.5 / (G * H_m)**0.75


def specific_speed_us(N_rpm, Q_gpm, H_ft):
    """US customary specific speed  Ns = N·Q^0.5 / H^0.75"""
    return N_rpm * Q_gpm**0.5 / H_ft**0.75


# ── Unit conversions ───────────────────────────────────────────────────────────
def gpm_to_m3s(gpm): return gpm * 6.30902e-5
def m3s_to_gpm(m3s): return m3s / 6.30902e-5
def ft_to_m(ft):     return ft * 0.3048
def m_to_ft(m):      return m / 0.3048
def hp_to_kw(hp):    return hp * 0.7457
def kw_to_hp(kw):    return kw / 0.7457


# ── Impeller design ────────────────────────────────────────────────────────────
def impeller_outer_diameter(N_rpm, H_m, slip_factor=0.9):
    """
    Euler/Pfleiderer estimate of outer diameter [m].
    u2 = sqrt(g·H / slip_factor)   →   D2 = 2·u2 / ω
    """
    omega = N_rpm * np.pi / 30
    u2 = np.sqrt(G * H_m / slip_factor)
    return 2 * u2 / omega


def impeller_inlet_diameter(D2, Ns_dim):
    """
    Estimate inlet (eye) diameter from empirical ratio.
    Ratio D1/D2 varies with Ns:  low Ns → 0.3,  high Ns → 0.7
    """
    ratio = 0.3 + 0.4 * min(Ns_dim / 2.5, 1.0)
    return ratio * D2


def impeller_width_outlet(Q_m3s, D2, Cm2, num_blades=6, blade_thickness=0.003):
    """
    Outlet width b2 [m] from continuity:
    Q = π·D2·b2·Cm2·(1 - Z·t / π·D2)
    """
    blockage = 1 - num_blades * blade_thickness / (np.pi * D2)
    return Q_m3s / (np.pi * D2 * Cm2 * blockage)


def meridional_velocity_outlet(Q_m3s, D2, b2_ratio=0.08):
    """
    Meridional (radial) velocity at outlet from area estimate.
    b2 ≈ b2_ratio · D2   (initial guess when b2 unknown)
    """
    b2 = b2_ratio * D2
    area = np.pi * D2 * b2
    return Q_m3s / area


# ── Velocity triangles ─────────────────────────────────────────────────────────
def velocity_triangle_outlet(N_rpm, D2, Q_m3s, b2, beta2_deg, num_blades=6,
                              blade_thickness=0.003):
    """
    Returns dict with outlet velocity triangle components [m/s].
    beta2 = blade angle at outlet (measured from tangential direction).
    """
    omega = N_rpm * np.pi / 30
    u2 = omega * D2 / 2
    blockage = 1 - num_blades * blade_thickness / (np.pi * D2)
    Cm2 = Q_m3s / (np.pi * D2 * b2 * blockage)
    beta2 = np.radians(beta2_deg)
    Cu2 = u2 - Cm2 / np.tan(beta2)     # whirl component (Euler)
    C2 = np.sqrt(Cm2**2 + Cu2**2)
    alpha2 = np.degrees(np.arctan2(Cm2, Cu2))
    return {"u2": u2, "Cm2": Cm2, "Cu2": Cu2, "C2": C2, "alpha2_deg": alpha2}


def velocity_triangle_inlet(N_rpm, D1, Q_m3s, b1, num_blades=6,
                             blade_thickness=0.003):
    """
    Returns dict with inlet velocity triangle assuming no pre-swirl (Cu1=0).
    """
    omega = N_rpm * np.pi / 30
    u1 = omega * D1 / 2
    blockage = 1 - num_blades * blade_thickness / (np.pi * D1)
    Cm1 = Q_m3s / (np.pi * D1 * b1 * blockage)
    beta1 = np.degrees(np.arctan2(Cm1, u1))
    W1 = np.sqrt(Cm1**2 + u1**2)
    return {"u1": u1, "Cm1": Cm1, "Cu1": 0.0, "W1": W1, "beta1_deg": beta1}


# ── Euler head & losses ────────────────────────────────────────────────────────
def euler_head(Cu2, u2, Cu1=0.0, u1=0.0):
    """Theoretical (Euler) head [m]."""
    return (u2 * Cu2 - u1 * Cu1) / G


def hydraulic_efficiency(Ns_dim):
    """
    Empirical hydraulic efficiency from dimensionless Ns.
    Ref: Gülich (2008) correlation.
    """
    return 1 - 0.055 / Ns_dim**0.5 - 0.2 * (0.26 - np.log10(Ns_dim))**2


def volumetric_efficiency(Q_m3s):
    """Empirical volumetric efficiency (leakage)."""
    return 1 / (1 + 0.68 * Q_m3s**(-0.68) * 1e-3 + 1e-6)  # simplified


def mechanical_efficiency():
    """Typical mechanical efficiency (bearing + seal losses)."""
    return 0.96


def overall_efficiency(eta_h, eta_v, eta_m):
    return eta_h * eta_v * eta_m


def shaft_power(Q_m3s, H_m, eta_overall, rho=RHO_WATER):
    """Required shaft power [W]."""
    return rho * G * Q_m3s * H_m / eta_overall


# ── NPSH ───────────────────────────────────────────────────────────────────────
def npsh_required(N_rpm, Q_m3s, Nss=220.0):
    """
    Required NPSH_r [m] from suction specific speed limit.
    Nss = N·Q^0.5 / NPSHr^0.75  →  NPSHr = (N·Q^0.5 / Nss)^(4/3)
    Nss ≈ 220 (SI, conservative) is a typical design target.
    """
    return (N_rpm * Q_m3s**0.5 / Nss) ** (4.0 / 3.0)


def npsh_available(p_abs_Pa, p_vapor_Pa, v_inlet_ms, z_inlet_m=0.0,
                   rho=RHO_WATER):
    """NPSHa [m] at pump inlet flange."""
    return ((p_abs_Pa - p_vapor_Pa) / (rho * G)
            + v_inlet_ms**2 / (2 * G)
            + z_inlet_m)


# ── Affinity (similarity) laws ─────────────────────────────────────────────────
def affinity_laws(Q1, H1, P1, N1, N2=None, D2=None, D1=None):
    """
    Scale from (Q1,H1,P1,N1) to new operating point.
    Provide either N2 (speed change) or D2/D1 (impeller trim).
    Returns (Q2, H2, P2).
    """
    if N2 is not None:
        r = N2 / N1
    elif D2 is not None and D1 is not None:
        r = D2 / D1
    else:
        raise ValueError("Provide either N2 or both D2 and D1.")
    return Q1 * r, H1 * r**2, P1 * r**3


# ── Performance curve (H-Q, η-Q, P-Q) ─────────────────────────────────────────
def performance_curves(N_rpm, D2_m, b2_m, beta2_deg, Q_design_m3s,
                       H_design_m, num_points=40):
    """
    Generate H-Q, efficiency-Q, and power-Q curves.
    Uses a parabolic head curve anchored at design point and shut-off head,
    combined with efficiency bell curve.

    Returns dict of arrays (Q, H, eta, P_kW).
    """
    omega = N_rpm * np.pi / 30
    u2 = omega * D2_m / 2

    # Theoretical (shut-off) head via Euler at Q→0  (Cu2→u2 when Cm2→0)
    H_th_shutoff = u2**2 / G       # theoretical max head
    H_shutoff = 0.55 * H_th_shutoff  # account for recirculation losses

    # Flow range: 0 → 130 % of design
    Q_max = 1.3 * Q_design_m3s
    Q_arr = np.linspace(0, Q_max, num_points)

    # Head curve:  H = H_shutoff - A·Q²   anchored at design point
    A = (H_shutoff - H_design_m) / Q_design_m3s**2
    H_arr = H_shutoff - A * Q_arr**2
    H_arr = np.clip(H_arr, 0, None)

    # Efficiency bell curve:  eta_max at Q_design, zero at Q=0 and Q=Q_max
    eta_max = 0.82  # typical best efficiency
    sigma = Q_design_m3s / 2
    eta_arr = eta_max * np.exp(-0.5 * ((Q_arr - Q_design_m3s) / sigma)**2)
    eta_arr[0] = 0.0

    # Power  (safe divide: replace zero eta with 1 before dividing, then mask)
    eta_safe = np.where(eta_arr > 0.01, eta_arr, 1.0)
    P_arr = np.where(
        eta_arr > 0.01,
        RHO_WATER * G * Q_arr * H_arr / eta_safe / 1000,  # kW
        0.0
    )

    return {"Q": Q_arr, "H": H_arr, "eta": eta_arr, "P_kW": P_arr,
            "Q_design": Q_design_m3s, "H_design": H_design_m,
            "H_shutoff": H_shutoff}


# ── Design summary ─────────────────────────────────────────────────────────────
def design_summary(N_rpm, Q_m3s, H_m, beta2_deg=25.0, rho=RHO_WATER):
    """
    Full design pass.  Returns a dict with all key parameters.
    beta2_deg: blade outlet angle (typical: 15°–35° for backward-curved).
    """
    omega = N_rpm * np.pi / 30

    Ns_dim = specific_speed_dimensionless(N_rpm, Q_m3s, H_m)
    Q_gpm  = m3s_to_gpm(Q_m3s)
    H_ft   = m_to_ft(H_m)
    Ns_us  = specific_speed_us(N_rpm, Q_gpm, H_ft)

    D2 = impeller_outer_diameter(N_rpm, H_m)
    D1 = impeller_inlet_diameter(D2, Ns_dim)

    u2 = omega * D2 / 2
    Cm2_est = meridional_velocity_outlet(Q_m3s, D2)
    b2 = impeller_width_outlet(Q_m3s, D2, Cm2_est)
    b1 = b2 * 1.2   # inlet slightly wider

    tri_out = velocity_triangle_outlet(N_rpm, D2, Q_m3s, b2, beta2_deg)
    tri_in  = velocity_triangle_inlet (N_rpm, D1, Q_m3s, b1)

    H_euler = euler_head(tri_out["Cu2"], tri_out["u2"])

    eta_h = hydraulic_efficiency(Ns_dim)
    eta_v = 0.97                         # simplified
    eta_m = mechanical_efficiency()
    eta   = overall_efficiency(eta_h, eta_v, eta_m)

    P_shaft_W = shaft_power(Q_m3s, H_m, eta, rho)
    P_shaft_kW = P_shaft_W / 1000

    NPSHr = npsh_required(N_rpm, Q_m3s)

    curves = performance_curves(N_rpm, D2, b2, beta2_deg, Q_m3s, H_m)

    return {
        # Operating point
        "N_rpm": N_rpm, "Q_m3s": Q_m3s, "H_m": H_m,
        "Q_gpm": Q_gpm, "H_ft": H_ft,
        # Specific speed
        "Ns_dim": Ns_dim, "Ns_us": Ns_us,
        # Impeller geometry
        "D2_m": D2, "D2_mm": D2 * 1000,
        "D1_m": D1, "D1_mm": D1 * 1000,
        "b2_m": b2, "b2_mm": b2 * 1000,
        "b1_m": b1, "b1_mm": b1 * 1000,
        # Velocity triangles
        "u2_ms": tri_out["u2"], "Cm2_ms": tri_out["Cm2"],
        "Cu2_ms": tri_out["Cu2"], "C2_ms": tri_out["C2"],
        "alpha2_deg": tri_out["alpha2_deg"],
        "u1_ms": tri_in["u1"], "Cm1_ms": tri_in["Cm1"],
        "W1_ms": tri_in["W1"], "beta1_deg": tri_in["beta1_deg"],
        "beta2_deg": beta2_deg,
        # Head & efficiency
        "H_euler_m": H_euler,
        "eta_hydraulic": eta_h, "eta_volumetric": eta_v,
        "eta_mechanical": eta_m, "eta_overall": eta,
        # Power
        "P_shaft_kW": P_shaft_kW, "P_shaft_hp": kw_to_hp(P_shaft_kW),
        # NPSH
        "NPSHr_m": NPSHr,
        # Curves
        "curves": curves,
    }
