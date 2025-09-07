# Network Traffic Detection

This project implements a network traffic detection system using a ConvLSTM model. The system captures network traffic, preprocesses the data, and uses the trained model to predict whether the traffic is benign or malicious.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Modules](#modules)
- [License](#license)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/network-traffic-detection.git
   cd network-traffic-detection
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:
```
python src/main.py
```

Make sure to configure the network interface and other settings in `src/configs/settings.yaml` before running the application.

## Modules

- **src/main.py**: Entry point of the application. Loads the model, captures traffic, preprocesses data, and logs predictions.
- **src/utils/capture.py**: Contains functions to capture network traffic using libraries like `scapy` or `pyshark`.
- **src/utils/preprocess.py**: Preprocesses the captured traffic data into the format required by the ConvLSTM model.
- **src/utils/logging_setup.py**: Sets up logging for the application, configuring the format and level of logs.
- **src/configs/settings.yaml**: Configuration settings for the application, including model paths and network interface details.
- **models/convlstm_model.keras**: The trained ConvLSTM model saved in Keras format.

## License

This project is licensed under the MIT License. See the LICENSE file for details.