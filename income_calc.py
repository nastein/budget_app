def calculate_tax(taxable_income, brackets):
	"""
	taxable_income : float
	brackets : list of tuples (upper_limit, rate)
	           upper_limit is the top of the bracket
	           rate is decimal (e.g. 0.22 for 22%)
	           Use None for final unlimited bracket.
	           
	Returns total tax owed.
	"""
	tax_owed = 0
	previous_limit = 0

	for upper_limit, rate in brackets:
	    
	    if upper_limit is None:
	        # Last bracket
	        taxable_amount = taxable_income - previous_limit
	    else:
	        taxable_amount = min(taxable_income, upper_limit) - previous_limit
	    
	    if taxable_amount <= 0:
	        break
	    
	    tax_owed += taxable_amount * rate
	    
	    if upper_limit is None or taxable_income <= upper_limit:
	        break
	    
	    previous_limit = upper_limit

	return tax_owed

def income_c(gross_income, cont401k_personal=0, match401k_rate=0, 
           HSA_cont_monthly=0, healthcare_cost_permonth=0, debug=False):

	cont401k_rate = cont401k_personal / gross_income
	cont401k_total = gross_income * (cont401k_rate + match401k_rate)

	HSA_cont = HSA_cont_monthly * 12
	healthcare_cost = healthcare_cost_permonth * 12

	FICA_rate = 7.65 / 100
	standard_deduction = 16100

	taxable_income = (
	    gross_income 
	    - cont401k_rate * gross_income 
	    - standard_deduction 
	    - HSA_cont 
	    - healthcare_cost
	)

	tax_brackets = [(.1,12400), (.12,50400), (.22,105700)]
	income_tax = calculate_tax(taxable_income, tax_brackets)
	FICA_tax = gross_income * FICA_rate

	net_income = (
	    gross_income 
	    - FICA_tax 
	    - income_tax 
	    - gross_income * cont401k_rate 
	    - HSA_cont 
	    - healthcare_cost
	)

	monthly_income = net_income / 12
	pretax_savings = cont401k_total + HSA_cont
	monthly_pretax_savings = pretax_savings / 12

	monthly_401k = cont401k_total / 12
	monthly_HSA = HSA_cont / 12

	if debug:
	    print("\nINCOME BREAKDOWN")
	    print("-" * 80)
	    print(f"{'Category':<35} {'Monthly':>12}   {'Yearly':>12}")
	    print("-" * 80)

	    print_row("Net Income", monthly_income)
	    print_row("401k Total (w/ match)", monthly_401k)
	    print_row("HSA", monthly_HSA)

	return monthly_income, monthly_401k, monthly_HSA