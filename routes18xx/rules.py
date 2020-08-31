class Rules:
    @staticmethod
    def load(game_json):
        rules_json = game_json.get("rules", {})
        return Rules(
            RailroadRules.load(rules_json),
            StationRules.load(rules_json),
            PrivateRules.load(rules_json),
            RouteRules.load(rules_json))

    def __init__(self, railroad_rules, station_rules, private_rules, route_rules):
        self.railroads = railroad_rules
        self.stations = station_rules
        self.privates = private_rules
        self.routes = route_rules

class RailroadRules:
    @staticmethod
    def load(rules_json):
        railroad_rules_json = rules_json.get("railroads", {})
        return RailroadRules(
            railroad_rules_json.get("can_close", True)
        )

    def __init__(self, can_close=True):
        self.can_close = can_close

class StationRules:
    @staticmethod
    def load(rules_json):
        stations_rules_json = rules_json.get("stations", {})
        return StationRules(
            stations_rules_json.get("reserved_until")
        )

    def __init__(self, reserved_until=None):
        self.reserved_until = reserved_until

class PrivateRules:
    @staticmethod
    def load(rules_json):
        private_rules = rules_json.get("privates", {})
        return PrivateRules(
            private_rules.get("close", {})
        )

    def __init__(self, close={}):
        self.close = close

class RouteRules:
    @staticmethod
    def load(rules_json):
        route_rules = rules_json.get("routes", {})
        return RouteRules(
            route_rules.get("omit_towns_from_limit", False)
        )

    def __init__(self, omit_towns_from_limit=False):
        self.omit_towns_from_limit = omit_towns_from_limit