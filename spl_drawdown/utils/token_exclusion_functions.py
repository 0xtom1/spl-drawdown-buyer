import csv


def get_exclusion_list(column_name: str = "mint_address") -> list:
    """Get exclusion list from data/token_exclusion_list.csv

    Args:
        column_name (str, optional): Defaults to "mint_address".

    Returns:
        list:
    """
    file_path = "spl_drawdown/data/token_exclusion_list.csv"
    column_data = []
    with open(file_path, "r") as file:
        reader = csv.DictReader(file)  # Use DictReader if CSV has headers
        if column_name:
            for row in reader:
                column_data.append(row[column_name])
    return list(set(column_data))
