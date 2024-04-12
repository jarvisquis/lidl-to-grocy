# Lidl To Grocy
This is a very basic and very beta python script that allows the following:
1. Query Lidl API using the wonderful library [lidl-plus](https://github.com/Andre0512/lidl-plus) by Andre0512
2. Extract products from receipt that do not represent a refund (e.g. Sodastream refund)
3. Add products based on barcode to [Grocy](https://grocy.info/) 
4. If barcode cannot be found in Grocy redirect remaining products to scan action of [BarcodeBuddy](https://github.com/Forceu/barcodebuddy)

## How to use
Since everything is stored in [__main__.py](src/lidl_to_grocy/__main__.py) make sure to adapt urls pointing to Grocy and BarcodeBuddy:
```{python}
# SET YOUR API URLs HERE!
BARCODE_BUDDY_API_URL = "https://<YOUR_HOST_NAME>/api"
GROCY_API_URL = "https://<YOUR_HOST_NAME>/api"
```

Further, have the following tokens at hand:
1. BarcodeBuddy API Token (see [Docs](https://barcodebuddy-documentation.readthedocs.io/en/latest/advanced.html#interacting-with-the-api))
2. Grocy API Token (see [Docs](https://demo.grocy.info/api) or your Grocy instance under /api endpoint)
3. Lidl Plus Token (see [Readme from Andre](https://github.com/Andre0512/lidl-plus#authentication))

Setup up environment by using [PDM](https://pdm-project.org/latest/):
```bash
pdm sync
```

Finally, call script:
```{bash}
pdm run python -m src.lidl_to_grocy <LIDL_TOKEN> <BBUDDY_TOKEN> <GROCY_TOKEN>
```

## Remarks
This is a two hour script. Therefore, expect bugs and strange behaviour ;)
