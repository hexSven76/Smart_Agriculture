
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.ethernet.Eth100M;
import inet.node.inet.SensorNode;
import inet.node.inet.StandardHost;
import inet.physicallayer.wireless.common.medium.RadioMedium;
import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;

network AgricultureNetwork
{
    @display("bgb=60,30;bgi=showcases/warehouse,s");
    submodules:
        configurator: Ipv4NetworkConfigurator {
            @display("p=3.4662657,4.033473");
        }
        visualizer: IntegratedCanvasVisualizer {
            @display("p=3.4662657,9.264383");
        }
        radioMedium: RadioMedium {
            @display("p=3.4032426,14.0541315");
        }
        sensor4: SensorNode {
            @display("p=22,6.5;i=misc/sensor2");
        }
        sensor1: SensorNode {
            @display("p=16.482326,20.196255;i=misc/sensor2");
        }
        sensor2: SensorNode {
            @display("p=33.772572,16.275303;i=misc/sensor2");
        }
        sensor3: SensorNode {
            @display("p=35,6.5;i=misc/sensor2");
        }
        gateway: SensorNode {
            @display("p=28.5,13;i=misc/sensorgateway");
        }
        server: StandardHost {
            @display("p=38.35591,12.96182");
        }
    connections:
        gateway.ethg++ <--> Eth100M <--> server.ethg++;
}
