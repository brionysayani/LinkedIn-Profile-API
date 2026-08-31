from app.config import Settings


def test_linkedin_prefixed_environment_names_are_supported(monkeypatch):
    monkeypatch.delenv("LI_AT", raising=False)
    monkeypatch.delenv("JSESSIONID", raising=False)
    monkeypatch.setenv("LINKEDIN_LI_AT", "li-at-token")
    monkeypatch.setenv("LINKEDIN_JSESSIONID", "ajax:123")
    monkeypatch.setenv("USER_AGENT", "Mozilla/5.0")

    settings = Settings()

    assert settings.li_at == "li-at-token"
    assert settings.jsessionid == "ajax:123"
    assert settings.user_agent == "Mozilla/5.0"
