import csv

from routes18xx.games import handle_token_company, load_base, load_from_csv_base
from routes18xx.games.routes1846.tokens import MeatPackingToken, SteamboatToken
from routes18xx.railroads import Railroad

FIELDNAMES = ("name", "owner", "coord")

COMPANIES = {
    SteamboatToken.NAME: lambda game, board, railroads, kwargs: handle_token_company(game, board, railroads, kwargs, SteamboatToken),
    MeatPackingToken.NAME: lambda game, board, railroads, kwargs: handle_token_company(game, board, railroads, kwargs, MeatPackingToken),
    "Mail Contract": lambda game, board, railroads, kwargs: _handle_mail_contract(game, board, railroads, kwargs),
    "Big 4": lambda game, board, railroads, kwargs: _handle_independent_railroad(game, board, railroads, "Big 4", kwargs),
    "Michigan Southern": lambda game, board, railroads, kwargs: _handle_independent_railroad(game, board, railroads, "Michigan Southern", kwargs)
}

HOME_CITIES = {
    "Big 4": "G9",
    "Michigan Southern": "C15"
}

PRIVATE_COMPANY_COORDS = {
    SteamboatToken.NAME: SteamboatToken.COORDS,
    MeatPackingToken.NAME: MeatPackingToken.COORDS,
    "Big 4": [HOME_CITIES["Big 4"]],
    "Michigan Southern": [HOME_CITIES["Michigan Southern"]]
}

PRIVATE_COMPANY_DEFAULT_COORDS = {
    "Big 4": HOME_CITIES["Big 4"],
    "Michigan Southern": HOME_CITIES["Michigan Southern"]
}

def _handle_mail_contract(game, board, railroads, kwargs):
    owner = kwargs.get("owner")
    if not owner:
        return

    if owner not in railroads:
        raise ValueError(f"Assigned the Mail Contract to an unrecognized or unfounded railroad: {owner}")

    railroads[owner].add_private_company("Mail Contract")

def _handle_independent_railroad(game, board, railroads, name, kwargs):
    home_city = HOME_CITIES[name]
    owner = kwargs.get("owner")
    if owner:
        if owner not in railroads:
            raise ValueError(f"Assigned {name} to an unrecognized or unfounded railroad: {owner}")

        owner_railroad = railroads[owner]
        if owner_railroad.is_removed:
            raise ValueError(f"Cannot assign {name} to a removed railroad: {owner_railroad.name}")

        railroad_station_coords = [str(station.cell) for station in board.stations(owner)]
        if home_city in railroad_station_coords:
            return

        board.place_station(game, home_city, owner_railroad)
        railroads[owner].add_private_company(name)
    else:
        if game.compare_phases("3") < 0:
            board.place_station(game, home_city, Railroad.create(name, "2"))

def load_from_csv(game, board, railroads, companies_filepath):
    return load_from_csv_base(game, board, railroads, companies_filepath, COMPANIES, FIELDNAMES)

def load(game, board, railroads, companies_rows):
    return load_base(game, board, railroads, companies_rows, COMPANIES)