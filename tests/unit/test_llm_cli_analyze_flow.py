import importlib
import asyncio
import tempfile
from pathlib import Path
import pytest
import click


@pytest.mark.asyncio
async def test_analyze_raises_on_failure(monkeypatch, tmp_path: Path):
    llm_cli = importlib.import_module('src.cli.llm')

    async def fake_generate_content(*args, **kwargs):
        return {
            'content': 'error details',
            'status': 'error',
            'metadata': {
                'provider': 'anthropic',
                'model': 'claude-3-5-sonnet-latest'
            }
        }

    monkeypatch.setattr(llm_cli, '_generate_content', fake_generate_content)

    # Build a minimal CLI context
    class DummyCtx:
        def __init__(self):
            self.started = False
        def start_command_tracking(self, *_):
            self.started = True
        def end_command_tracking(self):
            self.started = False
    ctx = type('Obj', (), {'obj': DummyCtx()})()

    with pytest.raises(click.ClickException):
        await llm_cli.analyze(
            ctx=ctx,
            project_url='https://github.com/example/project',
            provider='anthropic',
            model=None,
            max_tokens=1000,
            temperature=0.1,
            timeout=30,
            output=str(tmp_path / 'analysis.json'),
            format='json',
            include_code=True,
            include_docs=True,
            verbose=False,
            output_format='text',
            use_llm=True,
            llm_provider='anthropic',
            llm_model=None,
            quality_level='professional',
            strict_mode=False,
        )

    # Ensure file was not written on failure
    assert not (tmp_path / 'analysis.json').exists()


