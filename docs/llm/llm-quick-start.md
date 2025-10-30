# LLM Service Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Set Up API Key

Create `.env` file in project root:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### 2. Test Basic Functionality

```bash
# Check service status
ome llm service status

# Generate simple text
ome llm generate "What is 3D printing?"

# Generate OKH manifest
ome llm generate-okh https://github.com/example/project --preserve-context
```

### 3. Test Matching

```bash
# Test matching capabilities
ome llm match \
  --requirements "3D printing,CNC machining" \
  --capabilities "3D printer,CNC mill" \
  --domain manufacturing
```

## 📋 Common Commands

### Service Management
```bash
ome llm service status          # Check service health
ome llm service metrics         # View usage metrics
ome llm service health          # Detailed health check
```

### Text Generation
```bash
ome llm generate "prompt"                    # Basic generation
ome llm generate "prompt" --max-tokens 200   # With token limit
ome llm generate "prompt" --temperature 0.3  # With temperature
```

### OKH Generation
```bash
ome llm generate-okh <url>                  # Basic OKH generation
ome llm generate-okh <url> --preserve-context  # Keep context files
ome llm generate-okh <url> --quality-level high  # High quality analysis
```

### Matching Analysis
```bash
ome llm match --requirements "req1,req2" --capabilities "cap1,cap2"
ome llm match --domain manufacturing --preserve-context
```

### Provider Management
```bash
ome llm providers list         # List available providers
ome llm providers status       # Check provider status
ome llm providers test anthropic  # Test specific provider
ome llm providers set anthropic   # Set default provider
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional
LLM_ENABLED=true
LLM_DEFAULT_PROVIDER=anthropic
LLM_DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

### Configuration File (`config/llm_config.json`)
```json
{
  "enabled": true,
  "default_provider": "anthropic",
  "default_model": "claude-3-5-sonnet-20241022",
  "fallback_enabled": true,
  "cost_tracking_enabled": true
}
```

## 🐛 Troubleshooting

### Service Issues
```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Check service status
ome llm service status

# Check logs
tail -f logs/app.log
```

### Common Errors

| Error | Solution |
|-------|----------|
| `API Key not found` | Set `ANTHROPIC_API_KEY` in `.env` |
| `Provider unavailable` | Check API key validity |
| `Rate limit exceeded` | Wait and retry |
| `Model not found` | Use valid model name |

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
ome llm generate "test"
```

## 📊 Monitoring

### Check Usage
```bash
ome llm service metrics
```

### View Context Files
```bash
# When using --preserve-context
ls temp_*_context/
cat temp_generation_context/context_*.md
```

## 🔗 API Examples

### Generate Text
```bash
curl -X POST http://localhost:8001/v1/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain 3D printing", "max_tokens": 200}'
```

### Generate OKH
```bash
curl -X POST http://localhost:8001/v1/api/llm/generate-okh \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/example/project"}'
```

### Match Analysis
```bash
curl -X POST http://localhost:8001/v1/api/llm/match \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": ["3D printing"],
    "capabilities": ["3D printer"],
    "domain": "manufacturing"
  }'
```

## 💡 Tips

### For Developers
- Use `--preserve-context` to debug LLM interactions
- Start with simple prompts to test connectivity
- Monitor costs with `ome llm service metrics`
- Use `--quality-level high` for production use

### For Testing
- Test with synthetic data: `synth/synthetic_data/*.okh.json`
- Use `--strict-mode` for validation testing
- Check context files for detailed analysis
- Verify API connectivity before complex operations

### For Production
- Set up proper monitoring and alerting
- Configure cost limits
- Use appropriate quality levels
- Implement proper error handling

## 📚 Next Steps

1. **Read Full Documentation**: [LLM Service Documentation](llm-service.md)
2. **Explore Examples**: Check `synth/synthetic_data/` for test data
3. **Test Integration**: Try generating OKH manifests from real repositories
4. **Monitor Usage**: Use `ome llm service metrics` to track performance

## 🆘 Need Help?

- Check logs: `logs/app.log`
- Review context files when using `--preserve-context`
- Test with simple prompts first
- Verify configuration with `ome llm service status`
