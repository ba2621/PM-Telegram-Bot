from polymarket_telegram_bot.polymarket_stream import parse_ws_message


def test_parse_ws_message_extracts_trade_from_nested_data() -> None:
    raw = (
        '{"type":"trade","data":{"price":"0.52","size":"300000","side":"BUY",'
        '"asset_id":"123","timestamp":1730000000,"transactionHash":"0xabc",'
        '"maker_address":"0xmaker","taker_address":"0xtaker"}}'
    )

    trades = parse_ws_message(raw)
    assert len(trades) == 1
    trade = trades[0]

    assert trade.token_id == "123"
    assert trade.side == "BUY"
    assert trade.notional_usd == 156000.0
    assert trade.tx_hash == "0xabc"


def test_parse_ws_message_ignores_non_trade_payload() -> None:
    raw = '{"type":"heartbeat","ts":1730000000}'
    trades = parse_ws_message(raw)
    assert trades == []


def test_parse_ws_message_supports_last_trade_price_shape() -> None:
    raw = (
        '{"asset_id":"123","last_trade_price":"0.51","size":"250000","side":"SELL",'
        '"timestamp":1730000002}'
    )
    trades = parse_ws_message(raw)
    assert len(trades) == 1
    assert trades[0].notional_usd == 127500.0
