from Message import Message


class MessageBox:

    def __init__(self):
        self.inbox = []

    def is_empty(self) -> bool:
        """
        Checks if the message box is empty.
        :return: True if no messages, False otherwise
        """
        return len(self.inbox) == 0

    def store_message(self, message: Message):
        """
        Adds a new message to the message box.
        :param message: The message to be added
        """
        self.inbox.append(message)

    def retrieve_message(self) -> Message:
        """
        Retrieves and removes the first message from the message box.
        :return: The oldest message in the inbox
        """
        return self.inbox.pop(0) if self.inbox else None
