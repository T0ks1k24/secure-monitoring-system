def point_in_polygon(x, y, polygon):

    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi = polygon[i]["x"]
        yi = polygon[i]["y"]
        xj = polygon[j]["x"]
        yj = polygon[j]["y"]

        intersect = ((yi > y) != (yj > y)) and \
            (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi)

        if intersect:
            inside = not inside

        j = i

    return inside


def is_inside(bbox, polygon):
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return point_in_polygon(cx, cy, polygon)
