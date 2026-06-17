# TiddlyWikiBookStyle

Unified style ontology across desktop and mobile: a book. Inspiritation and idea credited to "Pefect Edition".

stylesheet:
```
Create a new tiddler in wiki with something-like the following details:

    Title: $:/_my/styles/book

    Tag: $:/tags/Stylesheet

    Type: text/css (or leave as default)
```

reader:
```
Create another tiddler that pulls unstyled/styled content together. Use TiddlyWiki's built-in {{{ filter }}} lists to dynamically construct the pages.

Create something-like the following Tiddler using Wikitext:

    Title: BookReader

    Type: text/vnd.tiddlywiki (Default)
```

use:
```
To test the layout, create a few test tiddlers:

    "Title:","Tag:", "Field:"; Add some long dummy text.

Open the BookReader tiddler and expand it to full-screen (using the standard TiddlyWiki "Zoom in" or full-screen view) to see the horizontal snapping layout in action.
```
