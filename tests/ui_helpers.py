def export_downloads(app):
    """Les exports générés sont distincts de la copie de secours du brouillon."""
    return [button for button in app.get("download_button")
            if button.label != "Télécharger la préparation (.json)"]


def preparation_value(app, key):
    """Conserve les assertions des scénarios de migration des anciennes listes."""
    fields = {"song_order": "path", "song_moments": "moment", "song_verses": "verses"}
    if key in fields and "preparation_items" in app.session_state:
        return [getattr(item, fields[key]) for item in app.session_state["preparation_items"]]
    return app.session_state[key]


def set_preparation_value(app, key, value):
    fields = ("song_order", "song_moments", "song_verses")
    if key in fields and "preparation_items" in app.session_state:
        snapshot = {field: preparation_value(app, field) for field in fields}
        del app.session_state["preparation_items"]
        for field, values in snapshot.items():
            app.session_state[field] = values
    app.session_state[key] = value


def item_widget_key(app, old_key):
    """Retrouve l'occurrence actuellement affichée à la position du scénario."""
    if old_key.startswith("sheet_moment_"):
        position = int(old_key.removeprefix("sheet_moment_"))
        return f"sheet_moment_{app.session_state['preparation_items'][position].uid}"
    if old_key.startswith("sheet_verses_"):
        position, identifier = old_key.removeprefix("sheet_verses_").split("_", 1)
        return f"sheet_verses_{app.session_state['preparation_items'][int(position)].uid}_{identifier}"
    prefix, position = old_key.split("-", 1)
    return f"{prefix}-{app.session_state['preparation_items'][int(position)].uid}"
