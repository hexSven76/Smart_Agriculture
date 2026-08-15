for sca in *.sca; do
    base="${sca%.sca}"
    vec="${base}.vec"

    if [ -f "$vec" ]; then
        echo "Processing: $base"

        opp_scavetool x \
            -F CSV-R \
            -f '(module =~ "AgricultureNetwork.sensor[*].app[0]" AND name =~ "packetSent*:count") OR (module =~ "AgricultureNetwork.server.app[0]" AND (name =~ "packetReceived*:count" OR name =~ "packetReceived*:sum(packetBytes)" OR name =~ "endToEndDelay*:vector")) OR (module =~ "AgricultureNetwork.sensor[*].wlan[0].radio.energyConsumer" AND name =~ "powerConsumption:vector") OR (module =~ "AgricultureNetwork.gateway.wlan[0].radio.energyConsumer" AND name =~ "powerConsumption:vector")' \
            "$sca" "$vec" \
            -o "${base}_metrics.csv"
    else
        echo "WARNING: No matching .vec file for $sca"
    fi
done