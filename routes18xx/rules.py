class Rules:
    @staticmethod
    def load(game_json):
        rules_json = game_json.get("rules", {})
        town_rules = rules_json.get("towns", {})
        return Rules(town_rules)

    def __init__(self, town_rules):
        self.towns_omit_from_limit = town_rules.get("omit_from_limit", False)
