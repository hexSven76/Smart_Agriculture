
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.ethernet.Eth100M;
import inet.node.inet.SensorNode;
import inet.node.inet.StandardHost;
import inet.physicallayer.wireless.common.medium.RadioMedium;
import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;

network AgricultureNetwork
{
    parameters:
        int numSensors = default(4);
        
    @display("bgb=600,600");

    submodules:
        configurator: Ipv4NetworkConfigurator {
            @display("p=3,4");
        }
        visualizer: IntegratedCanvasVisualizer {
            @display("p=3,9");
        }
        radioMedium: RadioMedium {
            @display("p=3,14");
        }
        sensor[numSensors]: SensorNode {
            @display("p=10,10;i=misc/sensor2");
        }
        gateway: SensorNode {
            @display("p=28,13;i=misc/sensorgateway");
        }
        server: StandardHost {
            @display("p=38,13");
        }

    connections:
        gateway.ethg++ <--> Eth100M <--> server.ethg++;
}
