from plotly import graph_objects as go, subplots as sp

axis_col = 'rgba(0, 0, 0, 0.15)'
zero_col = 'rgba(0, 0, 0, 0.3)'
no_col = 'rgba(0, 0, 0, 0)'

xaxis_desc: dict = dict(linecolor=no_col, gridcolor=axis_col, zerolinecolor=zero_col, zerolinewidth=2)
yaxis_desc: dict = dict(linecolor=no_col, gridcolor=axis_col, zerolinecolor=zero_col, zerolinewidth=2)
layout = dict(
    autosize=True,
    width=1400,
    height=400,
    margin=dict(
        l=60, r=25, b=60, t=60, pad=5
    ),
    # paper_bgcolor="white",
    font_family="Times New Roman",
    font_color="black",
    font_size=20,
    plot_bgcolor='white',
    xaxis=dict(**xaxis_desc, ),
    yaxis=yaxis_desc,
)
