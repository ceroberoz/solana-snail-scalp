# Installation Guide

## Requirements

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- (Optional) Git for cloning

## Step-by-Step Installation

### 1. Install uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone Repository

```bash
git clone https://github.com/ceroberoz/solana-snail-scalp.git
cd solana-snail-scalp
```

### 3. Install Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all dependencies.

### 4. Verify Installation

```bash
uv run python -m snail_scalp --help
```

You should see the help output with all available commands.

### 5. Run First Simulation

```bash
# Generate sample data
uv run python -m snail_scalp.generate_data

# Run simulation
uv run python -m snail_scalp --simulate --capital 20
```

## Troubleshooting Installation

### Issue: `uv: command not found`

**Solution:** Add uv to your PATH

```bash
# macOS/Linux
export PATH="$HOME/.cargo/bin:$PATH"

# Windows (PowerShell)
$env:PATH += ";$HOME\.cargo\bin"
```

### Issue: `Module not found`

**Solution:** Reinstall dependencies

```bash
uv sync --reinstall
```

### Issue: Python version too old

**Solution:** Install Python 3.12+

```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12

# Windows
# Download from python.org
```

## Development Setup

For development, install dev dependencies:

```bash
uv sync --dev
```

Run linting and type checking:

```bash
uv run ruff check src/snail_scalp
uv run mypy src/snail_scalp
```

## Next Steps

After installation:
1. Read the [CLI Reference](CLI_REFERENCE.md)
2. Learn the [Strategy](STRATEGY.md)
3. Try [Real Data Simulation](REAL_DATA.md)
