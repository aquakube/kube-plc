# KUBE-PLC #

apps/plc - This microservice consumes a single PLC Custom Resource (CR) as an environment variable.  On start-up, the microservice will schedule polling jobs according to the configured intervals on each readings property.  The application is instrumented with OpenTelemetry to emit metrics once it has successfully sampled a value the PLC.  The OpenTelemetry SDK and OTLP exporters can be configured through environment variables that are mounted to the pod on deployment.  The readings will be represented as an observable gauge that is configured to be periodically exported to an OpenTelemetry Collector.  The application also defines a REST API where clients can request Read or Write requests to the PLC.  There is an audit log of all Write requests the PLC receives, as each response is captured in a CloudEvent and put into a Kafka Topic.

apps/operator - With the one-to-one relationship defined on the resource to a singel physical PLC device, the operator can easily spin up and down the corresponding deployment for the PLC when a resource is created, updated, or deleted.  The operator will update the status of the PLC Custom Resource with an available property which will indicate if the physical PLC device is online and reachable.  This is accomplished through a readiness and liveness probes on the PLC service.

### Remote Development ###

Use skaffold run to automatically build and deploy your application.
```
skaffold run
```

Use skaffold dev to automatically build and deploy your application when your code changes.
```
skaffold dev
```

#### Deploy PLC Resources ####

The PLC CRs are hosted in your own repository which defines your Kuberenetes IaC.
```
cd kube-resources/skaffold
skaffold run -f plcs.yaml
skaffold delete -f plcs.yaml
```

### Local Development ###

Run the python application locally:
```
DEBUG=False \
ENVIRONMENT=dev \
NAME=hvdp \
KUBERNETES_NAMESPACE_NAME=fieldRef(v1:metadata.namespace) \
KUBERNETES_POD_NAME=fieldRef(v1:metadata.name) \
KUBERNETES_POD_UID=fieldRef(v1:metadata.uid) \
OTEL_METRICS_EXPORTER=console \
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=collector.opentelemetry.svc.cluster.local:4317 \
OTEL_EXPORTER_OTLP_METRICS_INSECURE=true \
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=grpc \
OTEL_EXPORTER_OTLP_METRICS_TIMEOUT=2500 \
PLC_TIMEOUT=1 \
SPEC="{'base': 'modbus+tcp://10.0.9.40:502/1/', 'properties': {'fuelPumpFault': {'forms': [{'href': '17405', 'modbus:entity': 'Coil', 'modbus:pollingTime': 5, 'op': ['observeproperty', 'readproperty']}], 'readOnly': True, 'title': 'Fuel Pump Fault', 'type': 'boolean'}, 'generator01TotalRunTimeHoursLw': {'forms': [{'href': '401083', 'modbus:entity': 'HoldingRegister', 'modbus:pollingTime': 15, 'op': ['observeproperty', 'readproperty'], 'scale': 0.1}], 'readOnly': True, 'title': 'Port Generator Total Run Time Hours LW', 'type': 'number', 'unit': 'hrs'}, 'generator01TotalRunTimeLoadedHoursLw': {'forms': [{'href': '401085', 'modbus:entity': 'HoldingRegister', 'modbus:pollingTime': 5, 'op': ['observeproperty', 'readproperty'], 'scale': 0.1}], 'readOnly': True, 'title': 'Port Generator Total Run Time Loaded Hours LW', 'type': 'number', 'unit': 'hrs'}, 'generator02TotalRunTimeHoursLw': {'forms': [{'href': '402083', 'modbus:entity': 'HoldingRegister', 'modbus:pollingTime': 15, 'op': ['observeproperty', 'readproperty'], 'scale': 0.1}], 'readOnly': True, 'title': 'Starboard Generator Total Run Time Hours LW', 'type': 'number', 'unit': 'hrs'}, 'generator02TotalRunTimeLoadedHoursLw': {'forms': [{'href': '402085', 'modbus:entity': 'HoldingRegister', 'modbus:pollingTime': 15, 'op': ['observeproperty', 'readproperty', 'writeproperty'], 'scale': 0.1}], 'readOnly': True, 'title': 'Starboard Generator Total Run Time Loaded Hours LW', 'type': 'number', 'unit': 'hrs'}}, 'title': 'High Voltage Distribution Panel', 'version': '0.0.1'}" \
python3 apps/plc/src/main.py 
```

### API Usage ###

The PLC service supports endpoints for livenss and readiness probes.
Readiness indicates if the plc the service manages is online and reachable.
The other endpoints are for remote control and monitoring of panels.

##### Local #####

Read property `generator02TotalRunTimeHoursLw`:
```
curl -X GET localhost:5000/api/plc/generator02TotalRunTimeHoursLw
```

Write value to property `generator02TotalRunTimeLoadedHoursLw`:
```
curl -X PUT localhost:5000/api/plc/generator02TotalRunTimeLoadedHoursLw \
  -H "Content-Type: application/json" \
  -d '{"value": 1113}'
```

Read Port Generator Events:
```
curl -X POST localhost:5000/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "403001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```

Read Starboard Generator Events:
```
curl -X POST localhost:5000/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "404001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```

Read and write to random HR:
```
curl -X POST localhost:5000/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "400406", "op": ["readproperty", "writeproperty"], "modbus:entity": "HoldingRegister", "value": 123} }'
```

##### External K8S #####

Read property `generator02TotalRunTimeHoursLw`:
```
curl -X GET http://10.0.9.21:30877/api/plc/generator02TotalRunTimeHoursLw
```


Read Port Generator Events:
```
curl -X POST http://10.0.9.21:30300/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "modbus+tcp://10.0.9.40:502/1/403001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```

Read Starboard Generator Events:
```
curl -X POST http://10.0.9.21:30300/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "404001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```

##### Internal K8S #####

Read Port Generator Events:
```
curl -X POST http://hvdp.plc.svc.cluster.local:5000/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "modbus+tcp://10.0.9.40:502/1/403001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```

Read Starboard Generator Events:
```
curl -X POST http://hvdp.plc.svc.cluster.local:5000/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "404001?quantity=120", "op": "readproperty", "modbus:entity": "HoldingRegister"} }'
```


Watch server sent events:
```
curl -N --http2 -H "Accept:text/event-stream" http://mccp.plc.svc.cluster.local:5000/api/events
```


```
curl -X POST http://10.0.9.21:31948/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "17440", "op": "readproperty", "modbus:entity": "Coil"} }'

  curl -X POST http://10.0.9.21:31948/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "17440", "op": "writeproperty", "modbus:entity": "Coil",  "value": 0} }'

curl -X POST http://10.0.9.21:31948/api/plc \
  -H "Content-Type: application/json" \
  -d '{ "form" : { "href": "1175357445", "op": ["readproperty", "writeproperty"], "modbus:entity": "Coil", "value": 1} }'
```