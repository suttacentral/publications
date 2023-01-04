# Publications

SuttaCentral books: make HTML, EPUB, PDF

## Requirements
* [Python 3.10](https://www.python.org/)
* Docker and docker-compose

## How to use
### Development stack

Clone repo

Install pre-commit git hooks:

1. First install dependencies (libraries responsible for formatting). You fill find them in Makefile#lint
e.g.
    ```bash
    pip install black isort mypy bandit autoflake
    ```
2. Then install the actual pre-commit hook
    ```bash
    # Go to project root
    cd publications

    # Make sure the file is executable
    chmod +x pre-commit

    # Install it
    cp pre-commit .git/hooks
    ```

It will mount the project root to the container:
```bash
# Build dev docker image
make build IMAGE_TARGET=development

# Run dev console to fiddle
make run-bash

# Tests
# if needed:
make build IMAGE_TARGET=development
# and
make test or make test-ci

# Lint code
# if needed:
make build IMAGE_TARGET=development
# and
make lint
```

### Production stack
```bash
# Go to project root
cd publications

# Run the script with given args
make run <personal_access_token> <publication_number>
```

# Maintenance

## Requirements file
Project uses [pip-tools](https://github.com/jazzband/pip-tools) to handle dependencies in `requirements/*.txt` files.
To manage requirements you need to have `pip-tools` installed in your env (or run docker for devs
`make build IMAGE_TARGET=development; make run-dev bash`).
Packages name used in this project are stored in `requirements/*.in`.
[Guide](https://code.kiwi.com/our-comprehensive-guide-to-python-dependencies-8a5a4366a563) on how to resolve conflicts
and/or update dependencies.

### How to add new package
1. Add package name to suitable `requirements/*.in` file
2. Run command to propagate changes and pin the package number
```bash
# Compile requirements *.txt files based on *.in file content
make compile-deps
```

### How to update all requirements to new versions
```bash
# To update all packages, periodically re-run
make recompile-deps
```

### How to sync requirements with your virtual environment
```bash
make sync-deps
```

### How to build and publish new docker image

#### Production
```bash
# Build docker image to github
make build IMAGE_TARGET=production

# Push docker image to github
make push-docker-image IMAGE_TARGET=production
```

#### Development
```bash
# Build docker image to github
make build IMAGE_TARGET=development

# Push docker image to github
make push-docker-image IMAGE_TARGET=development
```

# General notes

### [Architecture Scheme](scheme.html)

### Docker container
1. The project uses heavy `texlive` packages to generate books and covers, therefore we have decided to use a prebuilt
   Docker image for production.
2. Any .tex template or a `.env_public` file can be updated between application runs. There is an entrypoint in
   `Dockerfile` (production stage) to ensure that the latest project source files from GitHub repo are being used.

### GitHub Actions
The project can be run via GitHub Actions in three ways:
1. As a scheduled cron job (currently every Monday). It uses `suttacentral/sc_data/bilara_data` repo to detect if any
   publication included in `suttacentral.net/api/publication/editions` response were modified since a previous run.
   The detector uses `EDITION_FINDER_PATTERNS` environmental variable to match files to specific editions.
2. Manually by the user **without any input**. The app will automatically detect modified editions as
   above (see point 1.)
3. Manually by the user **with input** containing a publication number(s). The app accepts a single value
   or a list of values separated by a comma, for example: `scpub1` or `scpub1,scpub2,scpub3`.

### Configs
1. Each publication may have a different editions (currently HTML, EPUB and PDF are supported). Mapping of finished
   publications: `suttacentral.net/api/publication/editions`
2. Each edition has its own JSON config: `suttacentral.net/api/publication/edition/<edition_id>` which contains:
   - basic information about the publication's author, language, title, etc.
   - the number and details of individual volumes
   - the order and content of individual matters included in frontmatter, mainmatter and backmatter
   - the depth of a main table of contents and a secondary table of contents if specified
3. There are few kinds of front and back matters:
   - `./matter/<name>.html` are processed in unchanged form
   - others (e.g. `titlepage`, `halftitlepage`, etc.) use jinja2 templates included in `src/sutta_publisher/templates/html/`
   - `main-toc` is generated after the mainmatter is ready and uses jinja2 template
4. Mainmatter parts are composed of segments taken from SuttaCentral API. There are two types of segments:
   - `branch` - the segments which have no actual content. These are the headings (titles) of whole books, parts,
     chapters etc. included in a given mainmatter part
   - `leaf` - the segments with actual content: html markups, main text verses, notes, references
5. SuttaCentral API does not provide any information about the depth of a given segment. The structure is strictly based
   on `super_tree.json` and adequate `<text_uid>-tree.json`.

### Latex Document Config
Since `pylatex` package adds default documentclass and document_options commands to the files it generates, they config
must be changed via `LATEX_DOCUMENT_CONFIG` variable in `.env_public` file.

### Styling classes and languages
SuttaCentral's custom styling classes like namo, uddana-intro, pli, san can be added to the project via the following
variables included in `.env_public` file:
1. `SANSKRIT_LANGUAGES`: `class="pli"` --> `\textsanskrit`
2. `FOREIGN_SCRIPT_MACRO_LANGUAGES`: `lang="lzh"` --> `\langlzh`
3. `STYLING_CLASSES`: `class="uddana-intro"` --> `\scuddanaintro` (please note that the `sc` is added at the beginning
   and `-` hyphen is removed)

### Editions without Latex sections
If a given edition's depth does not allow to use Latex sections, we can force the project to use Latex chapters via
`TEXTS_WITH_CHAPTER_SUTTA_TITLES` variable in `.env_public` file.

### Pannasakas
Titles with IDs ending with `pannasaka` are converted to Latex custom `\pannasa` commands. Additional branches can be
added via `ADDITIONAL_PANNASAKA_IDS` variable in `.env_public` file.
