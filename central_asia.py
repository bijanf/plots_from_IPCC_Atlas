import pygmt

def plot_topo_only_land():
    """
    Plot topography over land only, assigning any below-sea-level elevations
    to the color bin at 0 m. Oceans and large lakes are shown in solid blue,
    while small lakes are omitted. Labels major Central Asian countries.
    (No triangular tip on the left side of the color bar due to GMT version constraints.)
    """

    # 1) Define the map region
    minlon, maxlon = 43, 89
    minlat, maxlat = 34, 56

    fig = pygmt.Figure()

    # 2) Create a custom CPT from -0.00001 to 8000 m,
    #    forcing anything < 0 to map to the color at 0 m.
    pygmt.makecpt(
        cmap="topo",
        series="-0.00001/8000/1000",
        continuous=True
    )

    # 3) Plot global relief with hillshading; negative elevations
    #    all use the 0-m color from the CPT.
    fig.grdimage(
        grid="@earth_relief_30s",
        region=[minlon, maxlon, minlat, maxlat],
        projection="M6i",
        shading=True,
        frame=True
    )

    # 4) Paint large water bodies in blue, skipping small lakes <5000 km^2.
    fig.coast(
        region=[minlon, maxlon, minlat, maxlat],
        projection="M6i",
        borders="1/0.5p",
        shorelines=True,
        rivers="0-2/1p,blue",
        land=None,
        water="lightblue",
        lakes="lightblue",
        area_thresh="90000",  # skip small lakes
        frame=True
    )

    # 5) Add a color bar (without triangular tip).
    #    For older GMT (<6.4), "triangle='l'" is unsupported, so we omit that.
    fig.colorbar(
        frame=['+l"Elevation (m)"']  # label for the color bar
    )

    # 6) Label some major Central Asian countries (approx. coordinates)
    country_positions = {
        "Kazakhstan":   (66, 49),
        "Uzbekistan":   (63, 42),
        "Turkmenistan": (57, 39),
        "Kyrgyzstan":   (74, 42),
        "Tajikistan":   (71, 38),
    
    
    }

    for country, (cx, cy) in country_positions.items():
        fig.text(
            x=cx, y=cy,
            text=country,
            region=[minlon, maxlon, minlat, maxlat],
            projection="M6i",
            font="15p,Helvetica,black",
            justify="CM"
        )

    # 7) Save the figure
    fig.savefig("central_asia_land_topo.pdf", crop=True, dpi=300)

if __name__ == "__main__":
    plot_topo_only_land()
