import contextvars

from langchain_core.tools import tool
from datetime import datetime
from langchain_community.tools import DuckDuckGoSearchRun
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as SearchTimeout
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from ddgs import DDGS


def _ddg_search(query: str) -> str:
    lines = []
    with DDGS() as d:
        try:
            news = d.news(query, region="in-en", timelimit="w", max_results=5)
        except Exception:
            news = []
        for r in news or []:
            lines.append(
                f"- {r.get('title', '')} | {r.get('source', '')} | {str(r.get('date', ''))[:10]}\n  {r.get('body', '')}"
            )
        if not lines:   # news mein kuch nahi mila to normal web search
            for r in d.text(query, region="in-en", max_results=4) or []:
                lines.append(f"- {r.get('title', '')}\n  {r.get('body', '')}")
    return "\n".join(lines) if lines else "No results found."


_search_pool = ThreadPoolExecutor(max_workers=2)

SEARCH_FALLBACK = (
    "Web search is unavailable right now. Answer from your own knowledge "
    "and mention that live results could not be fetched."
)



@tool
def web_search(query: str) -> str:
    """
    Search the web for recent or fast-changing information, such as news,
    current events or live facts. Do NOT use it for general knowledge,
    definitions or explanations that you can answer yourself.
    """
    future = _search_pool.submit(_ddg_search, query)
    try:
        return future.result(timeout=10)
    except Exception as e:
        print(">>> web_search problem:", type(e).__name__, str(e)[:200])
        return SEARCH_FALLBACK




@tool
def get_current_time() -> str:
    """
    This function returns the current date and time in a human-readable format.
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_weather_data(city: str) -> str:
    """
    This function fetches the current weather data for a given city
    """
    url = f'https://api.weatherstack.com/current?access_key=c4d65aaf369bea435be736d6585b0f3d&query={city}'
    response = requests.get(url)
    return response.json()



@tool
def get_stock_price(symbol: str) -> dict:
    """Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()