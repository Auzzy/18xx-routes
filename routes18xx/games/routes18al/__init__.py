NASHVILLE_COORD = "A4"
BIRMINGHAM_COORD = "G4"
ATLANTA_COORD = "G8"
MOBILE_COORD = "Q2"

def _contains_atlanta_to_birmingham(route):
    coords = {str(space.cell) for space in route}
    return ATLANTA_COORD in coords and BIRMINGHAM_COORD in coords

def _contains_nashville_to_mobile(route):
    coords = {str(space.cell) for space in route}
    return NASHVILLE_COORD in coords and MOBILE_COORD in coords

def hook_route_set_values(route_set, railroad):
    raw_values = {route: route.value for route in route_set}
    if railroad.has_private_company("Memphis and Charleston RR") and route_set:
        for route in route_set:
            if _contains_atlanta_to_birmingham(route):
                raw_values[route] = hook_route_max_value(route, railroad)
                break

        for route in route_set:
            if _contains_nashville_to_mobile(route):
                raw_values[route] = hook_route_max_value(route, railroad)
                break
    return raw_values

def hook_route_max_value(route, railroad):
    raw_value = route.value
    if railroad.has_private_company("Memphis and Charleston RR"):
        if _contains_atlanta_to_birmingham(route):
            raw_value += 20
        elif _contains_nashville_to_mobile(route):
            raw_value += 40
    return raw_value