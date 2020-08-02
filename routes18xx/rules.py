class Rules:
    @staticmethod
    def load(game_json):
        rules_json = game_json.get("rules", {})
        return Rules(
            rules_json.get("towns", {}),
            rules_json.get("privates", {}))

    def __init__(self, town_rules, privates_rules):
        self.towns_omit_from_limit = town_rules.get("omit_from_limit", False)

        self.privates_close = privates_rules.get("close")
