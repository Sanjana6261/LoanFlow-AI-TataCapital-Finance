import random

def log_approval(data):
    return "0x" + "".join(random.choices("0123456789abcdef", k=64))