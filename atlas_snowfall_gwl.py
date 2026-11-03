"""Snowfall change over Central Asia at global warming levels, following the IPCC AR6 WGI
Interactive Atlas method.

For every CMIP6 model with snowfall output and a warming-level year in the official Atlas
table (github.com/IPCC-WG1/Atlas, warming-levels/CMIP6_Atlas_WarmingLevels.csv):

    delta_m(x) = mean of annual snowfall over [n_m - 9, n_m + 10]  -  mean over the baseline

where n_m is the central year at which model m reaches the warming level in the chosen
scenario. The map value is the multi-model mean of delta_m. A grid cell counts as robust
(Atlas "simple" method) when more than int(0.8 N) of the N models have the sign of the
multi-model mean, which is the agreement() rule of the Atlas hatching functions.
Relative change is the multi-model mean delta over the multi-model mean baseline.

Usage:
    python atlas_snowfall_gwl.py DATA_DIR GWL_CSV OUT_DIR
DATA_DIR holds the unzipped CDS files in historical/, ssp2_4_5/, ssp3_7_0/, ssp5_8_5/.
"""
import os
import sys
from pathlib import Path

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[v] = "4"

import numpy as np
import pandas as pd
import xarray as xr

BOX = dict(lon=slice(40, 95), lat=slice(25, 60))      # a margin around the 45-90E, 30-56N map
CASES = [  # warming level, CDS experiment, column in the Atlas table
    (2, "ssp2_4_5", "2_ssp245"),
    (3, "ssp3_7_0", "3_ssp370"),
    (4, "ssp5_8_5", "4_ssp585"),
]
BASELINES = {"1995-2014": (1995, 2014), "1981-2010": (1981, 2010)}
COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Uzbekistan", "Turkmenistan"]


def member_labels(ds):
    """Return model_variant labels (as in the Atlas warming-level table) for each member."""
    if "member_id" in ds and "gcm_model" in ds:
        model = ds["gcm_model"].values.astype(str)
        variant = ds["gcm_variant"].values.astype(str) if "gcm_variant" in ds else ds["member_id"].values.astype(str)
        return [f"{m.strip()}_{v.strip()}" for m, v in zip(model, variant)]
    if "member_id" in ds:
        return [str(s).strip() for s in ds["member_id"].values.astype(str)]
    return [str(s).strip() for s in ds["member"].values.astype(str)]


def annual_box(path, years, monthly_totals=False):
    """Annual mean snowfall (mm/day) per member over the box, as (member, year, lat, lon).

    monthly_totals=True divides by the number of days in each month. The CDS copy of the
    CMIP6 SSP3-7.0 snowfall file (product v2.0-final) holds monthly totals although its
    metadata say daily means; main() detects this against the historical run.
    """
    ds = xr.open_dataset(path, chunks={"time": 120})
    var = "prsn" if "prsn" in ds else [k for k, v in ds.data_vars.items() if v.ndim == 4][0]
    da = ds[var]
    lat_desc = bool(ds.lat[0] > ds.lat[-1])
    box = dict(lon=BOX["lon"], lat=slice(BOX["lat"].stop, BOX["lat"].start) if lat_desc else BOX["lat"])
    if float(ds.lon.max()) > 180:
        da = da.assign_coords(lon=((da.lon + 180) % 360) - 180).sortby("lon")
    da = da.sel(**box).sel(time=slice(f"{years[0]}-01-01", f"{years[1]}-12-31"))
    units = da.attrs.get("units", "")
    if units in ("kg m-2 s-1", "kg m**-2 s**-1"):
        da = da * 86400.0
    elif units not in ("mm", "mm day-1", "mm/day", "mm d-1", "mm day**-1"):
        raise ValueError(f"unexpected units {units!r}")
    if monthly_totals:
        da = da / da.time.dt.days_in_month
    ann = da.groupby("time.year").mean("time").load()
    ann = ann.assign_coords(member=member_labels(ds)).sortby("lat")
    return ann


def agreement(delta):
    """Atlas simple-method robustness: 1 where more than int(0.8 N) models share the sign of the mean."""
    n = delta.notnull().sum("member")
    mean = delta.mean("member")
    pos = (delta > 0).sum("member")
    neg = (delta < 0).sum("member")
    need = np.floor(n * 0.8)
    agree = xr.where(mean > 0, pos > need, xr.where(mean < 0, neg > need, True))
    return agree.where(mean.notnull(), True).astype("int8")


def country_means(field, weights_mask):
    """Area-weighted mean over each country; field has dims (..., lat, lon)."""
    out = {}
    w = np.cos(np.deg2rad(field.lat))
    for c, m in weights_mask.items():
        out[c] = field.where(m).weighted(w).mean(("lat", "lon"))
    return out


def main(data_dir, gwl_csv, out_dir):
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(gwl_csv, na_values=["NA"]).set_index("model_run")

    hist = annual_box(next((data_dir / "historical").glob("*.nc")), (1975, 2014))
    import regionmask
    ne = regionmask.defined_regions.natural_earth_v5_0_0.countries_50
    mask3d = ne.mask_3D(hist.lon, hist.lat)
    names = list(mask3d.names.values)
    cmask = {c: mask3d.isel(region=names.index(c)) for c in COUNTRIES}

    rows = []
    for gwl, exp, col in CASES:
        scen_file = next((data_dir / exp).glob("*.nc"))
        scen = annual_box(scen_file, (2015, 2100))
        # consistency check: first scenario decade against last historical decade
        common = [m for m in scen.member.values if m in hist.member.values]
        ratio = float(scen.sel(member=common, year=slice(2015, 2024)).mean()
                      / hist.sel(member=common, year=slice(2005, 2014)).mean())
        if ratio > 10:
            print(f"WARNING {exp}: values {ratio:.1f} times the historical ones; "
                  "file holds monthly totals, dividing by days in month", flush=True)
            scen = annual_box(scen_file, (2015, 2100), monthly_totals=True)
            ratio = float(scen.sel(member=common, year=slice(2015, 2024)).mean()
                          / hist.sel(member=common, year=slice(2005, 2014)).mean())
        if not 0.8 < ratio < 1.25:
            raise ValueError(f"{exp}: scenario/historical snowfall ratio {ratio:.2f}")
        years = table[col]
        ok = [m for m in scen.member.values
              if m in hist.member.values and m in years.index
              and np.isfinite(years[m]) and years[m] < 9000]
        series = xr.concat([hist.sel(member=ok), scen.sel(member=ok)], dim="year")
        windows = []
        for m in ok:
            n = int(years[m])
            windows.append(series.sel(member=m, year=slice(n - 9, n + 10)).mean("year"))
        future = xr.concat(windows, dim="member")
        central = xr.DataArray([int(years[m]) for m in ok], dims="member", coords={"member": ok})
        for bname, (b0, b1) in BASELINES.items():
            base_years = series.sel(year=slice(b0, b1))
            base = base_years.mean("year")
            delta = future - base
            # Atlas advanced method: per-model signal where |delta| > sqrt(2) 1.645 sd / sqrt(20)
            sigma = np.sqrt(2) * 1.645 * base_years.std("year", ddof=1) / np.sqrt(20)
            share_signal = 100 * (abs(delta) > sigma).sum("member") / delta.sizes["member"]
            simple = agreement(delta)
            advanced = xr.where(share_signal <= 66, 2, xr.where(simple == 1, 1, 3)).astype("int8")
            advanced.attrs["flag_meanings"] = "1 robust signal, 2 no change or no robust signal, 3 conflicting signals"
            ds = xr.Dataset({
                "delta": delta,                                   # per model, mm/day
                "baseline": base,                                 # per model, mm/day
                "delta_mean": delta.mean("member"),
                "baseline_mean": base.mean("member"),
                "robust": simple,
                "advanced": advanced,
                "central_year": central,
            })
            ds["rel_mean"] = 100 * ds.delta_mean / ds.baseline_mean.where(ds.baseline_mean > 0)
            ds.attrs.update(gwl=gwl, experiment=exp, baseline=bname, n_models=len(ok),
                            method="IPCC AR6 WGI Atlas: 20-yr GWL window [n-9,n+10], "
                                   "multi-model mean, simple robustness (>80% sign agreement)")
            ds.to_netcdf(out_dir / f"prsn_gwl{gwl}_{exp}_base{bname}.nc")
            cd = country_means(delta, cmask)
            cb = country_means(base, cmask)
            for c in COUNTRIES:
                rel = (100 * cd[c] / cb[c]).values
                for m, r, d in zip(ok, rel, cd[c].values):
                    rows.append(dict(gwl=gwl, experiment=exp, baseline=bname, country=c,
                                     model=m, delta_mm_day=float(d), rel_pct=float(r)))
            print(f"+{gwl} degC {exp} base {bname}: {len(ok)} models, central years "
                  f"{int(central.min())}-{int(central.max())} (median {int(central.median())})", flush=True)
    pd.DataFrame(rows).to_csv(out_dir / "country_means_per_model.csv", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:4])
