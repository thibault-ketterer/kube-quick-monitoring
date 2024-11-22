import os
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd

# Initialize Dash app
app = Dash(__name__)

base_dir = "data"

from graph_callbacks import update_graph_lines, update_graph_area_stacked, update_graph_bar, setdata

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

# for default file selection
file_options = [{"label": f, "value": f} for f in get_available_files()]

# Layout for the Dash
app.layout = html.Div([
    html.H1("Top Pods Resource Usage"),
    html.Div([
        html.Label("Select Date File:"),
        dcc.Dropdown(
            id="file_selector",
            options=file_options,
            value=file_options[-1]['value'],
            placeholder="Select a date file for analysis",
            clearable=False,
            multi=True,
        )
    ]),
    html.Div([
        html.Label("Select Namespace:"),
        dcc.Dropdown(
            id="namespace_selector",
            options=[],  # This will be populated dynamically based on the selected file
            value=None,
            placeholder="Select a namespace",
            clearable=True,
            multi=True,
        )
    ]),
    html.Div([
        html.Label("Search Pod Name:"),
        dcc.Input(
            id="pod_name_search",
            type="text",
            placeholder="Enter pod name for partial match",
            debounce=True,
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

# Function to load data based on selected file(s)
def load_data(selected_files):
    if selected_files is not None:
        # Initialize an empty DataFrame
        combined_df = pd.DataFrame()

        # If selected_files is a single file, convert it to a list
        if isinstance(selected_files, str):
            selected_files = [selected_files]

        # Loop through each selected file and append to combined DataFrame
        for file in selected_files:
            input_file = os.path.join(base_dir, file)
            # Read the CSV file
            df = pd.read_csv(input_file)

            # Ensure timestamp is sorted for smooth plotting
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp")

            # Fill missing timestamp values with the last valid value
            df["timestamp"] = df["timestamp"].ffill()

            # Append to the combined DataFrame
            combined_df = pd.concat([combined_df, df], ignore_index=True)

        # Return the combined DataFrame
        return combined_df

    return pd.DataFrame()

# Callback to update namespace options based on selected file
@app.callback(
    Output("namespace_selector", "options"),
    Input("file_selector", "value")
)
def update_namespace_options(selected_file):
    df = load_data(selected_file)
    namespaces = df["namespace"].unique() if not df.empty else []
    return [{"label": namespace, "value": namespace} for namespace in namespaces] + [{"label": "-- ALL --", "value": ""}]

# Callback to update the graph based on user inputs
@app.callback(
    Output("pod-usage-graph", "figure"),
    Input("file_selector", "value"),
    Input("namespace_selector", "value"),
    Input("pod_name_search", "value"),
    Input("metric", "value"),
    Input("top_n", "value"),
    Input("graph_type", "value")
)
def update_graph(selected_file, namespace, pod_name_search, metric, top_n, graph_type):
    """
    Dynamically switch between graph types based on the selected option.
    """
    data = load_data(selected_file)

    # Filter by namespace if selected
    if namespace:
        if isinstance(namespace, str):
            data = data[data["namespace"] == namespace]
        else:
            data = data[data["namespace"].isin(namespace)]

    # Filter by pod name using partial match if search term is provided
    if pod_name_search:
        data = data[data["pod_name"].str.contains(pod_name_search, case=False, na=False)]

    setdata(data)

    if graph_type == "lines":
        return update_graph_lines(metric, top_n)
    elif graph_type == "area_stacked":
        return update_graph_area_stacked(metric, top_n)
    elif graph_type == "bar_stacked":
        return update_graph_bar(metric, top_n)
    else:
        # Default fallback (shouldn't happen with valid options)
        return {"data": [], "layout": {"title": "Invalid Graph Type"}}


if __name__ == "__main__":
    app.run_server(debug=True)

