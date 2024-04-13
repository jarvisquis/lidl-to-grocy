import json
import os
from pathlib import Path

import requests
import typer
from lidlplus import LidlPlusApi
from typing import Optional
from typing_extensions import Annotated


APP_DATA_DIR = Path.home() / ".lidl_to_grocy"

app = typer.Typer()


def _add_products_to_grocy(products: list, api_token: str,api_url:str) -> list | None:

    print(f"Trying to add {len(products)} products to grocy:")
    non_existing_products = []

    url_base = f"{api_url}/stock/products/by-barcode"
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


def _scan_products_in_barcode_buddy(products: list, api_token: str, api_url: str) -> None:

    print(f"Starting Scan of {len(products)} products")

    # Build url base with barcode buddy token
    url_base = f"{api_url}/action/scan?apikey={api_token}"

    # Set to purchase mode first
    headers = {
        "BBUDDY-API-KEY": api_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"state": 2}
    requests.post(
        f"{api_url}/state/setmode", headers=headers, data=payload
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
            http_code = resp.status_code
            try:
                http_result = resp.json()["result"]["result"]

                if http_code == 200:
                    result_msg = resp.json()["data"]["result"]
                else:
                    result_msg = "ERROR"
            except json.JSONDecodeError:
                http_result = "UNKNOWN"
                result_msg = "UNKNOWN"

            print(f"{name=} ({barcode=}) -> {http_result} ({result_msg})")

    # Reset state to consume
    headers = {
        "BBUDDY-API-KEY": api_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"state": 0}
    requests.post(
        f"{api_url}/state/setmode", headers=headers, data=payload
    )


def _get_most_recent_ticket(refresh_token: str) -> dict | None:
    print("Fetching most recent receipt from Lidl...", end="")
    # Authorize at Lidl
    lidl_api = LidlPlusApi("de", "DE", refresh_token=refresh_token)

    # Get all ticket ids and select id of most recent ticket
    ticket_ids = lidl_api.tickets()

    # If no ticket_ids could be retrieved return None
    if len(ticket_ids) == 0:
        print("FAILED (No receipt found)")
        return

    # Extract most recent ticket id
    most_recent_ticket_id = ticket_ids[0]["id"]
    print(f"OK (Got {most_recent_ticket_id=})")

    # Check if last run got the same or a more recent id
    # and return None if true
    print("Check id against last run...", end="")

    last_most_recent_ticket_id = _get_last_most_recent_ticket_id()
    if last_most_recent_ticket_id and (
        int(most_recent_ticket_id[9:]) <= int(last_most_recent_ticket_id[9:])
    ):
        print(f"FAILED (Id older than the one retrieved in the last run)")
        return

    # Store most recent ticket id of this run to check in the next run
    _store_most_recent_ticket_id(most_recent_ticket_id)
    print("OK")

    # Query ticket details
    print("Querying receipt details...", end="")
    most_recent_ticket = lidl_api.ticket(ticket_id=most_recent_ticket_id)
    print("OK")
    return most_recent_ticket


def _get_products(ticket: dict) -> list:
    print("Extracting products from receipt:")
    # Extract list of products first
    all_products = ticket["itemsLine"]

    # Filter product entries that represent a refund
    products_wo_refund = [
        p for p in all_products if float(p["originalAmount"].replace(",", ".")) >= 0
    ]

    print(f">> Products total: {len(all_products)}")
    print(f">> Products without refunds: {len(products_wo_refund)}")

    return products_wo_refund


def _get_last_most_recent_ticket_id() -> str | None:
    # Reference file path
    last_most_recent_ticket_id_path = APP_DATA_DIR / "last_most_recent_ticket_id.txt"

    # If file really exists read id from it and return
    if last_most_recent_ticket_id_path.exists():
        return last_most_recent_ticket_id_path.read_text()

    # otherwise try to get value from env var
    return os.environ.get("LAST_MOST_RECENT_TICKET_ID")


def _store_most_recent_ticket_id(ticket_id: str) -> None:
    # Reference file path
    last_most_recent_ticket_id_path = APP_DATA_DIR / "last_most_recent_ticket_id.txt"

    # Write ticket id into file
    last_most_recent_ticket_id_path.write_text(ticket_id)


def _init() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _clear_config_callback(value: bool) -> None:
    if value:
        _init()
        print(f"Deleting all files in {APP_DATA_DIR}...", end="")

        for f in APP_DATA_DIR.iterdir():
            f.unlink()

        print("OK. Exiting.")
        raise typer.Exit()


@app.command()
def main(
    lidl_refresh_token: Annotated[str, typer.Argument(envvar="LIDL_REFRESH_TOKEN")],
    barcode_buddy_token: Annotated[str, typer.Argument(envvar="BBUDDY_TOKEN")],
    barcode_buddy_url: Annotated[str, typer.Argument(envvar="BARCODE_BUDDY_API_URL")],
    grocy_token: Annotated[str, typer.Argument(envvar="GROCY_TOKEN")],
    grocy_url: Annotated[str, typer.Argument(envvar="GROCY_API_URL")],
    skip_grocy: Annotated[
        bool,
        typer.Option(
            "--skip-grocy", help="Set this flag to skip adding products via Grocy API."
        ),
    ] = False,
    skip_bbuddy: Annotated[
        bool,
        typer.Option(
            "--skip-bbuddy",
            help="Set this flag to skip scanning products via BBuddy API.",
        ),
    ] = False,
    clear_config: Annotated[
        Optional[bool],
        typer.Option("--clear-config", callback=_clear_config_callback, is_eager=True),
    ] = None,
    write_lidl_products_to_file: Annotated[
        bool,
        typer.Option(
            "--write-lidl-products-to-file",
            help="Set this flag to write products to products.json to skip Lidl API call in the next run. For debugging only.",
        ),
    ] = False,
) -> None:
    print(
        """
        Welcome to the great Lidl Plus Product Grocy Sync
        -------------------------------------------------
        """
    )
    _init()
    # Debug only: Check for products file and read from file if exists
    products_file = APP_DATA_DIR / "products.json"

    if products_file.exists() and not write_lidl_products_to_file:
        print(
            "Detected products.json. Reading products from file and SKIPPING Lidl API call."
        )
        products = json.loads(products_file.read_text())
    else:
        # Query lidl API for most recent ticket
        most_recent_ticket = _get_most_recent_ticket(lidl_refresh_token)
        if most_recent_ticket is None:
            print(f"No tickets available via Lidl API. Exiting.")
            raise typer.Exit(1)

        # Get purchased products
        products = _get_products(most_recent_ticket)

        # if selected store as file
        if write_lidl_products_to_file:
            products_file.write_text(json.dumps(products, indent=4))
            print(
                f"Written products to file in {products_file}. Delete for productive runs."
            )

    # ------------------------------ GROCY --------------------------------
    if skip_grocy:
        remaining_products = products
        print("Skipping Grocy API call. No products will be added to Grocy.")
    else:
        remaining_products = _add_products_to_grocy(products, api_token=grocy_token, api_url=grocy_url)

    # ------------------------------ BBUDDY -------------------------------
    if skip_bbuddy:
        print("Skipping scan to BBuddy. No products will be added via Barcode Buddy.")
    else:
        if remaining_products is None:
            print(
                "All products were added via Grocy. Scan via Barcode Buddy will be skipped"
            )
        else:
            print(
                f"{len(remaining_products)} of {len(products)} could not be added via Grocy API call."
            )
            _scan_products_in_barcode_buddy(
                remaining_products, api_token=barcode_buddy_token,api_url=barcode_buddy_url
            )

    print("Everything Done")


if __name__ == "__main__":
    app()
