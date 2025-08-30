# irgen

a script to convert specified spreadsheet to IP-XACT

# Dependency

[python](https://www.python.org/) >= 3.10

[uv](https://docs.astral.sh/uv/) (Optional but Recommend)

# Build

- use uv

    ```Shell
    # take 3.12 for an example
    uv venv --python 3.12
    
    # linux/unix
    source .venv/bin/activate
    # windows
    .venv\scripts\activate
    
    uv sync
    
    # Now you can use irgen
    irgen --help
    ```

- use python

  ```shell
  # sometimes python3 instead of python
  python -m venv .venv
  
  # linux/unix
  source .venv/bin/activate
  # windows
  .venv\scripts\activate
  
  pip install -e .
  
  # Now you can use irgen
  irgen --help
  ```
  

## Usage

```shell
irgen -i example.xlsx
```


