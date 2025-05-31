# SentientZone

**SentientZone** is an offline, cryptographically verifiable HVAC controller designed to optimize energy usage without relying on cloud services. It operates on a Raspberry Pi, making autonomous decisions based on environmental sensor data, and logs every action with cryptographic signatures to ensure tamper-proof records.

## Features

* **Offline Operation**: Functions entirely without internet connectivity, ensuring privacy and reliability.
* **Cryptographic Logging**: Utilizes Ed25519 signatures to authenticate each decision, creating an immutable audit trail.
* **Sensor Integration**: Monitors temperature, humidity, and motion to make informed HVAC control decisions.
* **Energy Optimization**: Reduces HVAC runtime by analyzing environmental data, leading to potential energy savings.
* **User Overrides**: Allows manual control through a local web interface, with all overrides logged and signed.
* **Modular Design**: Comprises distinct modules for sensors, decision-making, actuation, logging, and reporting.

## System Architecture

```
[ Sensors ] → [ Decision Engine ] → [ Actuator Controller ]
      ↓                 ↓                   ↓
[ Logger ] ← [ Override Manager ] ← [ User Interface ]
      ↓
[ Cryptographic Signer ] → [ Report Generator ]
```

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/sz3lp/SentientZone.git
   cd SentientZone
   ```

2. **Install Dependencies**:
   Ensure you have Python 3 installed. Then, install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the System**:
   Edit the `config.ini` file to match your hardware setup and preferences.

4. **Run the Installer**:

   ```bash
   python installer.py
   ```

5. **Start the Main Application**:

   ```bash
   python main.py
   ```

## Usage

* **Monitoring**: Access the local web interface at `http://<raspberry_pi_ip>:5000` to view system status and logs.
* **Manual Overrides**: Use the web interface to manually control HVAC states. All overrides are logged with signatures.
* **Reports**: Daily reports are generated and saved in the `reports/` directory, detailing system performance and energy usage.

## Hardware Requirements

* Raspberry Pi (Model 3 or later recommended)
* DHT22 Temperature and Humidity Sensor
* PIR Motion Sensor
* Relay Module compatible with Raspberry Pi GPIO
* HVAC system with accessible control interface

## Security and Privacy

SentientZone emphasizes user privacy and data integrity:

* **No Cloud Dependency**: All operations and data storage occur locally.
* **Tamper-Proof Logs**: Each decision and override is signed using Ed25519, ensuring authenticity.
* **User Control**: Manual overrides are respected and logged, providing transparency and control.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
