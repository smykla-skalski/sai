# IDE Detection

## Auto-detection (default behavior)

If `--no-ide` → skip IDE detection, `I=""`.
If `--ide <name>` → use that IDE directly.
Otherwise → auto-detect using confidence tiers.

## Tier 1 — High Confidence

One match = use that IDE:

| Config File                    | IDE       |
|:-------------------------------|:----------|
| `go.mod`                       | goland    |
| `Cargo.toml`                   | rustrover |
| `pyproject.toml` OR `setup.py` | pycharm   |
| `pom.xml` OR `build.gradle*`   | idea      |
| `Gemfile`                      | rubymine  |
| `composer.json`                | phpstorm  |
| `CMakeLists.txt`               | clion     |

## Tier 2 — Medium Confidence

Only if NO Tier 1 match:

| Config File                | IDE      |
|:---------------------------|:---------|
| `tsconfig.json`            | webstorm |
| `package.json` (alone)     | webstorm |
| `requirements.txt` (alone) | pycharm  |

## Detection Rules

- Exactly ONE Tier 1 match → use that IDE
- MULTIPLE Tier 1 matches → ask user (full mode) or skip (quick mode)
- ZERO Tier 1 + Tier 2 match → use Tier 2 IDE
- No config files found → ask user (full mode) or skip (quick mode)

**Key Rule:** Tier 1 always wins. A Python project with `pyproject.toml` + `package.json` → `pycharm` (not webstorm).

## IDE Options

goland, pycharm, webstorm, idea, rubymine, phpstorm, clion, rustrover
