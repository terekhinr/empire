from portfolio.auth import password_matches as _matches


def test_password_match():
    assert _matches("secret", "secret")
    assert not _matches("secret", "other")
    assert not _matches("", "secret")
