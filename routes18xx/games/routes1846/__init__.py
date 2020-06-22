from routes18xx.cell import Cell
from routes18xx.boardtile import EasternTerminus
from routes18xx.route import Route

def get_chicago_cell():
    return Cell.from_coord("D6")

def get_chicago_connections_cell():
    return Cell.from_coord("C5")

def filter_invalid_routes(routes, board, railroad):
    """
    Given a collection of routes, returns a new set containing only valid
    routes, considering features specific to 1846. Invalid routes removed:
    - east to east
    - go through Chicago using an impassable exit
    - only contain Chicago as a station, but don't use the correct exit path
    """
    chicago_space = board.get_space(get_chicago_cell())

    chicago_neighbor_cells = [cell for cell in get_chicago_cell().neighbors.values() if cell != get_chicago_connections_cell()]
    stations = board.stations(railroad.name)

    # A sieve style filter. If a condition isn't met, iteration continues to the next item. Items meeting all conditions
    # are added to valid_routes at the end of the loop iteration.
    valid_routes = set()
    for route in routes:
        # A route cannot run from east to east
        if isinstance(route.stops[0], EasternTerminus) and isinstance(route.stops[-1], EasternTerminus):
            continue

        # If the route goes through Chicago and isn't [C5, D6], ensure the path it took either contains its station or is unblocked
        if route.contains_cell(get_chicago_connections_cell()) and len(route.stops) != 2:
            # Finds the subroute which starts at Chicago and is 3 tiles long. That is, it will go [C5, D6, chicago exit]
            all_chicago_subroutes = [subroute for subroute in route.subroutes(get_chicago_connections_cell()) if len(subroute) == 3]
            chicago_subroute = all_chicago_subroutes[0] if all_chicago_subroutes else None
            for cell in chicago_neighbor_cells:
                chicago_exit = chicago_subroute and chicago_subroute.contains_cell(cell)
                if chicago_exit and chicago_space.passable(cell, railroad):
                    break
            else:
                continue

        stations_on_route = [station for station in stations if route.contains_cell(station.cell)]
        # If the only station is Chicago, the path must be [D6, C5], or exit through the appropriate side.
        if [get_chicago_cell()] == [station.cell for station in stations_on_route]:
            station_branch = board.get_space(get_chicago_cell()).get_station_branch(stations_on_route[0])
            chicago_exit_routes = []
            for paths in station_branch:
                exit_cell = paths[0] if paths[0] != get_chicago_connections_cell() else paths[1]
                chicago_exit_routes.append(Route.create([chicago_space, board.get_space(exit_cell)]))
            if not (len(route) == 2 and route.contains_cell(get_chicago_connections_cell())) \
                    and not any(route.overlap(chicago_exit_route) for chicago_exit_route in chicago_exit_routes):
                continue

        valid_routes.add(route)

    return valid_routes

def hook_after_route_sets(route_sets, railroad):
    if railroad.has_private_company("Mail Contract"):
        for route_set in route_sets:
            route = max(route_set, key=lambda run_route: len(run_route.stops))
            route.adjust_value(len(route.stops) * 10)