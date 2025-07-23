def fuzzify_rssi(rssi):
    if rssi >= -60:
        return "High"
    elif rssi >= -80:
        return "Medium"
    else:
        return "Low"

def fuzzify_latency(latency):
    if latency <= 50:
        return "Good"
    elif latency <= 150:
        return "Average"
    else:
        return "Poor"

def fuzzify_packet_loss(loss):
    if loss < 1:
        return "Low"
    elif loss < 5:
        return "Medium"
    else:
        return "High"

def fuzzify_throughput(tp):
    if tp >= 100:
        return "High"
    elif tp >= 30:
        return "Medium"
    else:
        return "Low"

def evaluate_qos(rssi, latency, loss, throughput):
    rssi_level = fuzzify_rssi(rssi)
    latency_level = fuzzify_latency(latency)
    loss_level = fuzzify_packet_loss(loss)
    tp_level = fuzzify_throughput(throughput)

    print(f"Fuzzy Levels: RSSI={rssi_level}, Latency={latency_level}, Loss={loss_level}, TP={tp_level}")

    # Apply fuzzy rules
    if rssi_level == "High" and latency_level == "Good" and loss_level == "Low" and tp_level == "High":
        return "High"
    elif latency_level == "Poor" or loss_level == "High":
        return "Low"
    else:
        return "Medium"

print(evaluate_qos(1212.2,-66.8,16.37,11))