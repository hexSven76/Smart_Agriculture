from pathlib import Path
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt


# ============================================================
# Configuration
# ============================================================

RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_CSV = RESULTS_DIR / "all_metrics.csv"


# ============================================================
# CSV parsing helpers
# ============================================================

def parse_vector_string(value):
    """Convert a whitespace-separated vector string into floats."""
    if pd.isna(value) or str(value).strip() == "":
        return np.array([], dtype=float)

    try:
        return np.array(
            [float(x) for x in str(value).split()],
            dtype=float
        )
    except ValueError:
        return np.array([], dtype=float)


def get_vector_rows(df, module_pattern, metric_name):
    """
    Return vector rows matching a module regex/glob-like pattern
    and metric name.
    """
    mask = (
        (df["type"] == "vector") &
        (df["module"].astype(str).str.match(module_pattern)) &
        (df["name"] == metric_name)
    )

    return df[mask]


# ============================================================
# Experiment-variable extraction
# ============================================================

def extract_experiment_variables(df):
    """Extract experiment variables from the runattr iterationvars row."""

    rows = df[
        (df["type"] == "runattr") &
        (df["attrname"] == "iterationvars")
    ]

    if rows.empty:
        return {
            "numSensors": np.nan,
            "txPower_mW": np.nan,
            "sendInterval_s": np.nan,
            "packetLength_Byte": np.nan,
            "simTime_s": np.nan,
        }

    text = str(rows.iloc[0]["attrvalue"])

    def extract(pattern):
        match = re.search(pattern, text)
        return float(match.group(1)) if match else np.nan

    return {
        "numSensors": extract(r"numSensors\s*=\s*([\d.]+)"),
        "txPower_mW": extract(r"txPower\s*=\s*([\d.]+)mW"),
        "sendInterval_s": extract(r"sendInterval\s*=\s*([\d.]+)s"),
        "packetLength_Byte": extract(r"packetLength\s*=\s*([\d.]+)Byte"),
        "simTime_s": extract(r"simTime\s*=\s*([\d.]+)s"),
    }


def extract_mac(df, filename):
    """Get MAC/config name."""

    rows = df[
        (df["type"] == "runattr") &
        (df["attrname"] == "configname")
    ]

    if not rows.empty:
        return str(rows.iloc[0]["attrvalue"])

    # Fallback
    for mac in ["BMac", "XMac", "LMac", "Ieee802154"]:
        if mac.lower() in filename.lower():
            return mac

    return "Unknown"


# ============================================================
# Packet metrics
# ============================================================

def calculate_packet_metrics(df):
    """Calculate total sent, received, and PDR."""

    sent_mask = (
        (df["type"] == "scalar") &
        (df["name"] == "packetSent:count") &
        (df["module"].astype(str).str.contains(r"\.sensor\[\d+\]\.app\[0\]"))
    )

    received_mask = (
        (df["type"] == "scalar") &
        (df["name"] == "packetReceived:count") &
        (df["module"].astype(str) == "AgricultureNetwork.server.app[0]")
    )

    sent_values = pd.to_numeric(
        df.loc[sent_mask, "value"],
        errors="coerce"
    ).dropna()

    received_values = pd.to_numeric(
        df.loc[received_mask, "value"],
        errors="coerce"
    ).dropna()

    packets_sent = sent_values.sum()
    packets_received = received_values.sum()

    if packets_sent > 0:
        pdr = packets_received / packets_sent
    else:
        pdr = np.nan

    return packets_sent, packets_received, pdr


# ============================================================
# End-to-end delay
# ============================================================

def calculate_end_to_end_delay(df):
    """
    Calculate mean E2E delay from the server.app[0] vector.

    IMPORTANT:
    vectime = time at which measurement occurred
    vecvalue = actual delay value
    """

    rows = get_vector_rows(
        df,
        r"^AgricultureNetwork\.server\.app\[0\]$",
        "endToEndDelay:vector"
    )

    if rows.empty:
        return np.nan

    delays = []

    for _, row in rows.iterrows():
        values = parse_vector_string(row["vecvalue"])
        if len(values):
            delays.extend(values)

    if not delays:
        return np.nan

    return float(np.mean(delays))


# ============================================================
# Throughput
# ============================================================

def calculate_throughput(df):
    """
    Calculate average server throughput.

    Throughput vector:
        vectime  = sampling times
        vecvalue = throughput in bps
    """

    rows = get_vector_rows(
        df,
        r"^AgricultureNetwork\.server\.app\[0\]$",
        "throughput:vector"
    )

    if rows.empty:
        return np.nan

    throughput_values = []

    for _, row in rows.iterrows():
        values = parse_vector_string(row["vecvalue"])

        if len(values):
            throughput_values.extend(values)

    if not throughput_values:
        return np.nan

    return float(np.mean(throughput_values))


# ============================================================
# Power consumption
# ============================================================

def time_weighted_average(time_values, power_values):
    """
    Calculate a time-weighted average for a sample-hold vector.

    For each sample:
        power[i] applies until time[i+1].

    The final sample is held until the end of the simulation.
    """

    if len(time_values) == 0 or len(power_values) == 0:
        return np.nan

    n = min(len(time_values), len(power_values))

    times = time_values[:n]
    powers = power_values[:n]

    if n == 1:
        return float(powers[0])

    durations = np.diff(times)

    # Ignore invalid/negative intervals
    valid = durations >= 0

    weighted_sum = np.sum(
        powers[:-1][valid] * durations[valid]
    )

    total_time = np.sum(durations[valid])

    if total_time <= 0:
        return float(np.mean(powers))

    return float(weighted_sum / total_time)


def calculate_sensor_power(df):
    """
    Calculate average sensor power consumption.

    Uses each sensor's:
        wlan[*].radio.energyConsumer.powerConsumption:vector

    Then averages across all sensors.
    """

    mask = (
        (df["type"] == "vector") &
        (df["name"] == "powerConsumption:vector") &
        df["module"].astype(str).str.match(
            r"^AgricultureNetwork\.sensor\[\d+\]\.wlan\[0\]\.radio\.energyConsumer$"
        )
    )

    rows = df[mask]

    if rows.empty:
        return np.nan

    sensor_powers = []

    for _, row in rows.iterrows():

        times = parse_vector_string(row["vectime"])
        powers = parse_vector_string(row["vecvalue"])

        avg_power = time_weighted_average(times, powers)

        if not np.isnan(avg_power):
            sensor_powers.append(avg_power)

    if not sensor_powers:
        return np.nan

    # CSV stores watts -> convert to mW
    return float(np.mean(sensor_powers) * 1000)


# ============================================================
# Process one CSV
# ============================================================

def process_file(path):
    print(f"Processing: {path.name}")

    df = pd.read_csv(path, low_memory=False)

    mac = extract_mac(df, path.name)

    variables = extract_experiment_variables(df)

    packets_sent, packets_received, pdr = calculate_packet_metrics(df)

    mean_delay = calculate_end_to_end_delay(df)

    avg_throughput = calculate_throughput(df)

    avg_sensor_power = calculate_sensor_power(df)

    result = {
        "MAC": mac,

        **variables,

        "packetsSent": packets_sent,
        "packetsReceived": packets_received,
        "PDR": pdr,

        "meanE2EDelay_s": mean_delay,
        "meanE2EDelay_ms": (
            mean_delay * 1000
            if not np.isnan(mean_delay)
            else np.nan
        ),

        "averageThroughput_bps": avg_throughput,

        "averageSensorPower_mW": avg_sensor_power,
    }

    return result


# ============================================================
# Graph generation
# ============================================================

def make_graph(df, x, y, xlabel, ylabel, title, filename):

    if x not in df.columns or y not in df.columns:
        return

    plot_df = df.dropna(subset=[x, y])

    if plot_df.empty:
        print(f"Skipping graph: {title} (no data)")
        return

    plt.figure(figsize=(9, 6))

    for mac in sorted(plot_df["MAC"].unique()):

        mac_df = plot_df[plot_df["MAC"] == mac]

        grouped = (
            mac_df
            .groupby(x)[y]
            .mean()
            .sort_index()
        )

        plt.plot(
            grouped.index,
            grouped.values,
            marker="o",
            label=mac
        )

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output = RESULTS_DIR / filename

    plt.savefig(output, dpi=200)
    plt.close()

    print(f"Created graph: {output.name}")


# ============================================================
# Main
# ============================================================

def main():

    csv_files = sorted(
        RESULTS_DIR.glob("*_metrics.csv")
    )

    if not csv_files:
        print("No metric CSV files found.")
        return

    print(f"Found {len(csv_files)} metric CSV file(s).\n")

    results = []

    for path in csv_files:

        try:
            result = process_file(path)
            results.append(result)

        except Exception as e:
            print(f"ERROR processing {path.name}: {e}")

    if not results:
        print("No results were successfully processed.")
        return

    result_df = pd.DataFrame(results)

    # Sort for easier inspection
    sort_columns = [
        "MAC",
        "numSensors",
        "txPower_mW",
        "sendInterval_s",
        "packetLength_Byte",
    ]

    result_df = result_df.sort_values(
        [c for c in sort_columns if c in result_df.columns]
    )

    result_df.to_csv(
        OUTPUT_CSV,
        index=False
    )

    print("\n============================================================")
    print("RESULTS")
    print("============================================================\n")

    print(
        result_df.to_string(
            index=False
        )
    )

    print(f"\nSaved: {OUTPUT_CSV}")

    # ========================================================
    # Graphs
    # ========================================================

    make_graph(
        result_df,
        "txPower_mW",
        "PDR",
        "Transmit Power (mW)",
        "Packet Delivery Ratio",
        "PDR vs Transmit Power",
        "PDR_vs_TxPower.png"
    )

    make_graph(
        result_df,
        "txPower_mW",
        "meanE2EDelay_ms",
        "Transmit Power (mW)",
        "Mean End-to-End Delay (ms)",
        "Mean End-to-End Delay vs Transmit Power",
        "Delay_vs_TxPower.png"
    )

    make_graph(
        result_df,
        "txPower_mW",
        "averageThroughput_bps",
        "Transmit Power (mW)",
        "Average Throughput (bps)",
        "Average Throughput vs Transmit Power",
        "Throughput_vs_TxPower.png"
    )

    make_graph(
        result_df,
        "txPower_mW",
        "averageSensorPower_mW",
        "Transmit Power (mW)",
        "Average Sensor Power Consumption (mW)",
        "Average Sensor Power vs Transmit Power",
        "Power_vs_TxPower.png"
    )

    make_graph(
        result_df,
        "numSensors",
        "PDR",
        "Number of Sensors",
        "Packet Delivery Ratio",
        "PDR vs Number of Sensors",
        "PDR_vs_NumSensors.png"
    )

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()