def subtotal(balances):
    # Add every active balance.
    return sum(balance for balance in balances if balance.active)

