ZONE_TYPE_MULTIPLIER = {
    "restricted": 1.5,
    "security": 2.0,
    "work_place": 1.0,
    "warning": 1.2
}


def calculate_risk(person_count, zone_hits):

    risk = 0.0

    # Crowd risk
    if person_count == 0:
        crowd_score = 0
    elif person_count <= 2:
        crowd_score = 10
    elif person_count <= 5:
        crowd_score = 30
    elif person_count <= 8:
        crowd_score = 50
    else:
        crowd_score = 70

    risk += crowd_score

    # Zone risk
    for zone in zone_hits:
        multiplier = ZONE_TYPE_MULTIPLIER.get(zone.zone_type, 1.0)
        risk += zone.risk_weight * multiplier

    return min(round(risk, 2), 100)
