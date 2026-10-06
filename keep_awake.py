"""
Keeps two Streamlit dementia-model apps awake by running a simulation on each,
then confirms the simulation embedded on the USC Schaeffer page works.

Exits with an error if any check fails, so GitHub emails you about the failed run.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

APPS = [
    ("My Streamlit app", "https://qsz3abkm5sumre3dtdoupy.streamlit.app/"),
    ("Schaeffer's Streamlit app", "https://dementiacost.streamlit.app/"),
]
SCHAEFFER_PAGE = (
    "https://schaeffer.usc.edu/cost-of-dementia-model/"
    "forecasting-dementias-impact-on-the-united-states/"
)

# Any of these appearing after "Run Simulation" means the simulation produced output.
CHART = (
    '[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], '
    '[data-testid="stArrowVegaLiteChart"], [data-testid="stPyplot"], '
    ".js-plotly-plot, .vega-embed"
)
RUN_BUTTON = "button:has-text('Run Simulation')"
LOAD_TIMEOUT = 5 * 60 * 1000   # a cold Streamlit app can take a few minutes to start
RESULT_TIMEOUT = 3 * 60 * 1000

SHOTS = Path("screenshots")
SHOTS.mkdir(exist_ok=True)


def run_simulation(scope, label):
    """Click Run Simulation inside `scope` (a page or frame) and wait for a chart."""
    scope.locator(RUN_BUTTON).first.wait_for(state="visible", timeout=LOAD_TIMEOUT)
    scope.locator(RUN_BUTTON).first.click()
    scope.locator(CHART).first.wait_for(state="visible", timeout=RESULT_TIMEOUT)
    print(f"  {label}: simulation ran, chart displayed")


def check_app(browser, name, url):
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    try:
        # Visit the public URL first: this is what triggers Streamlit to start the app.
        page.goto(url, timeout=LOAD_TIMEOUT)
        # Then open the app content directly (the public URL wraps it in an iframe).
        page.goto(url.rstrip("/") + "/~/+/", timeout=LOAD_TIMEOUT)
        run_simulation(page, name)
        return True
    except Exception as e:
        print(f"  {name}: FAILED - {e}")
        return False
    finally:
        page.screenshot(path=str(SHOTS / f"{name.replace(' ', '_')}.png"), full_page=True)
        page.close()


def check_schaeffer(browser):
    name = "Schaeffer page embed"
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    try:
        page.goto(SCHAEFFER_PAGE, timeout=LOAD_TIMEOUT)
        iframe = page.locator("iframe[src*='streamlit.app']").first
        iframe.wait_for(state="attached", timeout=60_000)
        iframe.scroll_into_view_if_needed()
        frame = page.frame_locator("iframe[src*='streamlit.app']").first
        run_simulation(frame, name)
        return True
    except Exception as e:
        print(f"  {name}: FAILED - {e}")
        return False
    finally:
        page.screenshot(path=str(SHOTS / "Schaeffer_page.png"), full_page=True)
        page.close()


def main():
    print(f"Check started {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, url in APPS:
            results.append(check_app(browser, name, url))
        results.append(check_schaeffer(browser))
        browser.close()

    if all(results):
        print("All checks passed.")
    else:
        print(f"{results.count(False)} check(s) failed. See screenshots in the run's artifacts.")
        sys.exit(1)


if __name__ == "__main__":
    main()
