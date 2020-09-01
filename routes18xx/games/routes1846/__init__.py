from routes18xx.cell import Cell
from routes18xx.boardtile import EasternTerminus
from routes18xx.route import Route

CHICAGO_COORD = "D6"
CHICAGO_CONNECTIONS_COORD = "C5"

def filter_invalid_routes(routes, board, railroad):
    """
    Given a collection of routes, returns a new set containing only valid
    routes, considering features specific to 1846. Invalid routes removed:
    - east to east
    """
    # A sieve style filter. If a condition isn't met, iteration continues to the next item. Items meeting all conditions
    # are added to valid_routes at the end of the loop iteration.
    valid_routes = set()
    for route in routes:
        # A route cannot run from east to east
        if isinstance(route.stops[0], EasternTerminus) and isinstance(route.stops[-1], EasternTerminus):
            continue

        valid_routes.add(route)

    return valid_routes

def hook_route_set_values(route_set, railroad):
    raw_values = {route: route.value for route in route_set}
    if railroad.has_private_company("Mail Contract") and route_set:
        longest_route = max(route_set, key=lambda run_route: len(run_route.stops))
        raw_values[longest_route] = hook_route_max_value(longest_route, railroad)
    return raw_values

def hook_route_max_value(route, railroad):
    raw_value = route.value
    if railroad.has_private_company("Mail Contract"):
        raw_value += len(route.stops) * 10
    return raw_value
