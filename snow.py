import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import BoundaryNorm

def plot_snow_changes_with_robustness(
    data_file, robustness_file, output_file, title, label, 
    vmin=-1.0, vmax=1.0, robustness_threshold=0.7
):
    # Load the data and robustness
    data = xr.open_dataset(data_file)
    robustness = xr.open_dataset(robustness_file)

    # Extract variables
    data_values = data['prsn_anom']  # Snow anomaly variable
    robustness_values = robustness['prsn_anom_robustness']  # Robustness variable

    # Define bounding box for Central Asia
    lon_min, lon_max = 45, 90  # Longitude range
    lat_min, lat_max = 30, 56  # Latitude range

    # Subset the data and robustness
    data_values = data_values.sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))
    robustness_values = robustness_values.sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))

    # Define a robustness mask (non-robust regions)
    robustness_mask = robustness_values < robustness_threshold  # Non-robust where robustness < threshold

    # Create grid for plotting
    lon, lat = np.meshgrid(data_values['lon'], data_values['lat'])

    # Define colormap with 10 discrete colors (blue to white to brown for snow changes)
    cmap = plt.get_cmap('BrBG', 14)  # 10 discrete colors, centered on 0
    norm = BoundaryNorm(np.linspace(vmin, vmax, 15), cmap.N)  # Define boundaries for 10 intervals

    # Plotting
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(10, 6))

    # Use pcolor for the data values
    pcm = ax.pcolor(lon, lat, data_values, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())

    # Add red dots for non-robust areas
    ax.scatter(
        lon[robustness_mask], lat[robustness_mask], color='black',
        s=1, transform=ccrs.PlateCarree(), label='Non-robust'
    )

    # Add country borders and Central Asia focus
    ax.add_feature(cfeature.BORDERS, linestyle='-', edgecolor='black')
    ax.add_feature(cfeature.COASTLINE)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # Add a tall colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(pcm, cax=cax, orientation='vertical')
    cbar.set_label(label)

    # Add titles and labels
    ax.set_title(title, pad=15)

    # Save the figure as PNG with high resolution and no extra white space
    plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0)

    # Show the plot
    plt.show()


# Example usage for snow_4
plot_snow_changes_with_robustness(
    data_file='snow_4/map.nc',
    robustness_file='snow_4/robustness.nc',
    output_file='snow_anomaly_central_asia_ssp5_8_5_4C_with_robustness.png',
    title='Snow Anomaly Changes with Robustness (SSP5-8.5, 4°C Warming, 1995-2014 Ref.) - Annual (18 Models)',
    label='Snow Anomaly (mm/day)',
    vmin=-.7, vmax=.7
)
# Example usage for snow_3
plot_snow_changes_with_robustness(
    data_file='snow_3/map.nc',
    robustness_file='snow_3/robustness.nc',
    output_file='snow_anomaly_central_asia_ssp3_7_0_3C_with_robustness.png',
    title='Snow Anomaly Changes with Robustness (SSP3-7.0, 3°C Warming, 1995-2014 Ref.) - Annual (23 Models)',
    label='Snow Anomaly (mm/day)',
    vmin=-.7, vmax=.7
)

# Plot for snow_2
plot_snow_changes_with_robustness(
    data_file='snow_2/map.nc',
    robustness_file='snow_2/robustness.nc',
    output_file='snow_anomaly_central_asia_ssp2_4_5_2C_with_robustness.png',
    title='Snow Anomaly Changes with Robustness (SSP2-4.5, 2°C Warming, 1995-2014 Ref.) - Annual (29 Models)',
    label='Snow Anomaly (mm/day)',
    vmin=-.7, vmax=.7
)