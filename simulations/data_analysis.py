from pathlib import Path
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt

# configuration
RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_CSV = RESULTS_DIR / "all_metrics.csv"
SIMULATION_TIME = 10.0


# ---------- CSV parsing helpers ----------


def parse_vector_string(value):
    """convert a whitespace-separated vector string into floats."""
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
    """return vector rows matching a module regex/patternand metric name."""
    mask = (
        (df["type"] == "vector") &
        (df["module"].astype(str).str.match(module_pattern)) &
        (df["name"] == metric_name)
    )

    return df[mask]


# ---------- Experiment-variable extraction ----------


def parse_value(value, unit=None):
    """convert simulation variables into numeric values."""

    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    if text == "":
        return np.nan

    # Byte and B are both valid
    if unit == "Byte":
        text = re.sub(r"Byte$", "", text, flags=re.IGNORECASE)

    elif unit == "B":
        text = re.sub(r"(Byte|B)$", "", text, flags=re.IGNORECASE)

    elif unit:
        text = re.sub(
            rf"{re.escape(unit)}$",
            "",
            text,
            flags=re.IGNORECASE
        )

    # remove whitespace
    text = text.strip()

    try:
        return float(text)
    except ValueError:
        return np.nan


def extract_experiment_variables(path):
    """extract experiment variables from  *_metrics.csv files."""

    filename = path.name

    # default values from Base configuration
    variables = {
        "txPower_mW": 2.24,
        "numSensors": 10.0,
        "sendInterval_s": 1.0,
        "packetLength_B": 10.0,
    }

    match = re.match(
        r"^(?:BMac|XMac|LMac|Ieee802154)_"
        r"(TxPower|NumSensors|Traffic|PacketLength)-"
        r"(.+?)-#\d+_metrics\.csv$",
        filename
    )

    if not match:
        return variables

    experiment = match.group(1)
    value = match.group(2)

    if experiment == "TxPower":

        variables["txPower_mW"] = parse_value(value, "mW")

    elif experiment == "NumSensors":

        match_value = re.match(r"numSensors=(.+)", value)

        if match_value:
            variables["numSensors"] = parse_value(
                match_value.group(1)
            )

    elif experiment == "Traffic":

        match_value = re.match(r"sendInterval=(.+)", value)

        if match_value:
            variables["sendInterval_s"] = parse_value(
                match_value.group(1), "s"
            )

    elif experiment == "PacketLength":

        match_value = re.match(r"packetLength=(.+)", value)

        if match_value:
            variables["packetLength_B"] = parse_value(
                match_value.group(1), "B"
            )

    return variables


def extract_mac(df, filename):
    """extracting MAC name."""

    rows = df[
        (df["type"] == "runattr") &
        (df["attrname"] == "configname")
    ]

    if not rows.empty:
        config_name = str(rows.iloc[0]["attrvalue"])
        return config_name.split("_")[0]

    for mac in ["BMac", "XMac", "LMac", "Ieee802154"]:
        if mac.lower() in filename.lower():
            return mac

    return "Unknown"


def extract_experiment(filename):
    """extract experiment type from the beginning of the filename."""

    match = re.match(
        r"^(?:BMac|XMac|LMac|Ieee802154)_([^,-]+)",
        filename
    )

    if match:
        return match.group(1)

    return "Unknown"


# ---------- Packet metrics ----------


def calculate_packet_metrics(df):
    """calculate total sent, received, and PDR."""

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


def calculate_packet_loss_ratio(pdr):
    """calculate Packet Loss Ratio from PDR."""
    if pd.isna(pdr):
        return np.nan

    return 1.0 - pdr


# ---------- End-to-end delay ----------


def calculate_end_to_end_delay(df):
    """calculate mean E2E delay from the server.app[0] vector."""

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


# ---------- Throughput ----------


def calculate_throughput(df, sim_time):
    """calculate Throughput = received bytes * 8 / simulation time"""

    rows = df[
        (df["type"] == "scalar") &
        (df["module"] == "AgricultureNetwork.server.app[0]") &
        (df["name"] == "packetReceived:sum(packetBytes)")
    ]

    if rows.empty or pd.isna(sim_time) or sim_time <= 0:
        return np.nan

    received_bytes = pd.to_numeric(
        rows.iloc[0]["value"],
        errors="coerce"
    )

    if pd.isna(received_bytes):
        return np.nan

    return float((received_bytes * 8) / sim_time)


# ---------- Power consumption ----------


def time_weighted_average(time_values, power_values):
    """calculate a time-weighted average for a sample vector."""

    if len(time_values) == 0 or len(power_values) == 0:
        return np.nan

    n = min(len(time_values), len(power_values))

    times = time_values[:n]
    powers = power_values[:n]

    if n == 1:
        return float(powers[0])

    durations = np.diff(times)

    # ignore negative intervals
    valid = durations >= 0

    weighted_sum = np.sum(
        powers[:-1][valid] * durations[valid]
    )

    total_time = np.sum(durations[valid])

    if total_time <= 0:
        return float(np.mean(powers))

    return float(weighted_sum / total_time)


def calculate_sensor_power(df):
    """calculate average sensor power consumption using each sensor's
        wlan[*].radio.energyConsumer.powerConsumption:vector."""

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

    # convert watts to mW
    return float(np.mean(sensor_powers) * 1000)


def calculate_energy_efficiency(throughput_bps, sensor_power_mW):
    """calculate energy efficiency."""
    if pd.isna(throughput_bps) or pd.isna(sensor_power_mW):
        return np.nan

    if sensor_power_mW <= 0:
        return np.nan

    # bps / mW = kbits/J
    return throughput_bps / sensor_power_mW


# ---------- Process one CSV ----------
 

def process_file(path):
    print(f"Processing: {path.name}")

    df = pd.read_csv(path, low_memory=False)
    mac = extract_mac(df, path.name)
    experiment = extract_experiment(path.name)
    variables = extract_experiment_variables(path)
    packets_sent, packets_received, pdr = calculate_packet_metrics(df)
    mean_delay = calculate_end_to_end_delay(df)
    avg_throughput = calculate_throughput(df, SIMULATION_TIME)
    avg_sensor_power = calculate_sensor_power(df)
    plr = calculate_packet_loss_ratio(pdr)
    energy_efficiency = calculate_energy_efficiency(avg_throughput, avg_sensor_power)

    result = {
        "MAC": mac,
        "Experiment": experiment,
        **variables,
        "packetsSent": packets_sent,
        "packetsReceived": packets_received,
        "PDR": pdr,
        "PLR": plr,
        "meanE2EDelay_s": mean_delay,
        "meanE2EDelay_ms": (
            mean_delay * 1000
            if not np.isnan(mean_delay)
            else np.nan
        ),
        "averageThroughput_bps": avg_throughput,
        "averageSensorPower_mW": avg_sensor_power,
        "energyEfficiency_kbits_per_J": energy_efficiency,
    }

    return result


# ---------- Graph generation ----------
 

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


# ---------- Main ----------
 

def main():

    csv_files = sorted(
        path for path in RESULTS_DIR.glob("*_metrics.csv")
        if path.name != "all_metrics.csv"
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

    # Average repetitions of each experiment
    group_columns = [
        "MAC",
        "Experiment",
        "numSensors",
        "txPower_mW",
        "sendInterval_s",
        "packetLength_B",
    ]

    metric_columns = [
        "packetsSent",
        "packetsReceived",
        "PDR",
        "PLR",
        "meanE2EDelay_s",
        "meanE2EDelay_ms",
        "averageThroughput_bps",
        "averageSensorPower_mW",
        "energyEfficiency_kbits_per_J",
    ]

    result_df = (
        result_df
        .groupby(group_columns, dropna=False)[metric_columns]
        .mean()
        .reset_index()
    )

    sort_columns = [
        "Experiment",
        "MAC",
        "numSensors",
        "txPower_mW",
        "sendInterval_s",
        "packetLength_B",
    ]

    # Separate results by experiment type
    tx_power_df = result_df[
        result_df["Experiment"] == "TxPower"
    ]

    num_sensors_df = result_df[
        result_df["Experiment"] == "NumSensors"
    ]

    traffic_df = result_df[
        result_df["Experiment"] == "Traffic"
    ]

    packet_length_df = result_df[
        result_df["Experiment"] == "PacketLength"
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

    # Graphs

    make_graph(
        tx_power_df,
        "txPower_mW",
        "PDR",
        "Transmit Power (mW)",
        "Packet Delivery Ratio",
        "PDR vs Transmit Power",
        "PDR_vs_TxPower.png"
    )

    make_graph(
        tx_power_df,
        "txPower_mW",
        "meanE2EDelay_ms",
        "Transmit Power (mW)",
        "Mean End-to-End Delay (ms)",
        "Mean End-to-End Delay vs Transmit Power",
        "Delay_vs_TxPower.png"
    )

    make_graph(
        tx_power_df,
        "txPower_mW",
        "averageThroughput_bps",
        "Transmit Power (mW)",
        "Average Throughput (bps)",
        "Average Throughput vs Transmit Power",
        "Throughput_vs_TxPower.png"
    )

    make_graph(
        tx_power_df,
        "txPower_mW",
        "averageSensorPower_mW",
        "Transmit Power (mW)",
        "Average Sensor Power Consumption (mW)",
        "Average Sensor Power vs Transmit Power",
        "Power_vs_TxPower.png"
    )

    make_graph(
        num_sensors_df,
        "numSensors",
        "PDR",
        "Number of Sensors",
        "Packet Delivery Ratio",
        "PDR vs Number of Sensors",
        "PDR_vs_NumSensors.png"
    )

    make_graph(
        traffic_df,
        "sendInterval_s",
        "PDR",
        "Send Interval (s)",
        "Packet Delivery Ratio",
        "PDR vs Send Interval",
        "PDR_vs_SendInterval.png"
    )

    make_graph(
        packet_length_df,
        "packetLength_B",
        "PDR",
        "Packet Length (Byte)",
        "Packet Delivery Ratio",
        "PDR vs Packet Length",
        "PDR_vs_PacketLength.png"
    )

    make_graph(
        tx_power_df,
        "txPower_mW",
        "PLR",
        "Transmit Power (mW)",
        "Packet Loss Ratio",
        "Packet Loss Ratio vs Transmit Power",
        "PLR_vs_TxPower.png"
    )

    make_graph(
        num_sensors_df,
        "numSensors",
        "PLR",
        "Number of Sensors",
        "Packet Loss Ratio",
        "Packet Loss Ratio vs Number of Sensors",
        "PLR_vs_NumSensors.png"
    )

    make_graph(
        traffic_df,
        "sendInterval_s",
        "PLR",
        "Send Interval (s)",
        "Packet Loss Ratio",
        "Packet Loss Ratio vs Send Interval",
        "PLR_vs_SendInterval.png"
    )

    make_graph(
        packet_length_df,
        "packetLength_B",
        "PLR",
        "Packet Length (Byte)",
        "Packet Loss Ratio",
        "Packet Loss Ratio vs Packet Length",
        "PLR_vs_PacketLength.png"
    )

    make_graph(
        tx_power_df,
        "txPower_mW",
        "energyEfficiency_kbits_per_J",
        "Transmit Power (mW)",
        "Energy Efficiency (kbits/J)",
        "Energy Efficiency vs Transmit Power",
        "EnergyEfficiency_vs_TxPower.png"
    )

    make_graph(
        num_sensors_df,
        "numSensors",
        "energyEfficiency_kbits_per_J",
        "Number of Sensors",
        "Energy Efficiency (kbits/J)",
        "Energy Efficiency vs Number of Sensors",
        "EnergyEfficiency_vs_NumSensors.png"
    )

    make_graph(
        traffic_df,
        "sendInterval_s",
        "energyEfficiency_kbits_per_J",
        "Send Interval (s)",
        "Energy Efficiency (kbits/J)",
        "Energy Efficiency vs Send Interval",
        "EnergyEfficiency_vs_SendInterval.png"
    )

    make_graph(
        packet_length_df,
        "packetLength_B",
        "energyEfficiency_kbits_per_J",
        "Packet Length (Byte)",
        "Energy Efficiency (kbits/J)",
        "Energy Efficiency vs Packet Length",
        "EnergyEfficiency_vs_PacketLength.png"
    )


    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
