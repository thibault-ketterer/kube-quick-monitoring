
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd

data = None

def setdata(df):
    global data
    data = df

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
    print("got data")
    print(df)
    # Calculate total usage per pod for the given metric
    usage = df.groupby("pod_name")[metric].sum()

    # Get the top N pod names
    top_pods = usage.nlargest(top_n).index.tolist()

    # Filter the original dataframe for these top pods
    return df[df["pod_name"].isin(top_pods)]

def update_graph_area_stacked(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    Displays data as a stacked area chart with a 5-minute average.
    """
    filtered_data = all_filters(data, metric=metric, top_n=top_n)

    # Sort pods by the total metric to ensure the biggest consumer is on top
    pod_totals = filtered_data.groupby("pod_name")[metric].sum().sort_values(ascending=False)
    filtered_data["pod_name"] = pd.Categorical(filtered_data["pod_name"], categories=pod_totals.index, ordered=True)
    filtered_data = filtered_data.sort_values(by=["timestamp", "pod_name"])

    # Create area traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name", observed=False):
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

def all_filters(data, metric, top_n):
    """
    apply top pod filter
    then apply resample on 5 minutes
    """
    # Filter the top N pods
    filtered_data = get_top_pods(data, metric=metric, top_n=top_n)

    # Ensure data is sorted by timestamp
    # filtered_data["timestamp"] = pd.to_datetime(filtered_data["timestamp"])
    filtered_data.loc[:, "timestamp"] = pd.to_datetime(filtered_data["timestamp"])
    filtered_data = filtered_data.sort_values(by="timestamp")

    # Compute 5-minute averages while preserving spikes
    filtered_data = (
        filtered_data.set_index("timestamp")
        .groupby("pod_name")[metric]
        .resample("5min")
        .max()
        .reset_index()
    )
    return filtered_data


# bar mode
def update_graph_bar(metric, top_n):
    """
    Update the graph based on the selected metric and top N pods.
    Displays data as a stacked bar chart with a 5-minute average.
    """
    filtered_data = all_filters(data, metric=metric, top_n=top_n)

    # Create bar traces for each pod
    traces = []
    for pod_name, pod_data in filtered_data.groupby("pod_name", observed=False):
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
    for pod_name, pod_data in filtered_data.groupby("pod_name", observed=False):
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
