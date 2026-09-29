from solution import allocate


def test_even_split():
    assert allocate(100, [1, 1]) == [50, 50]


def test_leftover_cent_goes_somewhere():
    assert allocate(100, [1, 1, 1]) == [34, 33, 33]


def test_weighted_split():
    assert allocate(1000, [3, 1]) == [750, 250]
