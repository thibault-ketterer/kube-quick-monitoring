
import os
import time
import csv
from datetime import datetime
from kubernetes import client, config

# Configuration for debugging
debug = True

# Base directory for logs
base_dir = "data"

# Global CSV writer and file
csv_writer, csv_file, current_day = None, None, None

# Initialize Kubernetes API
config.load_kube_config()
api = client.CustomObjectsApi()

# Function to set up the global CSV writer
def setup_csv_writer():
    """
    Sets up the global csv_writer and file for the current date.
    """
    global csv_writer, csv_file, current_day

    current_date = datetime.now()
    year_month = current_date.strftime("%Y-%m")
    day = current_date.strftime("%Y-%m-%d")

    # Update file if the day has changed
    if current_day != day:
        close_csv_writer()
        current_day = day

        # Create directory for the current month if it doesn't exist
        month_dir = os.path.join(base_dir, year_month)
        os.makedirs(month_dir, exist_ok=True)
        output_file = os.path.join(month_dir, f"pod_metrics_{day}.csv")
        csv_file = open(output_file, "a", newline="")
        csv_writer = csv.writer(csv_file)

        # Write header if file is new
        if csv_file.tell() == 0:
            csv_writer.writerow(["timestamp", "namespace", "pod_name", "cpu_mcpu", "memory_mib"])

# Function to close the global CSV file
def close_csv_writer():
    global csv_file
    if csv_file:
        csv_file.close()
        csv_file = None

# Function to convert CPU usage to mCPU
def parse_cpu(cpu_usage):
    if "n" in cpu_usage:
        return int(cpu_usage.strip("n")) / 1e6  # Convert nanocores to millicores
    if "u" in cpu_usage:
        return int(cpu_usage.strip("u")) / 1e3  # Convert microcores to millicores
    if "m" in cpu_usage:
        return int(cpu_usage.strip("m"))        # Already in millicores
    return int(cpu_usage) * 1000                 # Convert cores to millicores

# Function to convert memory usage to MiB
def parse_memory(mem_usage):
    if "Ki" in mem_usage:
        return int(mem_usage.strip("Ki")) / 1024  # Convert KiB to MiB
    if "Mi" in mem_usage:
        return int(mem_usage.strip("Mi"))         # Already in MiB
    if "Gi" in mem_usage:
        return int(mem_usage.strip("Gi")) * 1024  # Convert GiB to MiB
    return int(mem_usage) / (1024 * 1024)           # Convert bytes to MiB

# Function to collect metrics and save to CSV
def collect_metrics():
    while True:
        try:
            setup_csv_writer()  # Ensure the writer is set up for the current day

            # Fetch metrics from Kubernetes API
            response = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for pod in response.get("items", []):
                pod_name = pod["metadata"]["name"]
                namespace = pod["metadata"]["namespace"]

                # Parse CPU and memory usage
                cpu_usage = pod["containers"][0]["usage"]["cpu"]
                mem_usage = pod["containers"][0]["usage"]["memory"]
                cpu_mcpu = parse_cpu(cpu_usage)
                mem_mib = parse_memory(mem_usage)

                # Write to CSV
                csv_writer.writerow([timestamp, namespace, pod_name, cpu_mcpu, mem_mib])

                if debug:
                    print(f"[DEBUG] {namespace}/{pod_name}: CPU={cpu_mcpu}m, Mem={mem_mib}MiB")

            time.sleep(60)  # Wait before fetching metrics again
        except Exception as e:
            print(f"[ERROR] Failed to fetch metrics: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        collect_metrics()
    finally:
        close_csv_writer()  # Ensure the file is properly closed on exit

