import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.colors import LightSource, BoundaryNorm, ListedColormap
import numpy as np
import xarray as xr
import os
import requests
import gzip
import shutil

def download_etopo_data():
    """Download ETOPO1 elevation data."""
    cache_dir = os.path.expanduser("~/.gmt_data")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "ETOPO1_Ice_g_gmt4.grd")

    if os.path.exists(cache_file):
        print(f"Using cached: {cache_file}")
        return cache_file

    url = "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/ice_surface/grid_registered/netcdf/ETOPO1_Ice_g_gmt4.grd.gz"
    gz_file = cache_file + ".gz"

    print(f"Downloading ETOPO1 data (~400MB compressed)...")
    response = requests.get(url, stream=True, timeout=600)
    response.raise_for_status()

    with open(gz_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Extracting...")
    with gzip.open(gz_file, 'rb') as f_in:
        with open(cache_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(gz_file)

    print(f"Saved to: {cache_file}")
    return cache_file

def plot_topo_only_land():
    """
    Plot high-resolution topography with hillshading.
    """
    # Define the map region
    minlon, maxlon = 43, 89
    minlat, maxlat = 34, 56

    # Try to get elevation data
    try:
        dem_file = download_etopo_data()
        dem_full = xr.open_dataset(dem_file)
        # Subset to our region (ETOPO1 has y from -90 to 90)
        dem = dem_full['z'].sel(x=slice(minlon, maxlon), y=slice(minlat, maxlat))
        has_dem = True
        print(f"DEM shape: {dem.shape}")
    except Exception as e:
        print(f"Could not load DEM: {e}")
        has_dem = False

    # Calculate proper aspect ratio for the region
    lat_center = (minlat + maxlat) / 2
    aspect = 1 / np.cos(np.radians(lat_center))
    fig_width = 12
    fig_height = fig_width * (maxlat - minlat) / (maxlon - minlon) * aspect

    fig = plt.figure(figsize=(fig_width, fig_height))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([minlon, maxlon, minlat, maxlat], crs=ccrs.PlateCarree())

    # Custom elevation colormap (matching your original)
    colors_elev = [
        '#91a78c',  # 0-200m
        '#a1b89b',  # 200-500m
        '#bcceb6',  # 500-1000m
        '#d6d2af',  # 1000-2000m
        '#cdbc8b',  # 2000-3000m
        '#b0a182',  # 3000-4000m
        '#d6d0bd',  # 4000-5000m
        '#eff2ef',  # 5000-6000m
        '#ffffff',  # 6000-8000m
    ]
    elevations = [0, 200, 500, 1000, 2000, 3000, 4000, 5000, 6000, 8000]
    cmap_elev = ListedColormap(colors_elev)
    norm_elev = BoundaryNorm(elevations, cmap_elev.N)

    if has_dem:
        # Get the data as numpy array
        elev_data = dem.values
        lons = dem.x.values
        lats = dem.y.values

        # Create hillshade
        ls = LightSource(azdeg=315, altdeg=45)

        # Keep negative values for ocean/sea coloring
        # Water bodies (negative elevation) will be colored separately
        elev_clipped = np.clip(elev_data, 0, 8000)

        # Create a mask for Caspian Sea only (large water body with elevation < -20m)
        # Small negative values on land should keep their terrain color
        water_mask = elev_data < -20

        # Create RGB from colormap
        rgb = cmap_elev(norm_elev(elev_clipped))

        # Set water color for negative elevations (Caspian Sea, etc.)
        water_color = np.array([0.81, 0.90, 0.96, 1.0])  # #cfe6f5
        rgb[water_mask] = water_color

        # Apply hillshading
        shaded = ls.shade_rgb(rgb, elev_data.astype(float), vert_exag=0.03, blend_mode='soft')

        # Also color water areas without hillshading effect
        for i in range(3):
            shaded[:, :, i][water_mask] = water_color[i]

        # Plot the shaded relief (flip y-axis with origin='lower')
        ax.imshow(shaded, extent=[lons.min(), lons.max(), lats.min(), lats.max()],
                  transform=ccrs.PlateCarree(), origin='lower', aspect='auto')
    else:
        # Fallback to stock image
        ax.stock_img()

    # Add high-res features
    ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_0_boundary_lines_land', '10m',
                                                 edgecolor='black', facecolor='none', linewidth=0.8))
    ax.add_feature(cfeature.NaturalEarthFeature('physical', 'lakes', '10m',
                                                 edgecolor='#5f92b7', facecolor='none', linewidth=0.8))
    # Add coastline for Caspian Sea outline
    ax.add_feature(cfeature.NaturalEarthFeature('physical', 'coastline', '10m',
                                                 edgecolor='#5f92b7', facecolor='none', linewidth=0.8))

    # Add gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {'size': 10}
    gl.ylabel_style = {'size': 10}

    # Label countries
    country_positions = {
        "Kazakhstan":   (66, 49),
        "Uzbekistan":   (63, 42),
        "Turkmenistan": (57, 39),
        "Kyrgyzstan":   (74, 42),
        "Tajikistan":   (71, 38),
    }

    for country, (cx, cy) in country_positions.items():
        ax.text(cx, cy, country, transform=ccrs.PlateCarree(),
                fontsize=11, fontweight='normal', color='black',
                ha='center', va='center')

    # Label mountain ranges in dark red
    mountain_positions = {
        "Tien Shan": (79, 42),
        "Pamir":     (72, 38.5),
    }

    for mountain, (mx, my) in mountain_positions.items():
        ax.text(mx, my, mountain, transform=ccrs.PlateCarree(),
                fontsize=11, fontweight='bold', color='#8B0000',
                ha='center', va='center')

    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap_elev, norm=norm_elev)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', shrink=0.7, pad=0.02, aspect=30)
    cbar.set_label('Elevation (m)', fontsize=11)
    cbar.ax.tick_params(labelsize=9)

    plt.savefig("central_asia_land_topo.png", dpi=300, bbox_inches='tight', pad_inches=0.1)
    print("Saved: central_asia_land_topo.png")
    plt.close()

if __name__ == "__main__":
    plot_topo_only_land()
