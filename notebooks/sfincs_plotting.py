"""
HydroMT-SFINCS utilities functions for plotting
"""

from typing import Tuple
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from hydromt_sfincs.plots import plot_basemap
from IPython.display import HTML
from matplotlib import animation
from pathlib import Path

# Check if FFmpeg is already installed
def check_install_ffmpeg(path: str = "./ffmpeg"):
    from local_ffmpeg import is_installed, install
    import sys
    if not is_installed(path = path):
        # Install FFmpeg if not found
        success, message = install(path=path)
        if success:
            print(message)  # FFmpeg installed successfully
        else:
            print(f"Error: {message}")
    else:
        print(f"FFmpeg is already installed at {path}")
    # Add FFmpeg to system path
    sys.path.append(Path(path).resolve().as_posix())

def make_animation(
    da_h: xr.DataArray, 
    geoms: dict, 
    bmap: str = "sat",
    zoomlevel: int = "auto",
    plot_bounds: bool = False,
    figsize: Tuple[int] = None,
    step=1, 
    cmap = 'BuPu',
    vmin=  0,
    vmax= 3,
    ):
    # check_install_ffmpeg()

    def update_plot(i, da_h, cax_h):
        da_h = da_h.isel(time=i)
        t = da_h.time.dt.strftime("%d-%B-%Y %H:%M:%S").item()
        ax.set_title(f"SFINCS water depth {t}")
        cax_h.set_array(da_h.values.ravel())

    fig, ax = plot_basemap(
        ds = da_h.to_dataset(),
        geoms = geoms,
        variable="",
        plot_bounds=plot_bounds,
        bmap=bmap,
        zoomlevel=zoomlevel,
        figsize=figsize,
    )

    cbar_kwargs = {"shrink": 0.6, "anchor": (0, 0)}

    cax_h = da_h.isel(time=0).plot(
        x="x", y="y", ax=ax, vmin=vmin, vmax=vmax, 
        cmap=cmap,  cbar_kwargs=cbar_kwargs
    )
    plt.close()  # to prevent double plot

    ani = animation.FuncAnimation(
        fig,
        update_plot,
        frames=np.arange(0, da_h.time.size, step),
        interval=250,  # ms between frames
        fargs=(da_h, cax_h,),
    )

    # to show in notebook:
    return HTML(ani.to_jshtml())