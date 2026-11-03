"""CMIP6 snow water equivalent change over Central Asia at +2, +3, +4 degC (figure for the
reply), with Kazakhstan means of SWE and snowfall per model.

Usage: python swe_figure.py ESGF_DIR GWL_CSV ATLAS_DERIVED_DIR OUT_DIR
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
import regionmask
import xarray as xr
from matplotlib.colors import BoundaryNorm

sys.path.insert(0, str(Path(__file__).parent))
from swe_gwl import BASE, CASES, LAT, LON, annual_metrics, to_grid  # noqa: E402

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
                     "font.size": 6, "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6,
                     "legend.fontsize": 6, "pdf.fonttype": 42, "axes.linewidth": 0.5, "mathtext.default": "regular"})
MM = 1 / 25.4
PC = ccrs.PlateCarree()
EXTENT = [45, 90, 30, 56]


def main(esgf, gwl_csv, derived, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(gwl_csv, na_values=["NA"]).set_index("model_run")
    m3 = regionmask.defined_regions.natural_earth_v5_0_0.countries_50.mask_3D(LON, LAT)
    kz = m3.isel(region=list(m3.names.values).index("Kazakhstan"))
    w = xr.DataArray(np.cos(np.deg2rad(LAT)), dims="lat", coords={"lat": LAT})
    fields, rows = {}, []
    for gwl, exp, col, atlas_exp in CASES:
        rel = []
        for run in table.index:
            n = table.loc[run, col]
            if not np.isfinite(n) or n > 9000:
                continue
            model, member = run.rsplit("_", 1)
            fh, fs = (Path(esgf) / f"snw_{model}_{member}_{e}.nc" for e in ("historical", exp))
            if not (fh.exists() and fs.exists()):
                continue
            try:
                da = xr.concat([xr.open_dataarray(fh, use_cftime=True),
                                xr.open_dataarray(fs, use_cftime=True)], dim="time")
            except Exception:
                continue
            da = to_grid(da)
            mean, peak = annual_metrics(da)
            n = int(n)
            perennial = da.sel(time=da.time.dt.year.isin(range(*BASE))).groupby("time.month").mean().min("month") > 1.0
            for metric, f in (("annual mean SWE", mean), ("peak SWE", peak)):
                b = f.sel(year=slice(*BASE)).mean("year").where(~perennial)
                d = f.sel(year=slice(n - 9, n + 10)).mean("year").where(~perennial) - b
                if metric == "annual mean SWE":
                    rel.append((100 * d / b.where(b > 1.0)).expand_dims(model=[model]))
                bk = b.where(kz & (b > 1.0)).weighted(w).mean(("lat", "lon"))
                dk = d.where(kz & (b > 1.0)).weighted(w).mean(("lat", "lon"))
                rows.append(dict(gwl=gwl, model=model, metric=metric, rel_pct=float(100 * dk / bk)))
        r = xr.concat(rel, dim="model")
        med = r.median("model")
        share = xr.where(med < 0, (r < 0).sum("model"), (r > 0).sum("model")) / r.notnull().sum("model")
        fields[gwl] = (med, share, r.sizes["model"])
        ds = xr.open_dataset(Path(derived) / f"prsn_gwl{gwl}_{atlas_exp}_base1981-2010.nc")
        ds = ds.interp(lon=LON, lat=LAT, method="nearest")
        bk = ds.baseline.where(kz).weighted(w).mean(("lat", "lon"))
        dk = ds.delta.where(kz).weighted(w).mean(("lat", "lon"))
        for model, v in zip(ds.member.values, (100 * dk / bk).values):
            rows.append(dict(gwl=gwl, model=str(model), metric="snowfall", rel_pct=float(v)))
    df = pd.DataFrame(rows)
    df.to_csv(out / "kazakhstan_swe_snowfall_per_model.csv", index=False)
    print(df.groupby(["metric", "gwl"]).rel_pct.agg(
        n="count", median="median", p10=lambda x: x.quantile(0.1), p90=lambda x: x.quantile(0.9)).round(0).to_string())

    lev = [-80, -60, -50, -40, -30, -20, -10, -5, 5, 10, 20, 40]
    cmap = plt.get_cmap("BrBG", len(lev) + 1)
    norm = BoundaryNorm(lev, cmap.N, extend="both")
    fig = plt.figure(figsize=(175 * MM, 108 * MM))
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 0.05, 1.0], hspace=0.45, wspace=0.05,
                          left=0.07, right=0.99, top=0.99, bottom=0.07)
    lon2, lat2 = np.meshgrid(LON, LAT)
    for i, (gwl, exp, col, atlas_exp) in enumerate(CASES):
        med, share, nmod = fields[gwl]
        ax = fig.add_subplot(gs[0, i], projection=PC)
        ax.set_facecolor("0.85")
        mp = ax.pcolormesh(LON, LAT, med, cmap=cmap, norm=norm, transform=PC, shading="nearest", rasterized=True)
        nr = (share.values < 0.8) & np.isfinite(med.values)
        ax.scatter(lon2[nr], lat2[nr], s=0.5, c="k", linewidths=0, transform=PC, zorder=3)
        ax.set_extent(EXTENT, crs=PC)
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.4)
        ax.text(0.02, 0.04, f"+{gwl} °C ({exp.upper()[:4]}-{exp[4]}.{exp[5]}, {nmod} models)",
                transform=ax.transAxes, fontsize=6, bbox=dict(fc="white", ec="none", pad=1))
        ax.text(-0.02, 1.03, "abc"[i], transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right")
    cax = fig.add_subplot(gs[1, :])
    cb = fig.colorbar(mp, cax=cax, orientation="horizontal", ticks=lev)
    cb.set_label("Change in annual mean snow water equivalent (%)", fontsize=6.5)
    cb.outline.set_linewidth(0.4)
    ax = fig.add_subplot(gs[2, :])
    metrics = ["snowfall", "annual mean SWE", "peak SWE"]
    shades = ["#bf812d", "#8c510a", "#3d2604"]
    marks = ["o", "s", "^"]
    rng = np.random.default_rng(2)
    for k, (gwl, *_rest) in enumerate(CASES):
        for j, mt in enumerate(metrics):
            v = df[(df.gwl == gwl) & (df.metric == mt)].rel_pct.values
            x = j * 4 + k
            ax.scatter(x + rng.uniform(-0.15, 0.15, v.size), v, s=5, marker=marks[k], facecolor="none",
                       edgecolor=shades[k], linewidth=0.5)
            ax.hlines(np.median(v), x - 0.3, x + 0.3, color=shades[k], linewidth=1.6)
        ax.scatter([], [], s=12, marker=marks[k], facecolor="none", edgecolor=shades[k], label=f"+{gwl} °C")
    ax.axhline(0, color="k", linewidth=0.5)
    ax.set_xticks([1, 5, 9], ["Snowfall (IPCC Atlas)", "Annual mean SWE", "Peak SWE"])
    ax.set_ylabel("Kazakhstan, change (%)")
    ax.legend(frameon=False, ncol=3, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(-0.02, 1.03, "d", transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right")
    for ext in ("pdf", "png"):
        fig.savefig(out / f"swe_gwl_central_asia.{ext}", dpi=600 if ext == "pdf" else 300)


if __name__ == "__main__":
    main(*sys.argv[1:5])
