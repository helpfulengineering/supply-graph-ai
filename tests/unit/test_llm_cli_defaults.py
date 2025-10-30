import importlib


def test_anthropic_default_model_is_latest():
    llm_cli = importlib.import_module('src.cli.llm')
    # Ensure the default model for Anthropic matches centralized default
    assert llm_cli._get_default_model('anthropic') == 'claude-sonnet-4-5-20250929'


def test_create_llm_service_applies_default_when_model_missing(monkeypatch):
    """When provider is set and model omitted, a default model should be applied."""
    calls = {}

    async def fake_create_llm_service_with_selection(cli_provider=None, cli_model=None, verbose=False):
        calls['provider'] = cli_provider
        calls['model'] = cli_model
        class Dummy:
            async def health_check(self):
                return True
            async def shutdown(self):
                return None
        return Dummy()

    llm_cli = importlib.import_module('src.cli.llm')
    monkeypatch.setattr(llm_cli, 'create_llm_service_with_selection', fake_create_llm_service_with_selection)

    # Run
    import asyncio
    asyncio.get_event_loop().run_until_complete(llm_cli._create_llm_service(provider='anthropic', model=None))

    # Assert default model applied
    assert calls['provider'] == 'anthropic'
    assert calls['model'] == 'claude-sonnet-4-5-20250929'


