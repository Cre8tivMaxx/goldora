from pure_life.dashboard import add_reverse_link


def get_data(data=None):
	return add_reverse_link(data, "Expense Claim", "vehicle_log")
