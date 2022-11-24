## TEX template guide

### Jinja2 semantics

Standard jinja2 delimiters can conflict with latex syntax, therefore they have been replaced with the following:

Basic expressions

`{{ ... }}   ->   \VAR{ ... }`

Control structures (if/elif/else, for-loops, macros and blocks)

`{% ... %}   ->   \BLOCK{ ... }`

Comments

`{# ... #}   ->   \#{ ... }`

Line statements

`#   ->   %%`

### Examples

```latex
\markboth{\VAR{name | safe}}{\VAR{root_name | safe}}

\halftitlepageVolumeTranslationTitle{\BLOCK{if volume_translation_title}\VAR{volume_translation_title | safe}\BLOCK{endif}}
```
