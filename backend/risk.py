def classify_speed(kmh, limit):
    if kmh <= limit:
        return "within_limit"
    elif kmh <= limit + 5:
        return "grace"
    else:
        return "overspeed"
