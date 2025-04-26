from сollecting_data_for_training.script import Agent
from manual_marking.app import app

listing = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "ADAUSDT",
    "SOLUSDT"
]

# Agent().historical_data("ETHUSDT")

app.run(debug=True)