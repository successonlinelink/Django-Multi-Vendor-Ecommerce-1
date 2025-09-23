from plugin.countries import countries 

def tax_calculation(country, order_total): # Function to calculate tax based on country and order total
    tax_rate = 0 # Initialize tax rate to 0 -  by default the tax rate is 0 until it is calculated
    
    for c in countries(): # Loop through the list of countries
        if country == c['country']: # Check if the country matches
            tax_rate += int(float(c['tax_rate'])) / 100 * float(order_total) # Calculate tax based on the tax rate and order total

    return tax_rate # Return the calculated tax
    