def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, float(value)))


def triangular(value, left, peak, right):
    value = float(value)
    if value <= left or value >= right:
        return 0.0
    if value == peak:
        return 1.0
    if value < peak:
        return (value - left) / (peak - left)
    return (right - value) / (right - peak)


def left_shoulder(value, left, right):
    value = float(value)
    if value <= left:
        return 1.0
    if value >= right:
        return 0.0
    return (right - value) / (right - left)


def right_shoulder(value, left, right):
    value = float(value)
    if value <= left:
        return 0.0
    if value >= right:
        return 1.0
    return (value - left) / (right - left)


def weighted_average(weighted_values, fallback=0.0):
    total_weight = sum(weight for weight, _value in weighted_values)
    if total_weight <= 0:
        return fallback
    return sum(weight * value for weight, value in weighted_values) / total_weight
