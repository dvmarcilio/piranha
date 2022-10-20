# Find Patterns using Polyglot Piranha

This repo assumes Piranha Polyglot is using a modified tree-sitter go grammar. In particular, one that exposes the `statement_list` and `statement` productions.
I have one available here: <https://github.com/dvmarcilio/tree-sitter-go>.
Piranha Polyglot was modified to point to this grammar (`Cargo.toml`).
Then installed locally (assumes `rustup` is also installed).

```bash
git clone git@github.com:dvmarcilio/piranha.git
cd piranha
git switch go_modified_grammar
```

On the directory of this README:

```bash
python3 -m venv .env
source .env/bin/activate
pip install --upgrade pip
pip install /home/user/piranha/polyglot/piranha
```

## Find _go leak_ patterns

```bash
rm -Rf output_go_leak/
python3 go_leak_patterns.py /home/user/codebase/go/src ./output_go_leak/
```

For scalability, the script is skipping files larger than 1MB.
To change this size, pass the argument like `--skip-threshold-mb=2`.

After the script is finished, summarize the output:

```bash
python3 summarize_patterns.py ./output_go_leak
```

`summary.txt` will be written in `./output_go_leak`.

### Patterns

## Find `for` occurrences from patterns using Piranha Polyglot

```bash
python3 find_for_patterns.py /home/user/codebase/
```

The script will create an output directory (e.g., `output_20220928-145338`) containing:

- CSVs containing matches for each pattern.
  - values for row and col are 0-indexed (as per tree-sitter). You should add 1 when manually navigating through a file.
- `revision.txt`: output of running `git rev-parse HEAD` on the codebase script argument.

### Execution

The script first runs Piranha Polyglot for every `.go` file in the codebase collecting matches for `for_statement`.
All the other patterns look for specific constructs inside `for_statement`'s.
Thus, for the following patterns, the script will only execute Polyglot Piranha in the files matched in the first step.

Optionally, you can pass the script an output path as the last argument.
This is particularly useful if you want to reuse CSVs from a previous run.
Just copy the csv's into a new directory and pass this new directory as the last script argument.

```bash
mkdir output
cp output_20220929-082535/1_for_Loops.csv output/1_for_loops.csv
python3 find_for_patterns.py /home/user/go-code/ ./output
```

### Patterns

#### 1: For loops

```go
for ... {
}
```

#### 2: Any `go_stmt` in for

```go
for ... {
    ...?
    go expression()
    ...?
}
```

#### 3: "Only `go_stmt`"

```go
for ... {
    go expression()
}
```

#### 4: "Surrounded `go_stmt`"

```go
for ... {
    ...
    go expression()
    ...
}
```

#### 5: "Variable declaration before `go_stmt`"

```go
for ... {
    x := x
    y := y
    go expression()
}
```

#### 6: "Variable declaration before a surrounded `go_stmt`"

```go
for ... {
    x := x
    y := y
    ... expre
    go expression()
    ... expre
}
```
