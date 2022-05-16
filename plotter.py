# Plot related functions
# Time-stamp: <2022-05-16 15:29:42 zshuang>
import seaborn as sns
from matplotlib import pyplot as plt
from io import BytesIO
from mapper import STATION_PALETTE
import pandas as pd

def compute_width(height, col_width, nstations, page=1, perpage=10):
    """Compute the width of a figure. 

    Streamlit sizes a figure by width.  Our figure has a fixed height
    and variable width (corresponding to # of pay stations)

    """
    div,mod = divmod(nstations, perpage) # e.g., nstations = 23, perpage = 10, divmod = 2,3

    if div >= page:
        ncol = perpage
    elif page == div+1:
        ncol = mod
    else:
        ncol = 0

    return (ncol+1) * col_width * height # ncol + 1 to account for y tick labels
    

def time_to_y(time, t0='08:00', freq='5min'):
    """ convert a time (hr:min) to y value for plot on the heatmap """
    return (pd.to_datetime(time) - pd.to_datetime(t0))/freq

def plot_predictions(predictions, figsize, page=1, perpage=10, label_palette=STATION_PALETTE,
                     hline=None):
    """ plot predictions 
    
    If more than <perpage> stations, only plot <page>'th page
    hrule: if provided, plot a red horizontal line at the given time

    """
    
    nstations = len(predictions.columns)
    
    # https://seaborn.pydata.org/generated/seaborn.diverging_palette.html
    # colomap for probabilities
    cmap_proba = sns.diverging_palette(275,150,s=80,l=55,n=9,as_cmap=True)
    
    # https://seaborn.pydata.org/tutorial/color_palettes.html
    # color_palette for labels
    cmap_labels = sns.color_palette(label_palette, n_colors=nstations)
    

    if nstations > perpage:
        start = (page-1) * perpage
        end = start + perpage
        if end >= nstations:
            end = nstations
        predictions = predictions.iloc[:,start:end]
    

    
    #figsize = (col_width * height * min(nstations, perpage), height)

    fig = plt.figure(figsize=figsize, dpi=100, constrained_layout=True)
    ax = sns.heatmap(predictions, cmap=cmap_proba,
                    linewidth=0.004, linecolor='white',
                    cbar=None, vmin=0, vmax=1,
                    yticklabels=6, # every 30 min
                    ) 
    ax.tick_params(left=True) # plot tick marks on the time axis
    ax.set_yticklabels(ax.get_ymajorticklabels(), fontsize=16, rotation=0) # increase fontsize
    ax.ylabel=False
    
    # sample code for setting x label background color
    for i,tl in enumerate(ax.get_xticklabels()):
        tl.set_backgroundcolor(cmap_labels[i+(page-1)*perpage])
        tl.set_fontsize(16)

    if hline:
        y = time_to_y(hline)
        ax.hlines(y, *ax.get_xlim(), color='red', alpha=0.5)
    #plt.tight_layout(pad=2)
    #plt.tight_layout()

    # https://github.com/streamlit/streamlit/issues/3527
    # Use BytesIO to control image width
    buf = BytesIO()
    #fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    fig.savefig(buf, format='png', dpi=100)

    return buf

