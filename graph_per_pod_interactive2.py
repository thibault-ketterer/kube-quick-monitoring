
import os
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd

# Initialize Dash app
app = Dash(__name__)

base_dir = "data"
data = None

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


# Helper function to get the available files
def get_available_files():
    files = []
    for year_month in os.listdir(base_dir):
        month_dir = os.path.join(base_dir, year_month)
        if os.path.isdir(month_dir):
            for file in os.listdir(month_dir):
                if file.startswith("pod_metrics_") and file.endswith(".csv"):
                    files.append(os.path.join(year_month, file))
    return sorted(files)

# Layout for the Dash app
app.layout = html.Div([
    html.H1("Top Pods Resource Usage"),
    html.Div([
        html.Label("Select Date File:"),
        dcc.Dropdown(
            id="file_selector",
            options=[{"label": f, "value": f} for f in get_available_files()],
            value=None,
            placeholder="Select a date file for analysis",
            clearable=False,
        )
    ]),
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
    html.Div([
        html.Label("Select Graph Type:"),
        dcc.Dropdown(
            id="graph_type",
            options=[
                {"label": "Line Chart", "value": "lines"},
                {"label": "Stacked Area Chart", "value": "area_stacked"},
                {"label": "Stack Bar Chart", "value": "bar_stacked"},
            ],
            value="lines",
            clearable=False,
        )
    ]),
    dcc.Graph(id="pod-usage-graph"),
])

# Function to load data based on selected file
def load_data(selected_file):
    if selected_file is not None:
        input_file = os.path.join(base_dir, selected_file)
        # Read the CSV file
        df = pd.read_csv(input_file)

        # Ensure timestamp is sorted for smooth plotting
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        return df
    return pd.DataFrame()

# Callback to update the graph based on user inputs
@app.callback(
    Output("pod-usage-graph", "figure"),
    Input("file_selector", "value"),
    Input("metric", "value"),
    Input("top_n", "value"),
    Input("graph_type", "value")
)
def update_graph(selected_file, metric, top_n, graph_type):
    """
    Dynamically switch between graph types based on the selected option.
    """
    global data
    data = load_data(selected_file)

    if graph_type == "lines":
        return update_graph_lines(metric, top_n)
    elif graph_type == "area_stacked":
        return update_graph_area_stacked(metric, top_n)
    elif graph_type == "bar_stacked":
        return update_graph_bar(metric, top_n)
    else:
        # Default fallback (shouldn't happen with valid options)
        return {"data": [], "layout": {"title": "Invalid Graph Type"}}

def update_graph_area_stacked(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    Displays data as a stacked area chart with a 5-minute average.
    """
    # Filter the top N pods
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Ensure data is sorted by timestamp
    filtered_data["timestamp"] = pd.to_datetime(filtered_data["timestamp"])
    filtered_data = filtered_data.sort_values(by="timestamp")

    # Compute 5-minute averages while preserving spikes
    filtered_data = (
        filtered_data.set_index("timestamp")
        .groupby("pod_name")[metric]
        .resample("5T")
        .max()
        .reset_index()
    )

    # Sort pods by the total metric to ensure the biggest consumer is on top
    pod_totals = filtered_data.groupby("pod_name")[metric].sum().sort_values(ascending=False)
    filtered_data["pod_name"] = pd.Categorical(filtered_data["pod_name"], categories=pod_totals.index, ordered=True)
    filtered_data = filtered_data.sort_values(by=["timestamp", "pod_name"])

    # Create area traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name"):
        traces.append(
            go.Scatter(
                x=pod_data["timestamp"],
                y=pod_data[metric],
                name=pod_name,
                hoverinfo="text",
                text=[
                    f"Pod: {pod_name}<br>{metric}: {val}"
                    for val in pod_data[metric]
                ],
                mode="lines",
                stackgroup="one"
            )
        )

    # Configure the figure layout
    layout = go.Layout(
        title=f"Top {top_n} Pods by {metric} (5-Minute Average)",
        xaxis_title="Time",
        yaxis_title="CPU (mCPU)" if metric == "cpu_mcpu" else "Memory (MiB)",
        hovermode="x unified",
        template="plotly_white"
    )

    return {"data": traces, "layout": layout}


# bar mode
def update_graph_bar(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    Displays data as a stacked bar chart with a 5-minute average.
    """
    # Filter the top N pods
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Ensure data is sorted by timestamp
    filtered_data["timestamp"] = pd.to_datetime(filtered_data["timestamp"])
    filtered_data = filtered_data.sort_values(by="timestamp")

    # Compute 5-minute averages while preserving spikes
    filtered_data = (
        filtered_data.set_index("timestamp")
        .groupby("pod_name")[metric]
        .resample("5T")
        .max()
        .reset_index()
    )

    # Create bar traces for each pod
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
        title=f"Top {top_n} Pods by {metric} (5-Minute Average)",
        barmode="stack",
        xaxis_title="Time",
        yaxis_title="CPU (mCPU)" if metric == "cpu_mcpu" else "Memory (MiB)",
        hovermode="x unified",
        template="plotly_white"
    )

    return {"data": traces, "layout": layout}

def update_graph_lines(metric, top_n):
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

