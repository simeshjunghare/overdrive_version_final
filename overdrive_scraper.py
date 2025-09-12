import re
import asyncio
import sys
from difflib import SequenceMatcher
from playwright.async_api import async_playwright

# ----------------------------------------------------------------------
# Windows fix: Python 3.12 default event loop doesn't support subprocesses
# Playwright needs this to spawn browsers
# ----------------------------------------------------------------------
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def name_similarity(name1, name2):
    """Calculate similarity ratio between two names (0 to 1)."""
    clean = lambda s: re.sub(r'\W+', '', s.lower())
    name1_clean = clean(name1)
    name2_clean = clean(name2)

    if name1_clean == name2_clean:
        return 1.0
    if name1_clean in name2_clean or name2_clean in name1_clean:
        return 0.9

    return SequenceMatcher(None, name1_clean, name2_clean).ratio()


async def extract_publishers_async(company_name, min_similarity=0.7):
    """Async function: Search Overdrive and extract publishers."""
    base_url = "https://www.overdrive.com/search"
    search_url = f"{base_url}?q={company_name}"

    all_publishers = []
    matching_publishers = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # ✅ Use domcontentloaded so it doesn’t wait forever on “load”
        await page.goto(search_url, timeout=200000, wait_until="domcontentloaded")

        try:
            # ✅ Explicit wait for publisher section
            await page.wait_for_selector("//*[@id='Publisher content']//li", timeout=60000)

            li_tags = page.locator("//*[@id='Publisher content']//li")
            count = await li_tags.count()

            for i in range(count):
                a_tag = li_tags.nth(i).locator("a")
                publisher_name = await a_tag.get_attribute("aria-label") or await a_tag.inner_text()
                if publisher_name:
                    publisher_name = publisher_name.replace("Filter by", "").strip()
                publisher_url = await a_tag.get_attribute("href")

                all_publishers.append({
                    "publisher_name": publisher_name,
                    "publisher_url": publisher_url
                })

                similarity = name_similarity(company_name, publisher_name)
                if similarity >= min_similarity:
                    matching_publishers.append({
                        "publisher_name": publisher_name,
                        "publisher_url": publisher_url,
                        "similarity_score": round(similarity, 2)
                    })
                    if similarity == 1.0:  # perfect match
                        break

        except Exception as e:
            print(f"Error extracting publishers: {e}")

        await browser.close()

    matching_publishers.sort(key=lambda x: x['similarity_score'], reverse=True)

    return {
        "all_publishers": all_publishers,
        "matching_publishers": matching_publishers
    }


def extract_publishers(company_name, min_similarity=0.7):
    """Sync wrapper so Streamlit can call this easily."""
    return asyncio.run(extract_publishers_async(company_name, min_similarity))


if __name__ == "__main__":
    # Manual test
    company = input("Enter company name to search: ").strip()
    results = extract_publishers(company)
    print(results)
