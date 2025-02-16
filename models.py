from fastcore.basics import AttrDict, patch

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

@patch
def update_step(self:Checklist, step_id, text=None, status=None):
    """Update a step in the checklist"""
    with DBConnection() as cursor:
        updates = []
        params = []
        if text is not None:
            updates.append("text = ?")
            params.append(text)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            
        if not updates:
            return False
            
        query = f"""
            UPDATE steps 
            SET {', '.join(updates)}
            WHERE id = ? AND checklist_id = ?
        """
        params.extend([step_id, self.id])
        cursor.execute(query, params)
        return cursor.rowcount > 0
