# Synthetic Data Generator for OKH and OKW Models

This script generates realistic synthetic data for testing the matching engine. It can create both OKH manifests and OKW facilities with configurable complexity levels.

## Features

- **Dual Model Support**: Generate both OKH (OpenKnowHow) manifests and OKW (OpenKnowWhere) facilities
- **Complexity Levels**: Choose between minimal, complex, or mixed complexity
- **Realistic Data**: Uses Faker library to generate realistic names, addresses, and other data
- **Validation**: Optional validation to ensure generated records pass model constraints
- **Individual Files**: Each record is saved as a separate JSON file
- **Command-line Interface**: Easy-to-use CLI with configurable parameters

## Installation

The script requires the `faker` library. Install it using:

```bash
conda install -c conda-forge faker
```

Or with pip:

```bash
pip install faker
```

## Usage

### Basic Usage

```bash
# Generate 10 OKH manifests with mixed complexity
python generate_synthetic_data.py --type okh --count 10 --complexity mixed

# Generate 5 OKW facilities with complex data
python generate_synthetic_data.py --type okw --count 5 --complexity complex

# Generate minimal OKH manifests with validation
python generate_synthetic_data.py --type okh --count 3 --complexity minimal --validate
```

### Command-line Options

- `--type {okh,okw}`: Type of data to generate (required)
- `--count COUNT`: Number of records to generate (default: 10)
- `--complexity {minimal,complex,mixed}`: Complexity level (default: mixed)
- `--output-dir OUTPUT_DIR`: Output directory for generated files (default: ./synthetic_data)
- `--validate`: Validate generated records against model constraints

### Complexity Levels

- **minimal**: Only required fields are populated
- **complex**: All optional fields are populated with realistic data
- **mixed**: Random selection of optional fields (realistic variation)

## Generated Data Examples

### OKH Manifests

The generator creates realistic hardware projects such as:
- Arduino-based IoT sensor nodes
- CNC machined aluminum brackets
- Laser cut acrylic display cases
- 3D printed prosthetic hands
- Sheet metal enclosures

Each manifest includes:
- Complete licensing information
- Realistic contributor and organization data
- Manufacturing specifications with process requirements
- Material specifications
- Part specifications with TSDC codes
- Documentation references

### OKW Facilities

The generator creates realistic manufacturing facilities such as:
- Community makerspaces
- Professional machine shops
- Rapid prototyping labs
- Industrial manufacturing plants
- Electronics assembly houses

Each facility includes:
- Complete location and contact information
- Detailed equipment specifications
- Manufacturing process capabilities
- Material handling capabilities
- Certifications and quality standards
- Human capacity and innovation space details

## Output Format

Each generated record is saved as a separate JSON file with the naming convention:
- OKH: `okh_manifest_XXX.json`
- OKW: `okw_manifest_XXX.json`

Where XXX is a zero-padded sequence number.

## Realistic Relationships

The generator creates realistic relationships between:
- Manufacturing processes and required equipment
- Materials and compatible manufacturing methods
- TSDC codes and appropriate manufacturing parameters
- Equipment specifications and material capabilities

However, it intentionally does NOT create perfectly complementary datasets to ensure the matching engine can properly handle failed matches and situations where no valid matches exist.

## Validation

When using the `--validate` flag, the script will:
- Check that all required fields are present
- Validate license information
- Verify document references use valid URLs
- Ensure generated records pass the model's validation methods

Records that fail validation will be skipped with a warning message.

## Examples

```bash
# Generate a small test dataset
python generate_synthetic_data.py --type okh --count 5 --complexity mixed --output-dir ./test_data

# Generate a large dataset for performance testing
python generate_synthetic_data.py --type okw --count 100 --complexity complex --output-dir ./performance_test

# Generate both types for integration testing
python generate_synthetic_data.py --type okh --count 20 --complexity mixed --output-dir ./integration_test
python generate_synthetic_data.py --type okw --count 20 --complexity mixed --output-dir ./integration_test
```

## Dependencies

- Python 3.7+
- faker>=19.0.0
- The OKH and OKW model classes from the project

## Notes

- The script is designed to be standalone and doesn't require the full project environment
- Generated data uses realistic but fictional information
- All URLs and file paths are synthetic and don't point to real resources
- The script respects the incremental development principles by making small, focused changes
