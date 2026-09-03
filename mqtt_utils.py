"""paho-mqtt version compatibility."""
import paho.mqtt.client as mqtt


def make_client(client_id):
    """Build a Client that uses the v1 callback signatures on either paho major.

    paho-mqtt 2.x refuses to construct a Client without an explicit callback API
    version, so an unpinned `pip install paho-mqtt` turns every start into an
    immediate ValueError.
    """
    try:
        from paho.mqtt.enums import CallbackAPIVersion
    except ImportError:  # paho-mqtt 1.x
        return mqtt.Client(client_id=client_id)
    return mqtt.Client(CallbackAPIVersion.VERSION1, client_id=client_id)
