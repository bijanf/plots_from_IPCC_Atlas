"""Fetch CMIP6 monthly snow water equivalent (snw, LImon) over Central Asia from ESGF
via OPeNDAP subsetting, for the models of the IPCC Atlas warming-level table.

Usage: python fetch_esgf_snw.py GWL_CSV OUTDIR
"""
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import xarray as xr

SEARCH = "https://esgf-data.dkrz.de/esg-search/search"
EXPS = {"historical": (1975, 2014), "ssp245": (2015, 2100), "ssp370": (2015, 2100), "ssp585": (2015, 2100)}
NODE_ORDER = ["esgf3.dkrz.de", "esgf.ceda.ac.uk", "vesg.ipsl.upmc.fr", "esgf-node.ornl.gov"]
LON = (40, 95)
LAT = (25, 60)


def search(model, exp, member):
    q = dict(type="File", project="CMIP6", source_id=model, experiment_id=exp, member_id=member,
             variable_id="snw", table_id="LImon", latest="true", distrib="true",
             format="application/solr+json", limit="500", fields="title,url,data_node")
    with urllib.request.urlopen(SEARCH + "?" + urllib.parse.urlencode(q), timeout=120) as r:
        docs = json.load(r)["response"]["docs"]
    files = {}
    for d in docs:
        url = [u.split("|")[0] for u in d.get("url", []) if u.endswith("OPENDAP")]
        if not url:
            continue
        rank = NODE_ORDER.index(d["data_node"]) if d["data_node"] in NODE_ORDER else 99
        files.setdefault(d["title"], []).append((rank, url[0].removesuffix(".html")))
    return [[u for _, u in sorted(files[t])] for t in sorted(files)]   # replicas, best node first


def subset(url, y0, y1):
    ds = xr.open_dataset(url, decode_times=True, use_cftime=True)
    da = ds["snw"]
    lon = da["lon"]
    da = da.assign_coords(lon=((lon + 180) % 360) - 180).sortby("lon") if float(lon.max()) > 180 else da
    da = da.sortby("lat").sel(lon=slice(*LON), lat=slice(*LAT))
    years = da.time.dt.year
    da = da.sel(time=(years >= y0) & (years <= y1))
    return da.load() if da.sizes["time"] else None


def fetch(model, member, exp, out):
    target = out / f"snw_{model}_{member}_{exp}.nc"
    if target.exists():
        try:
            xr.open_dataarray(target).close()
            return f"have {target.name}"
        except Exception:
            target.unlink()                      # partial file from an interrupted run
    try:
        urls = search(model, exp, member)
        if not urls:
            return f"NONE {model} {member} {exp}"
        parts = []
        for replicas in urls:
            err = None
            for u in replicas:
                try:
                    p = subset(u, *EXPS[exp])
                    break
                except OSError as e:
                    err, p = e, "fail"
            if isinstance(p, str):
                raise err
            if p is not None:
                parts.append(p)
        da = xr.concat(parts, dim="time").sortby("time")
        da.to_netcdf(target)
        return f"ok {model} {member} {exp} {da.sizes['time']} months"
    except Exception as e:
        return f"FAIL {model} {member} {exp} {type(e).__name__}: {str(e)[:150]}"


if __name__ == "__main__":
    table = pd.read_csv(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for run in table.model_run:
        model, member = run.rsplit("_", 1)
        for exp in EXPS:
            jobs.append((model, member, exp))
    # netCDF/HDF5 is not thread-safe: one process per worker, at most 4 (laptop cap)
    with ProcessPoolExecutor(max_workers=4) as pool:
        for msg in pool.map(fetch, *zip(*jobs), [out] * len(jobs)):
            print(msg, flush=True)
