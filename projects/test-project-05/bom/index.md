# Bill of Materials (BOM)
[← Back to Documentation](../docs/index.md)
This directory contains the complete Bill of Materials for the project,
organized for maximum compatibility with the Open Matching Engine.

## File Formats

### CSV Format (`bom.csv`)
- Structured tabular data for programmatic processing
- Columns: item, quantity, unit, notes
- Compatible with spreadsheet applications
- Machine-readable for automation

### Markdown Format (`bom.md`)
- Human-readable list format
- Includes descriptions and context
- Easy to read and edit manually
- Good for documentation and review

## Integration

The generation services can:
- Ingest BOM content from this directory
- Produce BOM content compatible with this structure
- Validate BOM completeness and accuracy
- Generate manufacturing requirements

## Best Practices

- Keep both formats synchronized
- Include part numbers and specifications
- Document alternatives and substitutions
- Update when design changes
