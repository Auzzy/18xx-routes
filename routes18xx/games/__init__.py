import csv

def load_from_csv_base(game, board, railroads, companies_filepath, company_dict, fieldnames=("name", "owner", "coord")):
    if companies_filepath:
        with open(companies_filepath, newline='') as companies_file:
            companies_rows = tuple(csv.DictReader(companies_file, fieldnames=fieldnames, delimiter=';', skipinitialspace=True))
            return load_base(game, board, railroads, companies_rows, company_dict)

def load_base(game, board, railroads, companies_rows, company_dict):
    if not companies_rows:
        return

    private_company_names = [company["name"] for company in companies_rows]
    if len(private_company_names) != len(set(private_company_names)):
        raise ValueError("Each private company should only have a single entry.")

    for company_kwargs in companies_rows:
        name = company_kwargs.get("name")
        if name not in company_dict:
            raise ValueError(f"An unrecognized private company was provided: {name}")

        company_dict[name](game, board, railroads, company_kwargs)

def handle_token_company(game, board, railroads, kwargs, Token):
    owner = kwargs.get("owner")
    coord = kwargs["coord"]
    if not owner or not coord:
        return

    if owner not in railroads:
        raise ValueError(f"Assigned the {Token.NAME} to an unrecognized or unfounded railroad: {owner}")

    board.place_token(coord, railroads[owner], Token)
    railroads[owner].add_private_company(Token.NAME)