import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt

# Load and preprocess
df = pd.read_csv("network_data.csv", parse_dates=['Timestamp'])

# Rename columns for consistency
df = df.rename(columns={
    'RSSI (dBm)': 'rssi',
    'Latency (ms)': 'latency',
    'Packet Loss (%)': 'packet_loss',
    'Throughput (KB/s)': 'throughput'
})

# Set Timestamp as index and sort
df = df.set_index('Timestamp')
df = df.sort_index()

# Select only numeric QoS metric columns
metrics = ['rssi', 'latency', 'packet_loss', 'throughput']
data = df[metrics].copy()

# Resample to 1-minute intervals using mean, only on numeric data
data = data.resample('1min').mean().interpolate()

# 1️⃣ Truncated SVD Denoising
svd = TruncatedSVD(n_components=2)
reduced = svd.fit_transform(data)
reconstructed = svd.inverse_transform(reduced)
df_reconstructed = pd.DataFrame(reconstructed, columns=metrics, index=data.index)

# 2️⃣ ARIMA Forecasting
forecast_horizon = 3
forecast_results = {}

for metric in metrics:
    series = df_reconstructed[metric]
    try:
        model = ARIMA(series, order=(2, 1, 2))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=forecast_horizon)
        forecast_results[metric] = forecast
    except Exception as e:
        print(f"ARIMA failed for {metric}: {e}")
        forecast_results[metric] = [np.nan] * forecast_horizon

# Create forecast DataFrame
forecast_df = pd.DataFrame(forecast_results)
forecast_df.index = pd.date_range(start=df_reconstructed.index[-1], periods=forecast_horizon + 1, freq='1min')[1:]

# 3️⃣ QoS Classification
def classify_qos(row):
    if row['latency'] < 50 and row['rssi'] > -60 and row['packet_loss'] < 1 and row['throughput'] > 100:
        return "High"
    elif row['latency'] > 150 or row['packet_loss'] > 5 or row['throughput'] < 30:
        return "Low"
    else:
        return "Medium"

forecast_df['QoS'] = forecast_df.apply(classify_qos, axis=1)

# 4️⃣ Display Forecast
print("QoS Forecast for Next 3 Minutes:")
print(forecast_df)

# 5️⃣ Optional Plot
forecast_df[metrics].plot(title="Forecasted QoS Metrics", marker='o')
plt.xlabel("Timestamp")
plt.ylabel("Metric Value")
plt.grid(True)
plt.tight_layout()
plt.show()
