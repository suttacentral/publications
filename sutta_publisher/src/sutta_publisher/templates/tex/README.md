## TEX template guide

Standard jinja2 delimiters can conflict with latex syntax, therefore they have been replaced with the following:

Basic expressions

    {{ ... }}   ->   \VAR{ ... }

Control structures (if/elif/else, for-loops, macros and blocks)

    {% ... %}   ->   \BLOCK{ ... }

Comments

    {# ... #}   ->   \#{ ... }

Line statements

    #   ->   %%
