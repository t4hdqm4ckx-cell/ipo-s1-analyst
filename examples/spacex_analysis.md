# Example: Analyzing SpaceX's S-1

This example shows how to run the agent against SpaceX's S-1 filing once it has been
filed with the SEC (SpaceX filed in 2026).

## Command

```bash
# Set your key first
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Run the analysis
s1-analyst --company "Space Exploration Technologies" --verbose
```

Or if SpaceX is listed under a ticker:

```bash
s1-analyst --ticker SPCE --verbose
```

## What the agent investigates for SpaceX

Given SpaceX's unique profile (defense + commercial + government contracts),
the agent will specifically focus on:

1. **Launch manifest / backlog** — contracted revenue, Starship cadence
2. **Starlink revenue** — subscriber count, ARPU, growth trajectory
3. **Government contract concentration** — NASA, DoD dependency
4. **Export control / ITAR** — mandatory disclosure for launch vehicles
5. **Elon Musk key-man risk** — standard in S-1 risk factors
6. **Valuation vs. private rounds** — last private round at ~$350B (Jan 2025)
7. **SpaceX vs. ULA / Rocket Lab / Blue Origin** — competitive landscape
8. **Use of proceeds** — IPO for Starlink spinout vs. full company

## Expected report location

```
reports/Space_Exploration_Technologies_Corp_2026-XX-XX.md
```

## Notes on SpaceX-specific considerations

- SpaceX's S-1 will be unusual: dual revenue streams (launch + Starlink)
- Likely dual-class shares (Musk control)
- Heavy government dependency (ITAR/EAR will be flagged by risk scorer)
- The agent's risk scorer will detect: export controls, government contracts,
  key-man dependency, potentially dual-class structure
- Expect automated risk score of HIGH (40-60 range) due to regulatory exposure
  — this is normal for defense-adjacent tech, not a negative signal per se

## Adjust MAX_TOKENS for large filings

SpaceX's S-1 may be 500+ pages. For better analysis quality:

```bash
# In .env
MAX_TOKENS=16384
MAX_AGENT_ITERATIONS=30
```
