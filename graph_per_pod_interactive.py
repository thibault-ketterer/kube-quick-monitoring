
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# CSV file location
input_file = "pod_metrics.csv"
# input_file = "pod_metrics.csv.old"

def load_data():
    # Read the CSV file
    df = pd.read_csv(input_file)

    # Ensure timestamp is sorted for smooth plotting
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp")
    return df

def create_graph():
    # Load data
    df = load_data()

    # Create subplots: one for CPU and one for Memory
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("CPU Usage (mCPU)", "Memory Usage (MiB)"))

    # Group by pod and add traces
    for pod_name, pod_data in df.groupby("pod_name"):
        # CPU Usage
        fig.add_trace(
            go.Scatter(
                x=pod_data["timestamp"],
                y=pod_data["cpu_mcpu"],
                mode="lines",
                name=pod_name,
                hoverinfo="text",
                text=[f"Pod: {pod_name}<br>CPU: {cpu}m" for cpu in pod_data["cpu_mcpu"]],
                legendgroup=pod_name,
                showlegend=False  # No legends to reduce clutter
            ),
            row=1, col=1
        )

        # Memory Usage
        fig.add_trace(
            go.Scatter(
                x=pod_data["timestamp"],
                y=pod_data["memory_mib"],
                mode="lines",
                name=pod_name,
                hoverinfo="text",
                text=[f"Pod: {pod_name}<br>Memory: {mem}MiB" for mem in pod_data["memory_mib"]],
                legendgroup=pod_name,
                showlegend=False  # No legends to reduce clutter
            ),
            row=2, col=1
        )

    # Update layout
    fig.update_layout(
        title="Per-Pod Resource Usage",
        xaxis_title="Time",
        yaxis_title="CPU Usage (mCPU)",
        yaxis2_title="Memory Usage (MiB)",
        hovermode="x unified",  # Hover shows only the nearest trace
        height=800,
        template="plotly_white"
    )

    # Show the interactive graph
    fig.show()

if __name__ == "__main__":
    create_graph()

