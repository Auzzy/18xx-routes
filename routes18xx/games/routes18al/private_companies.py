import csv

from routes18xx.games import handle_token_company, load_base, load_from_csv_base
from routes18xx.games.routes18al.tokens import SNAToken
from routes18xx.railroads import Railroad

FIELDNAMES = ("name", "owner", "coord")

COMPANIES = {
    SNAToken.NAME: lambda game, board, railroads, kwargs: handle_token_company(game, board, railroads, kwargs, SNAToken),
    "Memphis and Charleston RR": lambda game, board, railroads, kwargs: _handle_mcrr(game, board, railroads, kwargs)
}

PRIVATE_COMPANY_COORDS = {
    SNAToken.NAME: SNAToken.COORDS
}

def _handle_mcrr(game, board, railroads, kwargs):
    owner = kwargs.get("owner")
    if not owner:
        return

    if owner not in railroads:
        raise ValueError(f"Assigned the Memphis and Charleston RR to an unrecognized or unfounded railroad: {owner}")

    print(f"railroad: {railroads[owner].name}")
    railroads[owner].add_private_company("Memphis and Charleston RR")

def load_from_csv(game, board, railroads, companies_filepath):
    return load_from_csv_base(game, board, railroads, companies_filepath, COMPANIES, FIELDNAMES)

def load(game, board, railroads, companies_rows):
    return load_base(game, board, railroads, companies_rows, COMPANIES)