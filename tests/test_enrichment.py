from polymarket_telegram_bot.enrichment import MarketMetadataResolver


def test_extract_outcome_maps_token_id_to_outcome() -> None:
    market = {
        "clobTokenIds": '["111","222"]',
        "outcomes": '["Yes","No"]',
    }
    outcome = MarketMetadataResolver._extract_outcome(market, "222")
    assert outcome == "No"


def test_extract_outcome_fallback_fields() -> None:
    market = {"subtitle": "Bullish"}
    outcome = MarketMetadataResolver._extract_outcome(market, "111")
    assert outcome == "Bullish"
