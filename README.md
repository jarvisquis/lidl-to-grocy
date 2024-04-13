# Lidl To Grocy
This is a very basic and very beta python script that allows the following:
1. Query Lidl API using the wonderful library [lidl-plus](https://github.com/Andre0512/lidl-plus) by Andre0512
2. Extract products from receipt that do not represent a refund (e.g. Sodastream refund)
3. Add products based on barcode to [Grocy](https://grocy.info/) 
4. If barcode cannot be found in Grocy redirect remaining products to scan action of [BarcodeBuddy](https://github.com/Forceu/barcodebuddy)

## How to use
Have the following Tokens at hand:
1. BarcodeBuddy API Token (see [Docs](https://barcodebuddy-documentation.readthedocs.io/en/latest/advanced.html#interacting-with-the-api))
2. Grocy API Token (see [Docs](https://demo.grocy.info/api) or your Grocy instance under /api endpoint)
3. Lidl Plus Token (see [Readme from Andre](https://github.com/Andre0512/lidl-plus#authentication))

Although you can provide the tokens and urls as CLI arguments the most easiest solution is to create and source a .env file with the following content:
```{sh}
export LIDL_REFRESH_TOKEN=<YOUR_LIDL_REFRESH_TOKEN>
export BBUDDY_TOKEN=<YOUR_BBUDDY_API_TOKEN>
export GROCY_TOKEN=<YOUR_GROCY_API_TOKEN>
export BARCODE_BUDDY_API_URL=<YOUR_BARCODE_BUDDY_API_URL>
export GROCY_API_URL=<YOUR_GROCY_API_URL>
```


Setup up environment by using [PDM](https://pdm-project.org/latest/):
```bash
pdm install
```


Finally, call script:
```{bash}
pdm run lidl-to-grocy
```

## Remarks
The CLI app itself writes at max two files to your home directory in a .dot file directory .lidl-to-grocy:
- last_most_recent_ticket_id.txt -> stores the most recent ticket id to make sure it will be processed only once.
- products.json -> Only written when --write-lidl-products-to-file provided. Normally you wouldn't do that.

To completly get rid of the above mentioned files just run:
```{bash}
pdm run lidl-to-grocy --clear-config
```
