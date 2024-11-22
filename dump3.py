
import time
import csv
from kubernetes import client, config

# Configuration for debugging
debug = True

# Initialize Kubernetes API
config.load_kube_config()
api = client.CustomObjectsApi()

# Output file
output_file = "pod_metrics.csv"

# Ensure the file has headers
with open(output_file, "w") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "namespace", "pod_name", "cpu_mcpu", "memory_mib"])

# Function to convert CPU usage to mCPU
def parse_cpu(cpu_usage):
    if "n" in cpu_usage:
        return int(cpu_usage.strip("n")) / 1e6  # Convert nanocores to millicores
    elif "u" in cpu_usage:
        return int(cpu_usage.strip("u")) / 1e3  # Convert microcores to millicores
    elif "m" in cpu_usage:
        return int(cpu_usage.strip("m"))  # Already in millicores
    else:
        return int(cpu_usage) * 1000  # Convert cores to millicores

# Function to convert memory usage to MiB
def parse_memory(mem_usage):
    if "Ki" in mem_usage:
        return int(mem_usage.strip("Ki")) / 1024  # Convert KiB to MiB
    elif "Mi" in mem_usage:
        return int(mem_usage.strip("Mi"))  # Already in MiB
    elif "Gi" in mem_usage:
        return int(mem_usage.strip("Gi")) * 1024  # Convert GiB to MiB
    else:
        return int(mem_usage) / (1024 * 1024)  # Convert bytes to MiB

# Collect metrics and save to CSV
def collect_metrics():
    while True:
        try:
            response = api.list_cluster_custom_object(
                "metrics.k8s.io", "v1beta1", "pods"
            )
            with open(output_file, "a") as f:
                writer = csv.writer(f)
                for pod in response["items"]:
                    pod_name = pod["metadata"]["name"]
                    namespace = pod["metadata"]["namespace"]

                    # Parse CPU and memory usage
                    cpu_usage = pod["containers"][0]["usage"]["cpu"]
                    mem_usage = pod["containers"][0]["usage"]["memory"]

                    # Convert CPU to mCPU and memory to MiB
                    cpu_mcpu = parse_cpu(cpu_usage)
                    mem_mib = parse_memory(mem_usage)

                    # Write to CSV
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([timestamp, namespace, pod_name, cpu_mcpu, mem_mib])

                    if debug:
                        print(f"[DEBUG] {namespace}/{pod_name}: CPU={cpu_mcpu}m, Mem={mem_mib}MiB")

            time.sleep(60)
        except Exception as e:
            print(f"[ERROR] Failed to fetch metrics: {e}")
            time.sleep(10)

if __name__ == "__main__":
    collect_metrics()

