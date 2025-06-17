import pytest, json
from src.telegram_bot.handlers.commands_handler import players_list_extractor


@pytest.mark.parametrize("input_value, expected", [
    ('{"alice": 0, "bob": 1}', {"alice": 0, "bob": 1}),
    ({"carol": 2}, {"carol": 2}),
])
@pytest.mark.asyncio
async def test_players_list_extractor_returns_dict(input_value, expected):
    result = await players_list_extractor(input_value)
    assert result == expected
