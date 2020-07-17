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
    - go through Chicago using an impassable exit
    - only contain Chicago as a station, but don't use the correct exit path
    """
    chicago_cell = board.cell(CHICAGO_COORD)
    chicago_connections_cell = board.cell(CHICAGO_CONNECTIONS_COORD)
    chicago_space = board.get_space(chicago_cell)

    chicago_neighbor_cells = [cell for cell in chicago_cell.neighbors.values() if cell != chicago_connections_cell]
    stations = board.stations(railroad.name)

    # A sieve style filter. If a condition isn't met, iteration continues to the next item. Items meeting all conditions
    # are added to valid_routes at the end of the loop iteration.
    valid_routes = set()
    for route in routes:
        # A route cannot run from east to east
        if isinstance(route.stops[0], EasternTerminus) and isinstance(route.stops[-1], EasternTerminus):
            continue

        # If the route goes through Chicago and isn't [C5, D6], ensure the path it took either contains its station or is unblocked
        if route.contains_cell(chicago_connections_cell) and len(route.stops) != 2:
            # Finds the subroute which starts at Chicago and is 3 tiles long. That is, it will go [C5, D6, chicago exit]
            all_chicago_subroutes = [subroute for subroute in route.subroutes(chicago_connections_cell) if len(subroute) == 3]
            chicago_subroute = all_chicago_subroutes[0] if all_chicago_subroutes else None
            for cell in chicago_neighbor_cells:
                chicago_exit = chicago_subroute and chicago_subroute.contains_cell(cell)
                if chicago_exit and chicago_space.passable(cell, railroad):
                    break
            else:
                continue

        stations_on_route = [station for station in stations if route.contains_cell(station.cell)]
        # If the only station is Chicago, the path must be [D6, C5], or exit through the appropriate side.
        if [chicago_cell] == [station.cell for station in stations_on_route]:
            station_branch = board.get_space(chicago_cell).get_station_branch(stations_on_route[0])
            chicago_exit_routes = []
            for paths in station_branch:
                exit_cell = paths[0] if paths[0] != chicago_connections_cell else paths[1]
                chicago_exit_routes.append(Route.create([chicago_space, board.get_space(exit_cell)]))
            if not (len(route) == 2 and route.contains_cell(chicago_connections_cell)) \
                    and not any(route.overlap(chicago_exit_route) for chicago_exit_route in chicago_exit_routes):
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
