# Templates for unstructured content

Some of the content for books has no associated HTML. This includes info from config files, as well as content such as blurbs.

This directory contains jinja templates for such content.

THESE ARE MERELY FIRST DRAFT SUGGESTIONS, PLEASE CHANGE THEM! THEY ARE NOT REAL JINJA TEMPLATES I AM JUST MAKING STUFF UP AS I GO ALONG AND HOPING FOR THE BEST!!

- In the "blurbs" template, note that "acronym" is *not* the same as UID, and *cannot* be automatically transformed. This is because capitalization depends on contextual knowledge (eg. `sn` becomes `SN` but `snp` becomes `Snp`.) Use the acronym in presentation contexts, UID for programming. The canonical source for transforming these is here: https://github.com/suttacentral/sc-data/blob/master/misc/uid_expansion.json
- I am including epub:type semantics, these can be included in Standalone HTML even though they are ignored!