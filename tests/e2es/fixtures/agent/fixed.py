def subtotal(balances):
    return sum(balance for balance in balances if balance.active)

