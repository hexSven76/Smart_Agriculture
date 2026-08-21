#!/bin/bash

cd "$(dirname "$0")" || exit 1

PROJECT_SRC="../src"
INET_SRC="C:/omnetpp/omnetpp-6.4.0/samples/inet-4.6.0/src"
INET_LIB="C:/omnetpp/omnetpp-6.4.0/samples/inet-4.6.0/src/libINET.dll"

CONFIGS=(
    "Ieee802154_NumSensors"
    "BMac_NumSensors"
    "XMac_NumSensors"
    "LMac_NumSensors"
    "Ieee802154_TxPower"
    "BMac_TxPower"
    "XMac_TxPower"
    "LMac_TxPower"
    "Ieee802154_Traffic"
    "BMac_Traffic"
    "XMac_Traffic"
    "LMac_Traffic"
    "Ieee802154_PacketLength"
    "BMac_PacketLength"
    "XMac_PacketLength"
    "LMac_PacketLength"
)

TOTAL=${#CONFIGS[@]}
CURRENT=0

echo
echo "============================================================"
echo " Smart Agriculture - Batch Simulation"
echo "============================================================"
echo "Configurations: $TOTAL"
echo

for CONFIG in "${CONFIGS[@]}"; do
    CURRENT=$((CURRENT + 1))

    echo
    echo "============================================================"
    echo " [$CURRENT/$TOTAL] Running: $CONFIG"
    echo "============================================================"
    echo

    opp_run \
        -u Cmdenv \
        -n "$PROJECT_SRC" \
        -n "$INET_SRC" \
        -l "$INET_LIB" \
        -c "$CONFIG"

    STATUS=$?

    if [ $STATUS -ne 0 ]; then
        echo
        echo "ERROR: Configuration '$CONFIG' failed."
        echo "Exit code: $STATUS"
        exit $STATUS
    fi

    echo
    echo "[$CURRENT/$TOTAL] $CONFIG completed successfully."
done

echo
echo "============================================================"
echo " ALL CONFIGURATIONS COMPLETED SUCCESSFULLY"
echo "============================================================"
