# Covers with lualatex

## basics

- make two covers, for paperback and epub.
- use the same images for both.
- each has one main file, which includes both the preamble and the template.
- fonts are the same as the books
- colors are varied per text: dn is one color, mn is one color, etc. The small books in kn (dhp, snp, etc.) all have the same color. These are all determined in the individual files.
- each cover has a different leaf image

## process

Files are made from the following:

- preamble/ template
- individual 
- images
- fonts

The individual specifications are appended to the preamble, as with the books. Individual files are the same for both epub and paperback. They specify:

- colors
- images

Templates are stamped out with data from the publications API. I've added most of these already the best I can.

- **I don't know the templates for the blurbs on the back cover, so these must be added!"**

## wrap words in `\z{}` on front

On the front cover, each word must be wrapped in a custom `\z{command}`. This is to generate the contour, which allows the text to stand out over the leaf image. The command must be applied per word, because other solutions don't allow line wrapping, or at least, none that I have found.

This applies to all commands that begin with `front`, i.e.

```
\fronttranslationtitle, \fronttranslationsubtitle, \frontbyline, \frontcreatorname, \frontvolumenumber, \frontvolumeacronym, \frontvolumetranslationtitle, \frontvolumeroottitle
```
## epub

After creating the epub cover, the pdf file must be converted to jpg. Use imagemagick or similar. I got reasonable results with:

```
convert -density 200 epub-example.pdf -quality 90 epub-example.jpg
```

## examples

Example files are provided as a convenience, these can be deleted.