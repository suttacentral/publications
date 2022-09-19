## Individual TEX templates guide

An environmental variable `INDIVIDUAL_TEMPLATES_MAPPING` responsible for the mapping is included in `.env_public` file.

### Defining an individual template for a whole edition:

```python
INDIVIDUAL_TEMPLATES_MAPPING = '{
    "<text_uid>": "<file_name>.tex",
}'
```

### Defining individual templates for each volume in an edition:

```python
INDIVIDUAL_TEMPLATES_MAPPING = '{
    "<text_uid>": ["<file_name>.tex", "<file_name>.tex", "<file_name>.tex",],
}'
```
