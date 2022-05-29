**ILLustrations Variations Exporter** is a tool designed to automate the process of exporting several image variations of an illustration.

Before using the tool
---
The tool only works with files in Adobe Photoshop's file format (*.PSD). Therefore, if you are working with another software you need to export it first.

**It is higly recommended** to merge down any layers that don't need to be toggled on/off by the program, especially if the native format of the illustration is not PSD. That will help to avoid issues when rendering the images and likely improve the rendering speed as well.

You need to define a naming convention for the layers, so that the tool can identify which layers it needs to show/hide for every variation.

Configuring the variations and modifiers
---
The first step when you open the application for the first time will be to setup your variations and modifiers. 

Both variations and modifiers can define a list of inclusion and exclusion patterns (they support both [glob](https://en.wikipedia.org/wiki/Glob_(programming)) and [Regular expressions](https://en.wikipedia.org/wiki/Regular_expression)), but when exporting the tool will only look into the variations (and their linked modifiers, if any). Variations can also define a subfolder, any version exported from a variation will go into that folder (or the base output folder if this setting is left empty).

The purpose of modifiers is to help you setup your variations. This is better illustrated with an example:

Let's you have a Safe For Work (SFW) and a Not Safe For Work (NSFW) variation configured. The SFW variation contains an inclusion pattern to match the clothes layers (so those layers will be toggled on) and the NSFW contains an exclusion pattern to hide the clothes plus an inclusion to toggle on some NSFW layer (I will let your imagination handle this one).

Now, you want to also provide versions of those two variations with the background off. You could create a "SFW Transp" and a "NSFW Transp" variations and redefine all the patterns of their non-transparent counterparts and add an exclusion pattern to match the background layer on top of that. This setup would work, but it is also quite cumbersome to do and error-prone, and it will get worse the more variations you need. This is where the modifiers come handy.

Following the same example, you could define a "Transparent" modifier (which would obviously contain an exclusion pattern to match the background layer) and link it to both variations. With this setup, the export process will generate additional transparent versions for both variations.

If there are more modifiers the tool will render versions for all the possible combinations by default, if this is not desirable you can also tweak the combinations to fit your needs.

**Important note:** The initial state of the layers is important, the tool will only toggle on or off the layers that match any inclusion or exclusion patterns respectively. The other layers will be left untouched. That means that if you have any layer that you don't want to see in any of the versions, you should keep that layer hidden in the PSD file that you load into the tool (or add an exclusion pattern for that in all variations).

Testing the configuration
---
Once the configuration is done you might want to test it, to do so you can apply the variations and modifiers from their corresponding menus and see how the checkboxes on the right panel (where the layer list is shown) update accordingly, you can also see a more visual confirmation by hitting the Update preview button afterwards (But keep in mind that the process might take a while depending on the resolution of the image and other factors).

Starting the export
---
Finally you are ready to export your illustration. Just load a PSD, select an output directory and hit that start button.