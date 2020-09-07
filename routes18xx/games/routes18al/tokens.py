from routes18xx.tokens import PrivateCompanyToken

class SNAToken(PrivateCompanyToken):
    NAME = "South and North Alabama RR"
    COORDS = ("E6", "G4", "G6", "H3", "H5")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place the {SNAToken.NAME} token: {railroad.name}")

        if str(cell) not in SNAToken.COORDS:
            raise ValueError(f"It is not legal to place the {SNAToken.NAME} token on this space ({cell}).")

        bonus = properties.get("sna_value")
        if not bonus:
            raise ValueError(f"{cell} does not define a {SNAToken.NAME} bonus value.")

        return SNAToken(SNAToken.NAME, cell, railroad, bonus)