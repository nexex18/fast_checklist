from fastcore.basics import AttrDict

class Checklist(AttrDict):
    def __init__(self, id, title, description, description_long='', created_at=None, steps=None):
        super().__init__(
            id=id,
            title=title,
            description=description,
            description_long=description_long,
            created_at=created_at,
            steps=steps or []
        )
