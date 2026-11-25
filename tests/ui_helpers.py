def export_downloads(app):
    """Les exports générés sont distincts de la copie de secours du brouillon."""
    return [button for button in app.get("download_button")
            if button.label != "Télécharger la préparation (.cantus.json)"]
