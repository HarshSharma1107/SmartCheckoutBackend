import Paho from "paho-mqtt";

export function createMqttClient({ brokerUrl, deviceId, onCommand, onStatus }) {
  const clientId = `ekart-${deviceId}`;
  const url = new URL(brokerUrl);
  const port = Number(url.port || (url.protocol === "wss:" ? 443 : 80));
  const path = url.pathname && url.pathname !== "/" ? url.pathname : "/mqtt";
  const client = new Paho.Client(url.hostname, port, path, clientId);

  client.onConnectionLost = (response) => {
    onStatus?.({ connected: false, error: response.errorMessage });
  };

  client.onMessageArrived = (message) => {
    try {
      onCommand?.(JSON.parse(message.payloadString), message.destinationName);
    } catch {
      onCommand?.({ raw: message.payloadString }, message.destinationName);
    }
  };

  function connect() {
    client.connect({
      useSSL: brokerUrl.startsWith("wss://") || brokerUrl.startsWith("mqtts://"),
      onSuccess: () => {
        onStatus?.({ connected: true });
        client.subscribe(`ekart/device/${deviceId}/commands`);
        publishStatus("online");
      },
      onFailure: (error) => onStatus?.({ connected: false, error }),
      reconnect: true,
    });
  }

  function publishStatus(status) {
    const message = new Paho.Message(JSON.stringify({ status, at: new Date().toISOString() }));
    message.destinationName = `ekart/device/${deviceId}/status`;
    client.send(message);
  }

  function publishHeartbeat(payload) {
    const message = new Paho.Message(JSON.stringify(payload));
    message.destinationName = `ekart/device/${deviceId}/heartbeat`;
    client.send(message);
  }

  return { connect, publishStatus, publishHeartbeat, client };
}
