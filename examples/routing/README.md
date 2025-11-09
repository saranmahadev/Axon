# Routing Examples

Examples demonstrating Axon's intelligent tier routing system.

## Examples

- `router_basic_usage.py` - Basic router operations
- `router_multi_tier.py` - Multi-tier routing demonstration
- `router_promotion_demo.py` - Automatic promotion/demotion
- `router_scoring_config.py` - Scoring engine configuration

## Concepts Covered

- Tier selection based on importance scores
- Automatic promotion from ephemeral → session → persistent
- Automatic demotion for low-scoring memories
- Custom scoring configurations

## Quick Start

```bash
python examples/routing/router_multi_tier.py
```
