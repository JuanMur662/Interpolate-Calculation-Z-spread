# Fair Z-spread Calculator

A pricing tool for new corporate bond issues, built around three real-world scenarios faced by credit research analysts and portfolio managers.

## What it does

| Method | When to use | What it does |
|---|---|---|
| **Interpolate** | Target tenor sits *between* the issuer's existing bonds | Linear interpolation on Z-spreads |
| **Extrapolate** | Target tenor is *outside* the issuer's range | Anchor at issuer's nearest bond + sector slope + liquidity premium |
| **Proxy (new issuer)** | Issuer has no bonds at all | Median of peers + issuer-specific adjustments + optional full curve build |

Every scenario produces a fair Z-spread number, a calculation breakdown, a visualization, and an Excel export.

---

## Run locally (5 minutes)

**1. Install Python 3.9+** if you don't have it: https://www.python.org/downloads/

**2. Open a terminal in this folder and run:**

```bash
pip install -r requirements.txt
streamlit run fair_spread_calculator.py
```

**3. Your browser will open at** `http://localhost:8501` — that's the app.

---

## Deploy a free public link (10 minutes)

You can share a URL with colleagues without paying anything via Streamlit Community Cloud.

**1. Push these 3 files to a public GitHub repo:**
- `fair_spread_calculator.py`
- `requirements.txt`
- `README.md`

**2. Go to** https://share.streamlit.io and sign in with GitHub.

**3. Click "New app"** → select your repo → main file = `fair_spread_calculator.py` → Deploy.

**4. You get a URL like** `https://your-app-name.streamlit.app` — share it freely.

---

## Methodology — the credit research mental model

The whole tool is built around one principle:

> **Spreads have a LEVEL (who you are) and a SHAPE (where you sit on the curve). When data is missing, borrow shape from the sector — never invent it.**

| Method | LEVEL anchor | SHAPE source |
|---|---|---|
| Interpolate | Issuer's own bonds | Issuer's own bonds |
| Extrapolate | Issuer's nearest bond | Sector / peer curve |
| Proxy | Peer median + adjustments | Sector curve (if building full curve) |

### Sanity-check every output

1. Does it fit the **sovereign + sector + rating** triangle?
2. Would a trader laugh? (5Y > 10Y on an upward-sloping market = something broke)
3. Is **new-issue concession** baked in? (Primary deals price 10–25 bps wide of secondary fair value.)

---

## Tips

- Use the **"Include in median"** checkbox in the proxy tab to exclude outlier peers (e.g., distressed credits, sovereign-linked names that distort the comparable set).
- The **liquidity premium** in extrapolate mode is automatically zeroed if the target sits inside the issuer's range — the tool warns you to switch tabs.
- Build the **full implied curve** in proxy mode to anchor secondary trading levels for the new issuer once it prints.
- Every tab has a **download button** — exports the full scenario to Excel so you can attach it to a credit memo or pricing committee deck.

---

## License

MIT. Use it, modify it, fork it.
