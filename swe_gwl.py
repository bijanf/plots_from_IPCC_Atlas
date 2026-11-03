"""Fact check of Sect. 2.4.7: CMIP6 snow water equivalent change over the Central Asian
mountains at +2, +3 and +4 degC, with the IPCC Atlas warming-level method.

Usage: python swe_gwl.py ESGF_DIR GWL_CSV ERA5_OROG ATLAS_DERIVED_DIR OUT_DIR
"""
import os
import sys
from pathlib import Path

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[v] = "4"

import numpy as np
import pandas as pd
import regionmask
import xarray as xr

CASES = [(2, "ssp245", "2_ssp245", "ssp2_4_5"), (3, "ssp370", "3_ssp370", "ssp3_7_0"),
         (4, "ssp585", "4_ssp585", "ssp5_8_5")]
COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Uzbekistan", "Turkmenistan"]
LON = np.arange(40.5, 95, 1.0)
LAT = np.arange(25.5, 60, 1.0)
BASE = (1981, 2010)


def to_grid(da):
    da = da.rename({k: v for k, v in {"latitude": "lat", "longitude": "lon"}.items() if k in da.dims})
    return da.interp(lon=LON, lat=LAT)


def annual_metrics(da):
    yr = da.time.dt.year
    return da.groupby(yr).mean("time"), da.groupby(yr).max("time")


def main(esgf, gwl_csv, orog, derived, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(gwl_csv, na_values=["NA"]).set_index("model_run")
    z = xr.open_dataset(orog)
    zvar = "z" if "z" in z else list(z.data_vars)[0]
    elev = z[zvar].squeeze(drop=True) / 9.80665
    elev = elev.rename({"latitude": "lat", "longitude": "lon"}).sortby("lat")
    elev = elev.coarsen(lat=4, lon=4, boundary="trim").mean().interp(lon=LON, lat=LAT)
    m3 = regionmask.defined_regions.natural_earth_v5_0_0.countries_50.mask_3D(LON, LAT)
    names = list(m3.names.values)
    ca = sum(m3.isel(region=names.index(c)) for c in COUNTRIES) > 0
    w = xr.DataArray(np.cos(np.deg2rad(LAT)), dims="lat", coords={"lat": LAT})
    domains = {"mountains >=1500 m": ca & (elev >= 1500), "mountains >=2000 m": ca & (elev >= 2000),
               "below 2000 m": ca & (elev < 2000)}

    rows = []
    for gwl, exp, col, atlas_exp in CASES:
        for run in table.index:
            n = table.loc[run, col]
            if not np.isfinite(n) or n > 9000:
                continue
            model, member = run.rsplit("_", 1)
            fh = Path(esgf) / f"snw_{model}_{member}_historical.nc"
            fs = Path(esgf) / f"snw_{model}_{member}_{exp}.nc"
            if not (fh.exists() and fs.exists()):
                continue
            try:
                da = xr.concat([xr.open_dataarray(fh, use_cftime=True), xr.open_dataarray(fs, use_cftime=True)], dim="time")
            except Exception as e:
                print(f"skip {model} {exp}: unreadable file ({type(e).__name__})", flush=True)
                continue
            da = to_grid(da)
            mean, peak = annual_metrics(da)
            n = int(n)
            perennial = da.sel(time=da.time.dt.year.isin(range(*BASE))).groupby("time.month").mean().min("month") > 1.0
            for metric, f in (("annual mean SWE", mean), ("peak SWE", peak)):
                base = f.sel(year=slice(*BASE)).mean("year")
                fut = f.sel(year=slice(n - 9, n + 10)).mean("year")
                for dname, dm in domains.items():
                    mk = dm & ~perennial & (base > 1.0)
                    b = base.where(mk).weighted(w).mean(("lat", "lon"))
                    d = (fut - base).where(mk).weighted(w).mean(("lat", "lon"))
                    rows.append(dict(gwl=gwl, model=model, metric=metric, domain=dname,
                                     rel_pct=float(100 * d / b), n_cells=int(mk.sum())))
            print(f"+{gwl} {model} done", flush=True)
        # snowfall on the same masks, from the Atlas recomputation
        ds = xr.open_dataset(Path(derived) / f"prsn_gwl{gwl}_{atlas_exp}_base1981-2010.nc")
        ds = ds.interp(lon=LON, lat=LAT, method="nearest")
        for dname, dm in domains.items():
            b = ds.baseline.where(dm).weighted(w).mean(("lat", "lon"))
            d = ds.delta.where(dm).weighted(w).mean(("lat", "lon"))
            for model, r in zip(ds.member.values, (100 * d / b).values):
                rows.append(dict(gwl=gwl, model=model, metric="snowfall (Atlas)", domain=dname,
                                 rel_pct=float(r), n_cells=int(dm.sum())))
    df = pd.DataFrame(rows)
    df.to_csv(out / "swe_snowfall_change_per_model.csv", index=False)
    s = df.groupby(["domain", "metric", "gwl"]).rel_pct.agg(
        n="count", median="median", p10=lambda x: x.quantile(0.1), p90=lambda x: x.quantile(0.9)).round(0)
    s.to_csv(out / "swe_snowfall_change_summary.csv")
    print(s.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:6])
