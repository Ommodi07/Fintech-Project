"""
Stores conversation history for context-aware response.
"""

chat_history = []


def add_to_memory(user_msg: str, bot_msg: str):
    """Add a user-bot exchange to memory."""
    chat_history.append({"user": user_msg, "bot": bot_msg})
    print(chat_history)
    if len(chat_history) > 4:
        for entry in chat_history[:-4]:
            chat_history.remove(entry)
    else :
        None


def get_memory() -> list:
    """Return current chat history."""
    return chat_history


def clear_memory():
    """Clear all chat history."""
    chat_history.clear()


def format_memory() -> str:
    """Format chat history as a readable string for the LLM prompt."""
    if not chat_history:
        return "No previous conversation."

    formatted = ""
    for entry in chat_history:
        formatted += f"User: {entry['user']}\Bot: {entry['bot']}\n\n"
    return formatted.strip()
