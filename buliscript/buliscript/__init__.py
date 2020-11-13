from .buliscript import BuliScript

# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = BuliScript(parent=app)
app.addExtension(extension)
