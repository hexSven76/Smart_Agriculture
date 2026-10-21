# Performance Evaluation of MAC Protocols in a Wireless Sensor Network

A simulation-based study comparing four medium access control (MAC) protocols in a wireless sensor network (WSN) scenario using **OMNeT++** and **INET**.

The project evaluates IEEE 802.15.4, B-MAC, X-MAC, and L-MAC under varying network sizes, transmission powers, traffic intervals, and packet lengths. The objective is to investigate how protocol selection and network conditions affect packet delivery, communication delay, throughput, and energy-related metrics.

## Overview

Wireless sensor networks are widely used in smart agriculture to monitor environmental conditions and support data-driven decisions. Since sensor nodes often operate under energy and communication constraints, the choice of MAC protocol can influence overall network performance.

This project compares four MAC configurations in a common wireless sensor network scenario using OMNeT++ and INET.

The study follows a **one-factor-at-a-time (OFAT)** experimental design. Each experiment varies one parameter while keeping the other configured parameters at their baseline values.

The main research objectives are to:

- Compare packet delivery performance across the four MAC configurations.
- Investigate the effect of network size on packet loss and energy efficiency.
- Evaluate the impact of traffic intensity on delay, throughput, and energy consumption.
- Examine how packet length affects communication reliability and channel utilization.
- Investigate the effect of transmission power under the selected simulation conditions.

## Protocols Under Study

| Protocol | General access mechanism | Key characteristic |
|---|---|---|
| IEEE 802.15.4 | CSMA/CA-based medium access | Standardized low-rate wireless personal area networking |
| B-MAC | Carrier-sense MAC with low-power listening | Periodic channel sampling and long preambles |
| X-MAC | Asynchronous low-power listening | Short preambles with receiver-address information and early acknowledgment |
| L-MAC | TDMA-based medium access | Scheduled transmission slots |

These protocols represent different approaches to coordinating access to a shared wireless medium. Their behavior is evaluated under the same application scenario, with comparable baseline radio parameters where applicable.

## Simulation Scenario

The simulated network represents a simplified smart-agriculture monitoring system.

- **Sensor nodes:** Generate periodic UDP traffic.
- **Gateway:** Receives sensor traffic and forwards packets to the server.
- **Server:** Receives application data through a UDP sink.
- **Wireless communication:** Connects sensor nodes to the gateway.
- **Wired communication:** Connects the gateway to the server using a 100 Mbps Ethernet link.

Sensor nodes are stationary and placed at randomized coordinates within a 500 m × 500 m deployment area. The gateway is positioned at `(300 m, 300 m)`, and the server is positioned nearby at `(330 m, 300 m)`.

### Network topology

<img width="835" height="828" alt="image" src="https://github.com/user-attachments/assets/220b9a5d-581d-44ad-8f8d-ca6a15423f98" />

## Experimental Configuration

The experiments vary four independent parameters.

| Parameter | Values |
|---|---|
| Number of sensors | 10, 20, 50, 100 |
| Transmission power | 1, 2.24, 5, 10 mW |
| Send interval | 0.5, 1, 2, 5 seconds |
| Application packet length | 32, 64, 128, 256 bytes |

### Common simulation parameters

| Parameter | Value |
|---|---|
| Simulation duration | 100 seconds |
| Radio center frequency | 2.45 GHz |
| Configured radio bandwidth | 2.8 MHz |
| Configured transmitter bitrate | 19,200 bps |
| Receiver energy detection threshold | −90 dBm |
| Receiver sensitivity | −100 dBm |
| Receiver SNIR threshold | −8 dB |
| Background noise power | −110 dBm |
| Sensor mobility | Stationary |
| Application protocol | UDP |

The radio and MAC configurations use the corresponding INET modules and parameters available for each protocol. Consequently, this is a comparison of complete protocol configurations within a common scenario, rather than a perfectly isolated comparison of the MAC layer alone.

### Experimental design

Each experiment changes one parameter while the remaining experimental parameters are held at their baseline values.

The design includes:

- 4 MAC configurations
- 4 parameter groups
- 4 values per parameter group
- 64 unique MAC/configuration combinations
- 5 repetitions per combination

This results in **320 simulation runs**.

Results are aggregated across the five repetitions of each configuration. Randomized sensor placement and other stochastic behavior should be interpreted in the context of the configured random seeds and reproducibility settings.

## Evaluation Metrics

The simulation results are used to compare the following metrics.

| Metric | Description |
|---|---|
| Packet Delivery Ratio (PDR) | Fraction of transmitted application packets successfully received |
| Packet Loss Ratio (PLR) | Fraction of transmitted application packets not successfully received |
| End-to-End Delay | Time between application packet transmission and reception |
| Throughput | Rate of successfully delivered application data |
| Average Sensor Power | Average power consumption reported for the sensor nodes |
| Energy Efficiency | Successfully delivered data relative to the measured energy consumption or power-based metric used in the analysis |

Throughput and energy-efficiency results depend on the precise measurement definitions and observation intervals used by the result-processing scripts. Consult the analysis code when reproducing these metrics.

## Requirements

The project was developed and tested with:

- **OMNeT++:** 6.4.0
- **INET Framework:** 4.6.0
- **Operating system:** Windows
- **Simulation language:** NED and OMNeT++ configuration files
- **Result format:** CSV, exported from simulation result data

Other versions may require configuration changes or compatibility testing.

## Getting Started

### 1. Install OMNeT++

Download and install OMNeT++ from the official website:

https://omnetpp.org/

### 2. Install INET

Obtain INET from its official repository:

https://github.com/inet-framework/inet

Import the framework into your OMNeT++ workspace and build it according to the INET documentation.

Make sure the installed INET version is compatible with your OMNeT++ version.

### 3. Obtain this project

Clone the repository:

```bash
git clone https://github.com/hexSven76/Smart_Agriculture
cd Smart_Agriculture
```

### 4. Import and build the project

Import the project into the OMNeT++ IDE, configure the INET project reference, and build the project.

## Running Simulations

The project uses `omnetpp.ini` to define the common parameters and protocol-specific configurations.

The main configuration sections are:

- `Base`
- `Ieee802154`
- `BMac`
- `XMac`
- `LMac`

The protocol configurations inherit common settings from `Base` and define their corresponding interfaces, radio modules, MAC implementations, and queue parameters.

### Running a configuration

Use the OMNeT++ IDE to select the desired configuration and start the simulation.

Alternatively, from an appropriately configured OMNeT++ environment, a configuration can be executed using:

```bash
opp_run -u Cmdenv -n .:<INET_NED_PATH> -f omnetpp.ini -c BMac
```

Replace `<INET_NED_PATH>` with the actual INET NED path in your environment. Depending on the workspace setup, the executable may need to be launched from the OMNeT++ environment, and additional library or project paths may be required.

The command above illustrates a single configuration run. It does not automatically execute all 64 experimental configurations or their five repetitions. Use the actual experiment automation scripts or IDE configuration if available.
