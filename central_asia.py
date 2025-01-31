import pygmt

def plot_topo_only_land():
    """
    Plot topography over land only, assigning any below-sea-level elevations
    to the color bin at 0 m. Oceans and large lakes are shown in solid blue,
    while small lakes are omitted. Labels major Central Asian countries.
    """

    # Define the map region
    minlon, maxlon = 43, 89
    minlat, maxlat = 34, 56

    fig = pygmt.Figure()

    # Create a custom CPT with the specified elevation ranges and colors

    # Define the CPT file content
    def create_custom_cpt():
        cpt_content = """\
    # Elevation (m) Color Palette Table (CPT)
    0 145/167/140 200 145/167/140
    200 161/184/155 500 161/184/155
    500 188/206/182 1000 188/206/182
    1000 214/210/175 2000 214/210/175
    2000 205/188/139 3000 205/188/139
    3000 176/161/130 4000 176/161/130
    4000 214/208/189 5000 214/208/189
    5000 239/242/239 6000 239/242/239
    6000 255/255/255 8000 255/255/255
    B 145/167/140
    F 250/250/250
    N 128/128/128
    """
        with open("custom.cpt", "w") as f:
            f.write(cpt_content)

    create_custom_cpt()  # Call this function before using makecpt()


    # Use the custom CPT in PyGMT
    pygmt.makecpt(
    cmap="custom.cpt",
    continuous=True
    )



    # Plot global relief with hillshading
    fig.grdimage(
        grid="@earth_relief_30s",
        region=[minlon, maxlon, minlat, maxlat],
        projection="M6i",
        shading=0.001,
        frame='a'
    )

    # Paint large water bodies in the specified color
    fig.coast(
        region=[minlon, maxlon, minlat, maxlat],
        projection="M6i",
        borders="1/0.1p",
        shorelines=True,
        rivers="0-2/1p,#5f92b7",  # River network color
        land=None,
        water="#cfe6f5",  # Water bodies color
        lakes="#cfe6f5",
        area_thresh="90000",  # skip small lakes
        frame="a"
    )

    # Add a color bar with custom elevation labels
    fig.colorbar(
        frame=['x+lElevation (m)'],  # Label for the color bar
    )

    # Label some major Central Asian countries (approx. coordinates)
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
            font="10p,Helvetica,#000000",  # Labels in black
            justify="CM"
        )

    # Save the figure
    fig.savefig("central_asia_land_topo.png", crop=True, dpi=300)

if __name__ == "__main__":
    plot_topo_only_land()
