# Four-Month Build Plan

This plan assumes a team of 6 with both hardware and software ownership.

## Team Roles

- Hardware Lead: BOM, wiring, power, enclosure, and lab bring-up
- Hardware Engineer: sensor mounting, soldering, calibration jigs, and test fixtures
- Firmware Engineer: ESP-IDF structure, task orchestration, sensor reads
- Comms/Integration Engineer: LoRa protocol, packet routing, node-to-node tests
- ML/Data Engineer: dataset collection, feature engineering, training, export
- QA/Documentation Lead: test plans, logs, acceptance criteria, and release notes

## Month 1: Lock The Architecture

### Goals

- Freeze node architecture, pin map, and power budget.
- Get one board powered and visible on serial.
- Confirm the firmware tree builds as a bring-up skeleton.

### Deliverables

- Final BOM and wiring diagram
- Pin assignment sheet
- Power budget estimate with duty cycle assumptions
- Hardware bring-up checklist
- Repo map that matches the actual tree

### Ownership

- Hardware Lead and Hardware Engineer: wiring, enclosure, power path
- Firmware Engineer: project skeleton and device initialization flow
- QA/Documentation Lead: bring-up checklist and issue tracker

## Month 2: Sensors And Data

### Goals

- Bring up the core sensor stack.
- Calibrate sensors and define sampling rates.
- Start collecting real data in a consistent format.

### Deliverables

- Stable readings from the core meteorological sensors
- Calibration notes for each sensor family
- CSV or JSON dataset schema
- First real dataset from repeated indoor and outdoor tests

### Ownership

- Hardware Engineer: sensor wiring and physical mounting
- Firmware Engineer: driver integration and sensor abstraction
- ML/Data Engineer: dataset schema and feature pipeline
- QA/Documentation Lead: calibration log format and test cases

## Month 3: ML And Mesh Integration

### Goals

- Replace demo-only model flow with real data training.
- Validate model export and embedded inference.
- Make two nodes talk reliably over LoRa.

### Deliverables

- Trained model with saved metrics
- Verified model export artifact
- End-to-end inference on one node
- Two-node LoRa heartbeat and alert exchange

### Ownership

- ML/Data Engineer: training, evaluation, threshold tuning
- Firmware Engineer: inference integration
- Comms/Integration Engineer: packet format, forwarding, retries
- Hardware Lead: radio and power stability during repeated tests

## Month 4: Validation And Handoff

### Goals

- Run the system as a real prototype, not just a lab demo.
- Validate autonomy, alerting, and recoverability.
- Produce a handoff package the team can present and extend.

### Deliverables

- Multi-hour or multi-day stability test
- Power consumption report
- Field trial log
- Final architecture diagram and system summary
- Demo script and acceptance checklist

### Ownership

- QA/Documentation Lead: validation report and final documentation
- Hardware Lead: enclosure and power verification
- Firmware Engineer: bug fixes and stability improvements
- Comms/Integration Engineer: mesh reliability
- ML/Data Engineer: final model tuning and metrics

## Exit Criteria

The build is ready to hand off when:

- A node boots reliably and reports sensor data.
- A second node can receive and forward alerts.
- The model runs on embedded hardware with documented metrics.
- Power behavior is measured and repeatable.
- The team has a clean build, test, and field log.
