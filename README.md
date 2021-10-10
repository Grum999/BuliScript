> # Work in progress!!
> BuliScript development is far from being finished, but current main branch provide a relatively stable version of plugin
> There's some bug and many stuff not yet implemented, but it's already possible to play a bit with language
>
> Even README is not yet ready ^_^'




# Buli Script

A plugin for [Krita](https://krita.org).


## What is Buli Script?
*Buli Script* is a Python plugin made for [Krita](https://krita.org) (free professional and open-source painting program).


Like [Logo](https://en.wikipedia.org/wiki/Logo_(programming_language)) programming language, *Buli Script* is a scripting language that can be used to draw thing programmatically.

But it differs from (Logo)[https://en.wikipedia.org/wiki/Logo_(programming_language)]:
- *Buli Script* provides a larger set of instructions, including some command that allows to drive [Krita](https://krita.org)
- *Buli Script* language wants to be easier to use than (Logo)[https://en.wikipedia.org/wiki/Logo_(programming_language)]


## Screenshots

Small WebM video (Unfortunately github is not able to embed WebM/WebP files properly... :-/ )

![UI Interface example](https://github.com/Grum999/BuliScript/raw/main/documentation/buliscript_01.webm)


## Functionalities

- Integrated editor 
  - Higlighted syntax 
  - Multiple (tabbed) documents, with "unsaved state" management (like Atom editor does)
  - Language help (language reference, quick help)
  - Script execution output, with search functionnalities 
  - Search&Replace functionnalities
- Integrated canvas view  
  - Zoom in/out, Pan
  - Rulers & Grid
- BuliScript Language
  - Basic flows (if then else, loop)
  - Macro definition
  - Drawing primitive (line, rectangle, ellipse, ...)


## Download, Install & Execute

> # Plugin is still in development phase, there's no release yet :)
> Download source manually for testing


### Download
+ **[ZIP ARCHIVE - v0.0.0](https://github.com/Grum999/BuliScript/releases/download/0.0.0/buliscript.zip)**
+ **[SOURCE](https://github.com/Grum999/BuliScript)**


### Installation

Plugin installation in [Krita](https://krita.org) is not intuitive and needs some manipulation:

1. Open [Krita](https://krita.org) and go to **Tools** -> **Scripts** -> **Import Python Plugins...** and select the **buliscript.zip** archive and let the software handle it.
2. Restart [Krita](https://krita.org)
3. To enable *Buli Script* go to **Settings** -> **Configure Krita...** -> **Python Plugin Manager** and click the checkbox to the left of the field that says **Buli Script**.
4. Restart [Krita](https://krita.org)



### Execute

When you want to execute *Buli Script*, simply go to **Tools** -> **Scripts** and select **Buli Script**.


### Tested platforms
Plugin has been tested with Krita 4.4.1 (appimage) on Linux Debian 10

Currently don't kwow if plugin works on Windows and MacOs, but as plugin don't use specific OS functionalities and/resources, it should be ok.



## Plugin's life

### What's new?

...



### Bugs

Yes!
I didn't found them, but they're here...


### What’s next?

...

## License

### *Buli Script* is released under the GNU General Public License (version 3 or any later version).

*Buli Script* is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

*Buli Script* is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should receive a copy of the GNU General Public License along with *Buli Commander*. If not, see <https://www.gnu.org/licenses/>.


Long story short: you're free to download, modify as well as redistribute *Buli Script* as long as this ability is preserved and you give contributors proper credit. This is the same license under which Krita is released, ensuring compatibility between the two.
