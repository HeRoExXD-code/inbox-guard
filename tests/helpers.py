def scripted(*replies):
    """A fake chat function that returns canned model replies, in order (no network)."""
    it = iter(replies)

    def chat(messages):
        return next(it)

    return chat
