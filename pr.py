import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import BoundaryNorm

# Load the data
data = xr.open_dataset('pr/map.nc')
pvalues = xr.open_dataset('pr/pvalue.nc')

# Extract variables
data_values = data['pr_trend']  # Main data variable for precipitation
pvalue_values = pvalues['pr_trend_pvalue']  # P-value variable

# Define bounding box for Central Asia (approx.)
lon_min, lon_max = 45, 90  # Longitude range
lat_min, lat_max = 30, 56  # Latitude range

# Subset the data
data_values = data_values.sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))
pvalue_values = pvalue_values.sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))

# Define a p-value threshold for significance
threshold = 0.10
significance_mask = pvalue_values > threshold  # Non-significant where p-value >= threshold

# Create grid for plotting
lon, lat = np.meshgrid(data_values['lon'], data_values['lat'])

# Define colormap with 10 discrete colors (brown to green)
cmap = plt.get_cmap('BrBG', 16)  # 10 discrete colors
norm = BoundaryNorm(np.linspace(-0.4, .4, 17), cmap.N)  # Define boundaries for 10 intervals

# Plotting
fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(10, 6))

# Use pcolor for the data values
pcm = ax.pcolor(lon, lat, data_values, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())

# Add black dots for non-significant areas
ax.scatter(lon[significance_mask], lat[significance_mask], color='black',
           s=1, transform=ccrs.PlateCarree(), label='Non-significant')

# Add country borders and Central Asia focus
ax.add_feature(cfeature.BORDERS, linestyle='-', edgecolor='black')
ax.add_feature(cfeature.COASTLINE)
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

# Add a tall colorbar
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.1, axes_class=plt.Axes)
cbar = plt.colorbar(pcm, cax=cax, orientation='vertical')
cbar.set_label('Precipitation Trend (mm/day per decade)')

# Add titles and labels
ax.set_title('ERA5 - Precipitation (pr) Trend mm/day per decade - 1980-2015 - Annual', pad=15)

# Save the figure as PNG with high resolution and no extra white space
plt.savefig('precipitation_trend_central_asia.png', dpi=300, bbox_inches='tight', pad_inches=0)

# Show the plot
plt.show()
