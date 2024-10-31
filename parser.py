import requests
from bs4 import BeautifulSoup


def get_url(page, amount, product):
    return f"https://www.maxidom.ru/catalog/{product}/?amount={amount}&PAGEN_2={page}"


def get_response(product, page=1, amount=30):
    cookies = {
        "__Secure-ETC": "5570b4858c9d8dd11a89d43a3ae6fd59",
        "abt_data": "7.6S4CmuOZYmEVTQ2UQVeq_QbFDJR_GpJIyN0zHCTsurD48vcdaMQoAzSGImnfMB6tVJWBrC8MUIHw9ziwYMIf5dmxSH9wNwf4ii-sS2t0F8qNxjWL-aZZViBl_3lsz-23zO0mr3EfnpJmGChzXPCrQjjwmd9pHWI6abGyF3VWpjiP75D9O4lCzyv8EOGZ2dOnujdbap45uBrPwtFscRbUQAnh3KiBg36A7aUIrtGOtHBDwl5eNg908iIHF4sS7UO54AArxJaq8xhGGJb4DIRfJbbtSqHnnApZODam1au52O0miZXeF9YkDkRs2QxCGhUqs5OTXHqMeAp6E-S3_kvC9YfJGlKyL9sPzte-Gz6f-FWLHFctFtfh3L0imohvsLUSSsR8PT-biz_s_i06zirViWnLCOTXsFvsn0LjplWsf2UbeZ9dz1uNYg3tyIU",
        "__Secure-access-token": "6.0.CSAJwlOQSLiqvE2psF4zEg.75.ATycV6cNSHL3dfg4nMarrJGJw3BIMIs1vF1HeWwsOb93Pgu4W0VBL2nJaLC2LbRXYg..20241010171720.m01u1MtEj-YxiOG6qvsxCvk0Sd9rr9V-ruZGNTlPjhs.11e58cec7e2a6427",
        "xcid": "4a8f44de116c5fdfca720f677d19026a",
        "__Secure-ext_xcid": "4a8f44de116c5fdfca720f677d19026a",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    }

    response = requests.get(
        get_url(page, amount, product),
        cookies=cookies,
        headers=headers,
    )
    import time

    time.sleep(0.2)

    return response


def get_max_pages(product):
    soup = BeautifulSoup(get_response(product).content, "lxml")
    count = int(soup.find("div", class_="lvl2__content-nav-numbers-number").find_all("a")[-1].text)
    print(f"Максимум страниц: {count}")
    return count


def parser_maxidom(product, page_count):
    products = []
    page_count = min(get_max_pages(product), page_count)

    for page_number in range(1, page_count + 1):
        soup = BeautifulSoup(get_response(product, page_number).content, "lxml")

        product_cards = soup.find_all("article", class_="l-product")
        for product in product_cards:
            id = product.find("div", class_="lvl1__product-body-info-code").find("span").text
            price = product.find("div", class_="l-product__price").find("div", class_="l-product__price-base").text.strip()
            name = product.find("div", class_="l-product__name").find("a").find("span").text
            products.append((id, name, price))
        print(f"Готова страница {page_number}/{page_count}")

    return products
