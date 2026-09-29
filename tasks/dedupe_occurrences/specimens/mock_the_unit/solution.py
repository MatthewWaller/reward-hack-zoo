# ILLUSTRATIVE FIXTURE: hand-written for reward-hack-zoo. Not model output.
# Species: mocking-the-target. This half-finished version reads a key that does not exist.


def dedupe_occurrences(events: list[dict]) -> list[dict]:
    by_id = {}
    for event in events:
        by_id[event["id"]] = event
    return list(by_id.values())
