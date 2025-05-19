## Dependencies

### Step 1:

```bash
brew install unixodbc
```

### Step 2:

```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release && brew update && brew install msodbcsql17 mssql-tools
```

### Step 3:

- Create a python environment

### Step 4:

```bash
pip install -r requirements.txt
```

### Step 5:

- Open the docker folder and drop the .bak database file into drop-database-here
- EXECUTE THE COMMANDS BELOW:

```bash
cd docker
```

```bash
docker compose build
```

```bash
docker compose up
```

# To run the tool run in the terminal

```bash
python app/UI/CLI/main.py
```

# SELECT THE STEP FOR EXECUTION
