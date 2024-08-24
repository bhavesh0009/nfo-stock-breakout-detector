# NFO Stock Breakout Detector

Automated tool to detect breakouts in NSE Futures & Options (F&O) stocks using the Angel One API. This project scans NSE F&O stocks for potential breakouts, identifies both full and partial breakouts, and generates detailed reports.

## Features

- Scans NSE F&O stocks for potential breakouts
- Identifies both full and partial breakouts
- Uses historical data and technical indicators for analysis
- Generates CSV reports with datetime stamps
- Implements rate limiting and error handling for robust API interactions
- Customizable breakout criteria

## Prerequisites

- Python 3.7+
- Angel One trading account with API access

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/nfo-stock-breakout-detector.git
   cd nfo-stock-breakout-detector
   ```

2. Create a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install required packages:

   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   Create a `.env` file in the project root and add your Angel One API credentials:

   ```
   ANGEL_ONE_APP_KEY=your_app_key
   ANGEL_ONE_CLIENT_ID=your_client_id
   ANGEL_ONE_TOTP_SECRET=your_totp_secret
   ANGEL_ONE_PIN=your_pin
   ```

## Usage

1. Ensure your Angel One credentials are set up in the `.env` file.

2. Run the main script:

   ```
   python main.py
   ```

3. The script will:
   - Fetch the latest instrument data
   - Prepare a list of stocks to scan
   - Scan for breakouts
   - Generate a CSV report with the results

4. Check the console output for a summary of detected breakouts.

5. Find the detailed breakout report in the generated CSV file (format: `breakout_stocks_YYYYMMDD_HHMMSS.csv`).

## Configuration

You can customize the breakout detection criteria by modifying the following parameters in `main.py`:

- `lookback`: Number of days to look back for establishing the previous high (default: 20)
- `volume_threshold`: Volume increase threshold for confirming a breakout (default: 1.5)
- `atr_multiple`: Multiple of ATR for considering a breakout significant (default: 1.0)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Disclaimer

This tool is for educational and informational purposes only. It is not intended to be used as financial advice. Always do your own research and consult with a qualified financial advisor before making any investment decisions.

## Contact

Your Name - [@bhavesh_09](https://x.com/bhavesh_09) - <bhavesh.ghodasara@gmail.com>

Project Link: [https://github.com/yourusername/nfo-stock-breakout-detector](https://github.com/yourusername/nfo-stock-breakout-detector)
