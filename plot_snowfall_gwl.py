"""Maps of annual snowfall change over Central Asia at +2, +3 and +4 degC global warming.

Reads the files written by atlas_snowfall_gwl.py and writes
    snowfall_gwl_central_asia.pdf/.png      absolute and relative change, country means
    snowfall_gwl_book_style_check.pdf/.png  the printed Fig. 2.8 style, both baselines

Usage:
    python plot_snowfall_gwl.py DERIVED_DIR FIG_DIR
"""
import os
import sys
from pathlib import Path

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[v] = "4"

import matplotlib
matplotlib.use("Agg")
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.colors import BoundaryNorm

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 6, "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6,
    "legend.fontsize": 6, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.dpi": 600, "axes.linewidth": 0.5, "mathtext.default": "regular",
})
MM = 1 / 25.4
EXTENT = [45, 90, 30, 56]
CASES = [(2, "ssp2_4_5", "SSP2-4.5"), (3, "ssp3_7_0", "SSP3-7.0"), (4, "ssp5_8_5", "SSP5-8.5")]
PC = ccrs.PlateCarree()
MIN_BASE = 0.05   # mm/day; relative change is not shown where mean snowfall is below this


def load(d, gwl, exp, base):
    ds = xr.open_dataset(Path(d) / f"prsn_gwl{gwl}_{exp}_base{base}.nc")
    return ds.sel(lon=slice(EXTENT[0] - 1, EXTENT[1] + 1), lat=slice(EXTENT[2] - 1, EXTENT[3] + 1))


def decorate(ax):
    ax.set_extent(EXTENT, crs=PC)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4, edgecolor="k")
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.4, edgecolor="k")
    ax.add_feature(cfeature.LAKES.with_scale("50m"), linewidth=0.3, edgecolor="k", facecolor="none")


def stipple(ax, ds, size=0.6):
    lon2, lat2 = np.meshgrid(ds.lon, ds.lat)
    nr = ds.advanced.values != 1          # no robust signal or conflicting signals
    ax.scatter(lon2[nr], lat2[nr], s=size, c="k", marker="o", linewidths=0, transform=PC, zorder=3)


def letter(ax, s):
    ax.text(-0.02, 1.02, s, transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right", va="bottom")


def main_figure(d, figdir, base="1981-2010"):
    abs_lev = [-0.5, -0.3, -0.2, -0.1, -0.05, -0.02, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]
    rel_lev = [-80, -60, -40, -30, -20, -10, -5, 5, 10, 20, 30, 40, 60, 80]
    cm_abs = plt.get_cmap("BrBG", len(abs_lev) + 1)
    cm_rel = plt.get_cmap("BrBG", len(rel_lev) + 1)
    n_abs = BoundaryNorm(abs_lev, cm_abs.N, extend="both")
    n_rel = BoundaryNorm(rel_lev, cm_rel.N, extend="both")

    fig = plt.figure(figsize=(175 * MM, 205 * MM))
    gs = fig.add_gridspec(6, 2, height_ratios=[1, 1, 1, 0.07, 0.22, 1.0], hspace=0.12, wspace=0.07,
                          left=0.085, right=0.99, top=0.985, bottom=0.05)
    letters = iter("abcdefg")
    for r, (gwl, exp, ssp) in enumerate(CASES):
        ds = load(d, gwl, exp, base)
        for c, (field, cmap, norm) in enumerate([(ds.delta_mean, cm_abs, n_abs),
                                                 (ds.rel_mean.where(ds.baseline_mean >= MIN_BASE), cm_rel, n_rel)]):
            ax = fig.add_subplot(gs[r, c], projection=PC)
            ax.set_facecolor("0.85")
            m = ax.pcolormesh(ds.lon, ds.lat, field, cmap=cmap, norm=norm, transform=PC, shading="nearest", rasterized=True)
            stipple(ax, ds)
            decorate(ax)
            letter(ax, next(letters))
            if c == 0:
                ax.text(-0.035, 0.5, f"+{gwl} °C ({ssp}, {ds.attrs['n_models']} models)", rotation=90,
                        transform=ax.transAxes, ha="right", va="center", fontsize=7)
            if r == 2:
                cax = fig.add_subplot(gs[3, c])
                cb = fig.colorbar(m, cax=cax, orientation="horizontal", ticks=abs_lev if c == 0 else rel_lev)
                cb.ax.tick_params(labelsize=5, length=2, width=0.4)
                if c == 0:
                    cb.ax.set_xticklabels([f"{t:g}".replace("-", "−") for t in abs_lev])
                cb.outline.set_linewidth(0.4)
                cb.set_label("Change in annual mean snowfall (mm day$^{-1}$ water equivalent)" if c == 0
                             else "Change in annual mean snowfall (%)", fontsize=6.5)
    # g: country means, one marker per model
    df = pd.read_csv(Path(d) / "country_means_per_model.csv")
    df = df[df.baseline == base]
    countries = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Uzbekistan", "Turkmenistan"]
    ax = fig.add_subplot(gs[5, :])
    shades = ["#bf812d", "#8c510a", "#3d2604"]
    marks = ["o", "s", "^"]
    rng = np.random.default_rng(1)
    for k, (gwl, exp, ssp) in enumerate(CASES):
        sub = df[df.gwl == gwl]
        for i, c in enumerate(countries):
            v = sub[sub.country == c].rel_pct.values
            x = i + (k - 1) * 0.24
            ax.scatter(x + rng.uniform(-0.06, 0.06, v.size), v, s=5, marker=marks[k], facecolor="none",
                       edgecolor=shades[k], linewidth=0.5, alpha=0.8)
            ax.hlines(np.mean(v), x - 0.1, x + 0.1, color=shades[k], linewidth=1.6)
        ax.scatter([], [], s=12, marker=marks[k], facecolor="none", edgecolor=shades[k],
                   label=f"+{gwl} °C ({ssp})")
    ax.axhline(0, color="k", linewidth=0.5)
    ax.set_xticks(range(len(countries)), countries)
    ax.set_ylabel("Change in annual mean snowfall (%)")
    ax.set_xlim(-0.6, len(countries) - 0.4)
    ax.legend(loc="lower left", frameon=False, ncol=3, handletextpad=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    letter(ax, next(letters))
    for ext in ("pdf", "png"):
        fig.savefig(Path(figdir) / f"snowfall_gwl_central_asia.{ext}", dpi=600 if ext == "pdf" else 300)
    plt.close(fig)


def book_style_check(d, figdir):
    """Same colour scale, stippling rule and extent as the printed Fig. 2.8, for both baselines."""
    cmap = plt.get_cmap("BrBG", 14)
    norm = BoundaryNorm(np.linspace(-0.7, 0.7, 15), cmap.N)
    fig, axs = plt.subplots(3, 2, figsize=(175 * MM, 150 * MM), subplot_kw={"projection": PC},
                            gridspec_kw=dict(hspace=0.08, wspace=0.05))
    for r, (gwl, exp, ssp) in enumerate(CASES):
        for c, base in enumerate(["1981-2010", "1995-2014"]):
            ds = load(d, gwl, exp, base)
            ax = axs[r, c]
            m = ax.pcolormesh(ds.lon, ds.lat, ds.delta_mean, cmap=cmap, norm=norm, transform=PC, shading="nearest", rasterized=True)
            stipple(ax, ds, size=0.8)
            decorate(ax)
            letter(ax, "abcdef"[2 * r + c])
    fig.colorbar(m, ax=axs, shrink=0.6, label="Change in annual mean snowfall (mm day$^{-1}$)")
    for ext in ("pdf", "png"):
        fig.savefig(Path(figdir) / f"snowfall_gwl_book_style_check.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    derived, figdir = sys.argv[1], sys.argv[2]
    Path(figdir).mkdir(parents=True, exist_ok=True)
    book_style_check(derived, figdir)
    main_figure(derived, figdir)
