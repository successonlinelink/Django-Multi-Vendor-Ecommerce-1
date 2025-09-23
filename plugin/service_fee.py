from decimal import Decimal

def calculate_service_fee(order_total): # Function to calculate service fee based on order total
    # Assuming a fixed service fee rate of 5% for this example
    service_fee = 5
    return Decimal(order_total) * Decimal(service_fee) / 100 # Calculate service fee as a percentage of the order total
    # Return the calculated service fee
    # Note: The service fee rate can be adjusted as needed, or fetched from a configuration file or database