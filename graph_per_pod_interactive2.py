
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd

# Initialize Dash app
app = Dash(__name__)

from graph_per_pod_interactive import load_data
# Load data once
data = load_data()

def get_top_pods(df, metric="cpu_mcpu", top_n=20):
    """
    Filter the top N pods by a given metric (CPU or Memory).

    Parameters:
        df (DataFrame): The input data containing pod metrics.
        metric (str): The metric to filter by ("cpu_mcpu" or "memory_mib").
        top_n (int): The number of top pods to select.

    Returns:
        DataFrame: Filtered DataFrame containing only the top N pods.
    """
    # Calculate total usage per pod for the given metric
    usage = df.groupby("pod_name")[metric].sum()

    # Get the top N pod names
    top_pods = usage.nlargest(top_n).index.tolist()

    # Filter the original dataframe for these top pods
    return df[df["pod_name"].isin(top_pods)]


# Layout for the Dash app
app.layout = html.Div([
    html.H1("Top Pods Resource Usage"),
    html.Div([
        html.Label("Select Metric:"),
        dcc.Dropdown(
            id="metric",
            options=[
                {"label": "CPU (mCPU)", "value": "cpu_mcpu"},
                {"label": "Memory (MiB)", "value": "memory_mib"},
            ],
            value="cpu_mcpu",
            clearable=False,
        )
    ]),
    html.Div([
        html.Label("Number of Top Pods:"),
        dcc.Slider(
            id="top_n",
            min=1,
            max=50,
            step=1,
            value=20,
            marks={i: str(i) for i in range(1, 51, 5)}
        )
    ]),
    dcc.Graph(id="pod-usage-graph"),
])

# Callback to update the graph based on inputs
@app.callback(
    Output("pod-usage-graph", "figure"),
    [Input("metric", "value"), Input("top_n", "value")]
)

def update_graph_area(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    Displays data as a stacked area chart.
    """
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Ensure data is sorted by timestamp for cumulative stacking
    filtered_data = filtered_data.sort_values(by="timestamp")

    # Prepare the cumulative stack
    timestamps = filtered_data["timestamp"].unique()
    cumulative_values = pd.DataFrame(index=timestamps)
    cumulative_values["timestamp"] = timestamps

    # Create traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name"):
        pod_values = pod_data.set_index("timestamp")[metric].reindex(timestamps, fill_value=0)

        if cumulative_values.shape[1] == 1:  # First pod (no cumulative stack yet)
            cumulative_values[pod_name] = pod_values
        else:  # Subsequent pods add to the cumulative stack
            cumulative_values[pod_name] = cumulative_values.iloc[:, -1] + pod_values

        # Add trace for the pod
        traces.append(
            go.Scatter(
                x=timestamps,
                y=cumulative_values[pod_name],
                mode="lines",
                fill="tonexty",  # Stack on top of the previous trace
                name=pod_name,
                hoverinfo="text",
                text=[
                    f"Pod: {pod_name}<br>{metric}: {val}"
                    for val in pod_values
                ]
            )
        )

    # Configure the figure layout
    layout = go.Layout(
        title=f"Top {top_n} Pods by {metric}",
        xaxis_title="Time",
        yaxis_title="CPU (mCPU)" if metric == "cpu_mcpu" else "Memory (MiB)",
        hovermode="x unified",  # Unified hover for stacked areas
        template="plotly_white"
    )

    return {"data": traces, "layout": layout}

# bar mode
def update_graph_bar(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    """
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Create traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name"):
        traces.append(
            go.Bar(
                x=pod_data["timestamp"],
                y=pod_data[metric],
                name=pod_name,
                hoverinfo="text",
                text=[
                    f"Pod: {pod_name}<br>{metric}: {val}"
                    for val in pod_data[metric]
                ]
            )
        )

    # Configure the figure layout
    layout = go.Layout(
        title=f"Top {top_n} Pods by {metric}",
        barmode="stack",
        xaxis_title="Time",
        yaxis_title="CPU (mCPU)" if metric == "cpu_mcpu" else "Memory (MiB)",
        hovermode="x unified",
        template="plotly_white"
    )

    return {"data": traces, "layout": layout}


def update_graph_line(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    """
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Create traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name"):
        traces.append(
            go.Scatter(
                x=pod_data["timestamp"],
                y=pod_data[metric],
                mode="lines",
                name=pod_name,
                hoverinfo="text",
                text=[
                    f"Pod: {pod_name}<br>{metric}: {val}"
                    for val in pod_data[metric]
                ]
            )
        )

    # Configure the figure layout
    layout = go.Layout(
        title=f"Top {top_n} Pods by {metric}",
        xaxis_title="Time",
        yaxis_title="CPU (mCPU)" if metric == "cpu_mcpu" else "Memory (MiB)",
        hovermode="x unified",
        template="plotly_white"
    )

    return {"data": traces, "layout": layout}


if __name__ == "__main__":
    app.run_server(debug=True)

