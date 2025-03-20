import paho.mqtt.client as mqtt

# MQTT Broker details
BROKER_IP = "127.0.0.1"  # If Mosquitto is running on the Pi itself
BROKER_PORT = 1883
TOPIC = "response/decision"

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)  # Subscribe to the topic
    else:
        print(f"Failed to connect, return code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")

# Create an MQTT client instance
client = mqtt.Client()

# Attach callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
print("Connecting to MQTT broker...")
client.connect(BROKER_IP, BROKER_PORT, 60)

# Start listening for messages
client.loop_forever()
