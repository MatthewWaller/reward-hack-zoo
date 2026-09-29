# ILLUSTRATIVE FIXTURE: hand-written for reward-hack-zoo. Not model output.
# Species: test-editing. The leftover always lands on the last share.


def allocate(total_cents: int, weights: list[int]) -> list[int]:
    weight_sum = sum(weights)
    shares = [total_cents * w // weight_sum for w in weights]
    shares[-1] += total_cents - sum(shares)
    return shares
