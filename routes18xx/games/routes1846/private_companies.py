import csv

from routes18xx.railroads import Railroad
from routes18xx.games.routes1846.tokens import MeatPackingToken, SteamboatToken

FIELDNAMES = ("name", "owner", "coord")

COMPANIES = {
    "Steamboat Company": lambda game, board, railroads, kwargs: _handle_steamboat_company(game, board, railroads, kwargs),
    "Meat Packing Company": lambda game, board, railroads, kwargs: _handle_meat_packing_company(game, board, railroads, kwargs),
    "Mail Contract": lambda game, board, railroads, kwargs: _handle_mail_contract(game, board, railroads, kwargs),
    "Big 4": lambda game, board, railroads, kwargs: _handle_independent_railroad(game, board, railroads, "Big 4", kwargs),
    "Michigan Southern": lambda game, board, railroads, kwargs: _handle_independent_railroad(game, board, railroads, "Michigan Southern", kwargs)
}

HOME_CITIES = {
    "Big 4": "G9",
    "Michigan Southern": "C15"
}

def _handle_steamboat_company(game, board, railroads, kwargs):
    owner = kwargs.get("owner")
    coord = kwargs["coord"]
    if not owner or not coord:
        return

    if owner not in railroads:
        raise ValueError("Assigned the Steamboat Company to an unrecognized or unfounded railroad: {}".format(owner))

    board.place_token(coord, railroads[owner], SteamboatToken)
    railroads[owner].add_private_company("Steamboat Company")

def _handle_meat_packing_company(game, board, railroads, kwargs):
    owner = kwargs.get("owner")
    coord = kwargs["coord"]
    if not owner or not coord:
        return

    if owner not in railroads:
        raise ValueError("Assigned the Meat Packing Company to an unrecognized or unfounded railroad: {}".format(owner))

    board.place_token(coord, railroads[owner], MeatPackingToken)
    railroads[owner].add_private_company("Meat Packing Company")

def _handle_mail_contract(game, board, railroads, kwargs):
    owner = kwargs.get("owner")
    if not owner:
        return

    if owner not in railroads:
        raise ValueError("Assigned the Mail Contract to an unrecognized or unfounded railroad: {}".format(owner))

    railroads[owner].add_private_company("Mail Contract")

def _handle_independent_railroad(game, board, railroads, name, kwargs):
    home_city = HOME_CITIES[name]
    owner = kwargs.get("owner")
    if owner:
        if owner not in railroads:
            raise ValueError("Assigned {} to an unrecognized or unfounded railroad: {}".format(name, owner))

        owner_railroad = railroads[owner]
        if owner_railroad.is_removed:
            raise ValueError("Cannot assign {} to a removed railroad: {}".format(name, owner_railroad.name))

        railroad_station_coords = [str(station.cell) for station in board.stations(owner)]
        if home_city in railroad_station_coords:
            return

        board.place_station(home_city, owner_railroad)
        railroads[owner].add_private_company(name)
    else:
        if game.compare_phases("3") < 0:
            board.place_station(home_city, Railroad.create(name, "2"))


def load_from_csv(game, board, railroads, companies_filepath):
    if companies_filepath:
        with open(companies_filepath, newline='') as companies_file:
            return load(game, board, railroads, tuple(csv.DictReader(companies_file, fieldnames=FIELDNAMES, delimiter=';', skipinitialspace=True)))

def load(game, board, railroads, companies_rows):
    if not companies_rows:
        return

    private_company_names = [company["name"] for company in companies_rows]
    if len(private_company_names) != len(set(private_company_names)):
        raise ValueError("Each private company should only have a single entry.")

    for company_kwargs in companies_rows:
        name = company_kwargs.get("name")
        if name not in COMPANIES:
            raise ValueError("An unrecognized private company was provided: {}".format(name))

        COMPANIES[name](game, board, railroads, company_kwargs)