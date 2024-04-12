import requests
import typer
from lidlplus import LidlPlusApi
import json
from pathlib import Path

# SET YOUR API URLs HERE!
BARCODE_BUDDY_API_URL = "https://barcodebuddy.mocca.casa/api"
GROCY_API_URL = "https://grocy.mocca.casa/api"


def _add_products_to_grocy(products: list, api_token: str) -> list | None:

    print(f"Trying to add {len(products)} products to grocy:")
    non_existing_products = []

    url_base = f"{GROCY_API_URL}/stock/products/by-barcode"
    for product in products:
        # Extract barcode and product name
        barcode = product.get("codeInput", "-1")
        name = product.get("name", "UNKNOWN")
        price = float(product.get("currentUnitPrice", "0").replace(",", "."))
        quantity = float(product.get("quantity", "0").replace(",", "."))

        # Build final url with barcode parameter
        url = f"{url_base}/{barcode}/add"

        # Provide headers and payload
        headers = {"GROCY-API-KEY": api_token, "Content-Type": "application/json"}
        payload = {"amount": quantity, "transaction_type": "purchase", "price": price}

        # Do request
        resp = requests.post(url, headers=headers, json=payload)

        # If response has http status code other than 200...
        if resp.status_code != 200:
            # ... store product in non existing products list and get error message
            non_existing_products.append(product)
            result_msg = resp.json().get("error_message", "ERROR")
        else:
            # ... otherwise everything ok
            result_msg = "OK"

        # Print status of upload
        print(f"{name=} ({barcode=}) -> {resp.status_code}: {result_msg}")

    # Return the list of non existing products only if item count gt 0
    if len(non_existing_products) > 0:
        print(f"Could not add {len(non_existing_products)} products")
        return non_existing_products


def _scan_products_in_barcode_buddy(products: list, api_token: str) -> None:

    print(f"Starting Scan of {len(products)} products")

    # Build url base with barcode buddy token
    url_base = f"{BARCODE_BUDDY_API_URL}/action/scan?apikey={api_token}"

    # Set to purchase mode first
    headers = {
        "BBUDDY-API-KEY": api_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"state": 2}
    requests.post(
        f"{BARCODE_BUDDY_API_URL}/state/setmode", headers=headers, data=payload
    )

    # Iterate over products...
    for product in products:

        # Extract barcode and product name
        barcode = product.get("codeInput", "-1")
        name = product.get("name", "UNKNOWN")
        price = float(product.get("currentUnitPrice", "0").replace(",", "."))

        # For products that having a quantity in g, kg or any other weight
        # we only scan once
        is_weight = product.get("isWeight")
        quantity = 1 if is_weight else int(product.get("quantity", "0"))

        # Scan for each quantity...
        for q in range(quantity):
            # Send barcode to barcodebuddy
            payload = {"barcode": barcode, "price": price}
            headers = {
                "BBUDDY-API-KEY": api_token,
            }
            resp = requests.post(url_base, headers=headers, data=payload)

            # Handle barcodebuddy response
            http_code = resp.json()["result"]["http_code"]
            http_result = resp.json()["result"]["result"]

            if http_code == 200:
                result_msg = resp.json()["data"]["result"]
            else:
                result_msg = "ERROR"

            print(f"{name=} ({barcode=}) -> {http_result} ({result_msg})")

    # Reset state to consume
    headers = {
        "BBUDDY-API-KEY": api_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"state": 0}
    requests.post(
        f"{BARCODE_BUDDY_API_URL}/state/setmode", headers=headers, data=payload
    )


def _get_most_recent_ticket(refresh_token: str) -> dict:
    print("Fetching most recent receipt from Lidl...", end="")
    # Authorize at Lidl
    lidl_api = LidlPlusApi("de", "DE", refresh_token=refresh_token)

    # Get all ticket ids and select id of most recent ticket
    ticket_ids = lidl_api.tickets()
    most_recent_ticket_id = ticket_ids[0]["id"]

    # Query details of most recent ticket id and return
    most_recent_ticket = lidl_api.ticket(ticket_id=most_recent_ticket_id)
    print("OK")
    return most_recent_ticket


def _get_products(ticket: dict) -> list:
    print("Extracting products from receipt...")
    # Extract list of products first
    all_products = ticket["itemsLine"]

    # Filter product entries that represent a refund
    products_wo_refund = [
        p for p in all_products if float(p["originalAmount"].replace(",", ".")) >= 0
    ]

    print(f"Products total: {len(all_products)}")
    print(f"Products without refunds: {len(products_wo_refund)}")

    return products_wo_refund


def main(
    lidl_refresh_token: str,
    barcode_buddy_token: str,
    grocy_token: str,
    skip_lidl: bool = False,
    skip_grocy: bool = False,
    skip_bbuddy: bool = False,
) -> None:
    print("Welcome to the great Lidl Plus Product Grocy Sync")
    print("-------------------------------------------------")
    print()

    p_path = Path("products.json")

    if not skip_lidl:
        ticket = _get_most_recent_ticket(lidl_refresh_token)
        products = _get_products(ticket)

        with p_path.open("w") as p_file:
            json.dump(products, p_file, indent=4)
    else:
        print("Query Lidl skipped!")
        if not p_path.exists():
            print("No products.json available. Exiting now.")
            exit(1)
        with p_path.open() as p_file:
            products = json.load(p_file)

    if not skip_grocy:
        failed_products = _add_products_to_grocy(products, api_token=grocy_token)
    else:
        failed_products = products
        print("Add to Grocy skipped!")

    if not skip_bbuddy:
        if failed_products is not None:
            print("WARNING: Some products could not be added to grocy directly.")
            _scan_products_in_barcode_buddy(
                failed_products, api_token=barcode_buddy_token
            )
    else:
        print("Scan to BBuddy skipped!")

    print("Everything Done")


if __name__ == "__main__":
    typer.run(main)
