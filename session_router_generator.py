#!/usr/bin/env python3
"""
Session Router Generator

Generates session-specific router configurations from a reference router,
applying model catalog filtering and availability checks.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class SessionRouterGenerator:
    """Generates session routers from reference configuration."""
    
    def __init__(self, reference_path: str, catalog_path: str = None):
        """
        Initialize generator.
        
        Args:
            reference_path: Path to reference-router.json
            catalog_path: Optional path to model-catalog.json
        """
        self.reference_path = Path(reference_path)
        self.catalog_path = Path(catalog_path) if catalog_path else None
        
        with open(self.reference_path) as f:
            self.reference = json.load(f)
            
        self.catalog = None
        if self.catalog_path and self.catalog_path.exists():
            with open(self.catalog_path) as f:
                self.catalog = json.load(f)
    
    def generate(self, output_path: str, session_id: str = None) -> Dict[str, Any]:
        """
        Generate session router configuration.
        
        Args:
            output_path: Where to write session-router.json
            session_id: Optional session identifier
            
        Returns:
            Generated configuration dictionary
        """
        session_config = {
            "version": self.reference["version"],
            "cooldownSeconds": self.reference.get("cooldownSeconds", 60),
            "provider": self.reference["provider"],
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "generatedFrom": str(self.reference_path),
            "sessionId": session_id or f"session-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "defaultQuotaGroup": self.reference["defaultQuotaGroup"],
            "maxFallbackAttempts": self.reference["maxFallbackAttempts"],
            "quotaGroups": self.reference["quotaGroups"],
            "roles": {}
        }
        
        # Filter each role's models through catalog availability
        for role_name, role_config in self.reference["roles"].items():
            available_models = self._filter_available_models(role_config["models"])
            
            if not available_models:
                print(f"Warning: Role '{role_name}' has no available models", file=sys.stderr)
                continue
                
            session_config["roles"][role_name] = {
                "description": role_config["description"],
                "models": available_models,
                "quotaGroup": role_config["quotaGroup"]
            }
            
            # Copy optional role-level maxFallbackAttempts
            if "maxFallbackAttempts" in role_config:
                session_config["roles"][role_name]["maxFallbackAttempts"] = role_config["maxFallbackAttempts"]
        
        # Write to output
        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(session_config, f, indent=2)
            
        return session_config
    
    def _filter_available_models(self, models: List[str]) -> List[str]:
        """
        Filter models through catalog availability.
        
        Args:
            models: List of model identifiers
            
        Returns:
            Filtered list of available models
        """
        if not self.catalog:
            # No catalog = all models pass (trust reference)
            return models
            
        available = []
        for model_id in models:
            # Check catalog for availability
            if model_id in self.catalog.get("models", {}):
                model_info = self.catalog["models"][model_id]
                if model_info.get("available", True):
                    available.append(model_id)
                else:
                    print(f"Filtered out unavailable model: {model_id}", file=sys.stderr)
            else:
                # Not in catalog = assume available (backward compat)
                available.append(model_id)
                
        return available


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate session router from reference configuration"
    )
    parser.add_argument(
        "--reference",
        default="reference-router.json",
        help="Path to reference router configuration"
    )
    parser.add_argument(
        "--catalog",
        help="Optional path to model catalog"
    )
    parser.add_argument(
        "--output",
        default="session-router.json",
        help="Output path for generated session router"
    )
    parser.add_argument(
        "--session-id",
        help="Optional session identifier"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print configuration to stdout instead of writing file"
    )
    
    args = parser.parse_args()
    
    generator = SessionRouterGenerator(args.reference, args.catalog)
    session_config = generator.generate(
        args.output if not args.dry_run else "/dev/null",
        args.session_id
    )
    
    if args.dry_run:
        print(json.dumps(session_config, indent=2))
    else:
        print(f"Generated session router: {args.output}")
        print(f"  Roles: {len(session_config['roles'])}")
        print(f"  Session ID: {session_config['sessionId']}")


if __name__ == "__main__":
    main()
