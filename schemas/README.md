# Configuration Schemas

This directory contains JSON Schema definitions for router configuration files.

## Files

- **reference-router.schema.json**: Schema for reference router configuration
  - Validates structure, types, and required fields
  - Documents all configuration options
  - Used by IDEs for autocomplete and validation

## Usage

Add `$schema` field to your configuration file:

```json
{
  "$schema": "./schemas/reference-router.schema.json",
  "version": 2,
  ...
}
```

## Validation

Validate a configuration file against the schema:

```bash
# Using jsonschema CLI (Python)
pip install jsonschema
jsonschema -i reference-router.json schemas/reference-router.schema.json

# Using ajv CLI (Node.js)
npm install -g ajv-cli
ajv validate -s schemas/reference-router.schema.json -d reference-router.json
```

## Schema Version

Current schema version: **Draft-07**

Compatible with most JSON Schema validators and IDE plugins.
