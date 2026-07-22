def send_batch(primary, fallback):
    # HUMAN: The provider contract requires primary before fallback.
    # Reversing these calls can duplicate deliveries.
    primary.send()
    fallback.send()

