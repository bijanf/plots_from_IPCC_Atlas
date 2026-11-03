"""Download CMIP6 snowfall from the dataset that underpins the IPCC AR6 WGI Interactive Atlas.

Source: Copernicus Climate Data Store, "Gridded monthly climate projection dataset
underpinning the IPCC AR6 Interactive Atlas", doi:10.24381/cds.5292a2b0 (CC BY 4.0).
Variable: monthly mean of daily accumulated snowfall precipitation (prsn, mm day-1,
water equivalent), CMIP6, one member per model, 1 degree global grid.

Needs a CDS account with the dataset licence accepted and ~/.cdsapirc in place.

Usage:
    python download_atlas_snowfall.py OUTDIR
"""
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cdsapi

DATASET = "projections-climate-atlas"
REQUESTS = {
    "historical": "1850-2014",
    "ssp2_4_5": "2015-2100",
    "ssp3_7_0": "2015-2100",
    "ssp5_8_5": "2015-2100",
}


def fetch(experiment, period, outdir):
    target = outdir / f"cmip6_prsn_{experiment}.zip"
    if not target.exists():
        cdsapi.Client(quiet=True).retrieve(
            DATASET,
            {
                "origin": "cmip6",
                "experiment": experiment,
                "domain": "global",
                "period": period,
                "variable": "monthly_mean_of_daily_accumulated_snowfall_precipitation",
            },
            str(target),
        )
    with zipfile.ZipFile(target) as z:
        z.extractall(outdir / experiment)
    print(experiment, "done:", sorted(p.name for p in (outdir / experiment).iterdir()), flush=True)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(fetch, e, p, out) for e, p in REQUESTS.items()]
        for j in jobs:
            j.result()
