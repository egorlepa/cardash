import obd
import paho.mqtt.client as mqtt
import asyncio
import os
from obd import OBDCommand
from obd.protocols import ECU
from obd.decoders import *

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "sensors/"

SENSORS = {
    "rpm": obd.commands["RPM"],
    "speed": obd.commands["SPEED"],
    "throttle_position": obd.commands["THROTTLE_POS"],
    "coolant_temp": obd.commands["COOLANT_TEMP"],
    "oil_temp": obd.commands["OIL_TEMP"],
    "fuel_pressure": obd.commands["FUEL_PRESSURE"],
    "fuel_rate": obd.commands["FUEL_RATE"],
    "intake_pressure": obd.commands["INTAKE_PRESSURE"],
    "intake_temp": obd.commands["INTAKE_TEMP"],
    "boost_pressure": obd.commands["MONITOR_BOOST_PRESSURE_B1"],
    "runtime": OBDCommand("RUN_TIME", "Engine Run Time", b"011F", 4, uas(0x12),ECU.ENGINE, True),
}

def connect_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    return client

def validate_supported_commands(connection):
    supported_sensors = {}
    for topic, command in SENSORS.items():
        if connection.supports(command):
            supported_sensors[topic] = command
        else:
            print(f"Command {command} not supported, skipping {topic}")
    return supported_sensors

async def handle_response(topic, response, client):
    if response.value is not None:
        client.publish(MQTT_TOPIC_PREFIX + topic, str(response.value))

async def main():
    connection = obd.Async(delay_cmds=0)
    if not connection.is_connected():
        print("Failed to connect to OBD-II adapter.")
        return
    
    client = connect_mqtt()
    
    valid_sensors = validate_supported_commands(connection)
    
    for topic, command in valid_sensors.items():
        connection.watch(command, callback=lambda r, t=topic: asyncio.create_task(handle_response(t, r, client)))
    
    connection.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        connection.stop()
        client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
