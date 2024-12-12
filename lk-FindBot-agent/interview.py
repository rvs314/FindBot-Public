
from oai import Conversation
from sheets import Notes


class Interview:
    notes: Notes
    convo: Conversation

    def __init__(self,  convo: Conversation, notes: None | Notes = None):
        self.notes = Notes() if notes is None else notes
        self.convo = convo
