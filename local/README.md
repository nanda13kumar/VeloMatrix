# Local workspace (optional)

VeloMatrix reads **policy** and **connector bindings** from:

- `demo-data/catalog.json`
- `demo-data/bindings.json`

…inside the directory resolved by `VOLOMATRIX_DATA_BASE`, or by default:

`<repo-root>/local/demo-data/`

The `demo-data/` folder is **gitignored** so you can keep tenant-specific scores and queries out of git.

Generate starter files:

```bash
python3 scripts/seed_local_demo.py
```

Point the API at a custom directory:

```bash
export VOLOMATRIX_DATA_BASE=/path/to/your/workspace
```
